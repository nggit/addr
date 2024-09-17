FROM alpine:3.20

# https://nginx.org/en/linux_packages.html#Alpine
RUN echo '@nginx https://nginx.org/packages/alpine/v3.20/main' >> /etc/apk/repositories; \
    wget -qO /etc/apk/keys/nginx_signing.rsa.pub https://nginx.org/keys/nginx_signing.rsa.pub; \
    apk update && apk upgrade

# install required packages
RUN apk add --no-cache nginx-module-njs@nginx libcap

# create a non-root user 'app'
# shadow version: useradd --home-dir /app --create-home --user-group app -G nginx
RUN adduser -Dh /app -u 1000 app app && addgroup app nginx; \
    echo "export PATH=/app/.local/bin:$PATH" > /app/.profile

# clean up
RUN rm -rf /tmp/* /var/cache/apk/*

EXPOSE 80 443
VOLUME ["/etc/nginx", "/etc/letsencrypt"]
WORKDIR /etc/nginx

ENTRYPOINT ["/usr/bin/env", "--"]
CMD ["sh", "-c", "chown -R app:app /etc/letsencrypt /etc/nginx /var/cache/nginx /var/log/nginx; \
    setcap 'cap_net_bind_service=ep' /usr/sbin/nginx; \
    su -c 'exec /usr/sbin/nginx -g \"daemon off;\"' - app"]
