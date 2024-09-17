#!/usr/bin/env python3
# Copyright (c) 2023 nggit

import asyncio
import logging
import os

import asyncssh

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    print('INFO: uvloop is not installed')

from sqlite3i import Database
from config.config import (
    DEFAULT_PLAN,
    DOMAIN,
    LOG_LEVEL,
    SSH_HOST_KEYS_DIR,
    SSH_LISTEN_HOST,
    SSH_LISTEN_PORT,
    NAMES_DIR,
    PORTS_DIR,
    DB_PATH
)
from utils import validate_name

_SSH_HOST_KEYS = [
    os.path.join(
        SSH_HOST_KEYS_DIR,
        item
    )[:-4] for item in os.listdir(SSH_HOST_KEYS_DIR) if item.endswith('.pub')
]

logging.basicConfig(level=LOG_LEVEL)

# https://asyncssh.readthedocs.io/en/latest/api.html#asyncssh.set_debug_level
asyncssh.set_debug_level(2)


class AddrSSHServer(asyncssh.SSHServer):
    logger = logging.getLogger('asyncssh')
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    _waiters = {}

    def connection_made(self, conn):
        self._conn = conn
        self._loop = asyncio.get_event_loop()
        self._db = Database(DB_PATH)
        self._db.connect()

    def connection_lost(self, exc):
        if exc:
            self.logger.error('connection_lost: %s', str(exc))

        self._db.close()

    def begin_auth(self, username: str) -> bool:
        name = username.strip().lower()

        if validate_name(name):
            self._conn.send_auth_banner(f'Welcome to {DOMAIN}!\n')
        else:
            self._conn.send_auth_banner(
                'Name must be 5 - 63 characters,\n'
                'contain no characters other than a-z, 0-9, "-" and ".",\n'
                'begin and end with letters or numbers\n'
            )
            self._conn.close()

        return True

    def public_key_auth_supported(self) -> bool:
        return True

    def validate_public_key(self, username: str, key: asyncssh.SSHKey) -> bool:
        name = username.strip().lower()
        fingerprint = key.get_fingerprint()

        stmt = self._db.prepare('SELECT fingerprint FROM names WHERE name = ?')
        stmt.execute([name])
        row = stmt.fetch()

        if row:
            if row['fingerprint'] != fingerprint:
                self._conn.send_auth_banner(
                    f'\n{name} is already registered with another device. '
                    'Please choose another domain name.\n'
                )
                self._conn.close()
                return False
        else:
            stmt = self._db.prepare(
                'SELECT names.plan, fingerprints.usage FROM names '
                'LEFT JOIN fingerprints ON names.name = fingerprints.owner '
                'WHERE fingerprints.fingerprint = ?'
            )
            stmt.execute([fingerprint])
            row = stmt.fetch()

            if row and row['usage'] >= row['plan']:
                self._conn.send_auth_banner(
                    '\nPlan limit exceeded (%d/%d).\n' %
                    (row['usage'], row['plan'])
                )
                self._conn.close()
                return False

            if not self._db.prepare(
                    'INSERT INTO names '
                    '(name, port, plan, status, fingerprint) '
                    'VALUES (?, ?, ?, ?, ?)'
                    ).execute([name, 0, DEFAULT_PLAN, 0, fingerprint]):
                self._conn.close()
                return False

            if not self._db.prepare(
                    'INSERT INTO fingerprints (fingerprint, owner, usage) '
                    'VALUES (?, ?, ?)'
                    ).execute([fingerprint, name, 1]):
                self._db.prepare(
                    'UPDATE fingerprints SET usage = usage + 1 '
                    'WHERE fingerprint = ?'
                ).execute([fingerprint])

        fileno = self._conn.get_extra_info('socket').fileno()
        self._waiters[fileno] = self._loop.create_future()
        return True

    async def server_requested(self, listen_host: str, listen_port: int) -> bool:  # noqa: E501
        name = self._conn.get_extra_info('username').strip().lower()
        fileno = self._conn.get_extra_info('socket').fileno()
        fut = self._waiters[fileno]

        if listen_port not in (80, 443):
            fut.set_result(f'Port {listen_port:d} is not supported')
            return False

        _listen_port = self.get_port(name)

        try:
            listener = await self._conn.forward_local_port(
                '',
                _listen_port,
                listen_host,
                listen_port
            )

            if _listen_port == 0:
                port = listener.get_port()

                if '.' in name:
                    domain = name
                else:
                    domain = f'{name}.{DOMAIN}'

                # create name and port files that bind to each other
                # name <--> port
                # will be used by /etc/nginx/njs/router.js
                with open(os.path.join(NAMES_DIR, domain), 'w') as f:
                    f.write('%d' % port)

                with open(os.path.join(PORTS_DIR, '%d' % port), 'w') as f:
                    f.write(domain)

                if not self._db.prepare(
                        'INSERT INTO ports (port, owner) VALUES (?, ?)'
                        ).execute([port, name]):
                    self._db.prepare(
                        'UPDATE ports SET owner = ? WHERE port = ?'
                    ).execute([name, port])

                self._db.prepare(
                    'UPDATE names SET port = ? WHERE name = ?'
                ).execute([port, name])
        except OSError as exc:
            self.logger.error('Port forwarding failed: %s', str(exc))
            return False
        finally:
            self._db.close()

        if not fut.done():
            fut.set_result(None)

        return listener

    @staticmethod
    def get_port(name):
        with Database(DB_PATH) as db:
            stmt = db.prepare(
                'SELECT ports.port FROM ports LEFT JOIN names '
                'ON ports.port = names.port AND ports.owner = names.name '
                'WHERE names.name = ?'
            )
            stmt.execute([name])
            row = stmt.fetch()

            if row:
                return row['port']

        return 0

    @classmethod
    async def handle_client(cls, process: asyncssh.SSHServerProcess) -> None:
        name = process.get_extra_info('username').strip().lower()
        fileno = process.get_extra_info('socket').fileno()
        loop = asyncio.get_running_loop()
        timer = loop.call_at(loop.time() + 10, cls._waiters[fileno].cancel)

        try:
            result = await cls._waiters[fileno]

            if result:
                process.stdout.write(f'\n{result}.\n')
                process.exit(1)
        except asyncio.CancelledError:
            process.stdout.write('\nFailed to create tunnel (timeout).\n')
            process.exit(1)
        finally:
            timer.cancel()
            del cls._waiters[fileno]

        _listen_port = cls.get_port(name)

        if _listen_port > 0:
            process.stdout.write(
                '\nYou can access your application through '
                'the following public addresses:\n'
            )
            process.stdout.write(
                f'  HTTP:\thttps://{name}.{DOMAIN}\n'
            )
            process.stdout.write(
                f'  TCP :\t{name}.{DOMAIN}:{_listen_port}\n'
            )

            if '.' in name:
                process.stdout.write(
                    '\nPoint your domain using CNAME to '
                    f'"{name}.{DOMAIN}" to enable custom domains.\n'
                )

            while not process.stdin.at_eof():
                try:
                    await process.stdin.readline()
                except asyncssh.BreakReceived:
                    process.stdout.write('\nTunnel closed.\n')
                    process.exit(0)
                except Exception:  # nosec B110
                    pass
        else:
            process.stdout.write('\nFailed to create tunnel.\n')
            process.exit(1)


async def main():
    server = await asyncssh.create_server(
        AddrSSHServer,
        SSH_LISTEN_HOST,
        SSH_LISTEN_PORT,
        server_host_keys=_SSH_HOST_KEYS,
        process_factory=AddrSSHServer.handle_client,
        server_version=DOMAIN,
        compression_algs=None,
        allow_scp=False,
        keepalive_interval=120,
        keepalive_count_max=720
    )

    await server.wait_closed()


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
