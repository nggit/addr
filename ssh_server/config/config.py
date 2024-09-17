import os
import subprocess

from sqlite3i import Database
from .utils import load_dotenv

load_dotenv()

# ---- GENERAL SETTINGS ----

# all names will be under this domain (as subdomains, e.g. you.localhost)
DOMAIN = os.environ.get('DOMAIN', 'localhost')

# DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# ---- SSH SERVER SETTINGS ----
# for more SSH configurations please see ssh_server.py

# this means a limit on the number of subdomains
# that can be created for each client
DEFAULT_PLAN = int(os.environ.get('DEFAULT_PLAN', 10))

SSH_LISTEN_HOST = os.environ.get('SSH_LISTEN_HOST', '')
SSH_LISTEN_PORT = int(os.environ.get('SSH_LISTEN_PORT', 22))

# ----
# the settings end here
# please don't edit the following lines unless you know what you are doing

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
SSH_HOST_KEYS_DIR = os.path.join(CONFIG_DIR, 'data', 'ssh')
NAMES_DIR = os.path.join(CONFIG_DIR, 'data', 'routes', 'names')
PORTS_DIR = os.path.join(CONFIG_DIR, 'data', 'routes', 'ports')
DB_PATH = os.path.join(CONFIG_DIR, 'data', 'routes.db')

os.makedirs(SSH_HOST_KEYS_DIR, exist_ok=True)
os.makedirs(NAMES_DIR, exist_ok=True)
os.makedirs(PORTS_DIR, exist_ok=True)

with Database(DB_PATH) as db:
    if not os.path.exists(DB_PATH):
        _CREATE_TABLES = """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS names (
              name TEXT PRIMARY KEY NOT NULL,
              port INTEGER DEFAULT 0,
              plan INTEGER DEFAULT 10,
              status INTEGER DEFAULT 0,
              fingerprint TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ports (
              port INTEGER PRIMARY KEY,
              owner TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS fingerprints (
              fingerprint TEXT PRIMARY KEY NOT NULL,
              owner TEXT NOT NULL,
              usage INTEGER DEFAULT 1
            )
        """

        for query in _CREATE_TABLES.split(';'):
            if not db.prepare(query).execute():
                try:
                    os.unlink(DB_PATH)
                except FileNotFoundError:
                    pass

                break


KEY_PATH = os.path.join(SSH_HOST_KEYS_DIR, 'id_rsa')

if not os.path.exists(KEY_PATH):
    result = subprocess.run(
        ['ssh-keygen', '-t', 'rsa', '-b', '2048', '-f', KEY_PATH, '-N', ''],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    print(result.stdout)
