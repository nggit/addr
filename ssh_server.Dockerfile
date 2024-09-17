FROM alpine:3.20

# update system
RUN apk update && apk upgrade

# install required packages
RUN apk add --no-cache libcap openssh-keygen python3

# create a non-root user 'app'
# shadow version: useradd --home-dir /app --create-home --user-group app
RUN adduser -Dh /app -u 1000 app app; \
    echo "export PATH=/app/.local/bin:$PATH" > /app/.profile

# install pip and python packages locally for user 'app'
RUN python3 -m venv --system-site-packages /usr/local; \
    python3 -m pip install asyncssh; \
    python3 -m pip install sqlite3i; \
    python3 -m pip install uvloop

# clean up
RUN rm -rf /tmp/* /var/cache/apk/*

EXPOSE 22
VOLUME /app/ssh_server
WORKDIR /app

ENTRYPOINT ["/usr/bin/env", "--"]
CMD ["sh", "-c", "chown -R app:app /app; \
    setcap 'cap_net_bind_service=ep' $(readlink -f /usr/bin/python3); \
    su -c 'exec python3 /app/ssh_server/ssh_server.py' - app"]
