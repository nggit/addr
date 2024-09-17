# addr
This is an alternative to ngrok.

It's like [localhost.run](https://localhost.run/), or [srv.us](https://docs.srv.us/).

This is **not yet a complete project** since it was created in 2022.
But I'm publishing it now in case it's useful.

![addr](https://raw.githubusercontent.com/nggit/addr/main/ssh-client.png)

## Features
- No propietary client, just use the `ssh` command to create a reverse tunnel
- It's possible to choose your own subdomain
- addr gives you a nearly permanent port!

## Installing
addr consists of only two components: `service_ssh_server` which handles SSH connections,
and `service_nginx_proxy` which acts as an HTTP router. It routes dynamically using a tiny [njs](https://nginx.org/en/docs/njs/) script in [nginx/njs/router.js](https://github.com/nggit/addr/blob/main/nginx/njs/router.js).

No worries, you can get up and running right away and touch up the configuration later!

### 1. Build images
```
docker-compose build --no-cache
```

### 2. Create and run the containers
**Note:** addr will run on ports 22 and 80 (and 443). If you already have an `sshd` running, ensure you have moved it to another port number.
```
docker-compose up
```

If all goes well, you can run in the background with `-d`:
```
docker-compose up -d
```

Open up the homepage at http://`DOMAIN`, e.g. [http://localhost](http://localhost). You should see how to use the service.

## Configuring
Once successfully installed and running, you can always change the configuration and then run this accordingly:
```
docker-compose restart
```

### Configure service_ssh_server
1. You can set your `DOMAIN`, etc. at [ssh_server/config/.env](https://github.com/nggit/addr/blob/main/ssh_server/config/.env)

### Configure service_nginx_proxy
1. Set up your homepage by creating `index.html` in [nginx/www/](https://github.com/nggit/addr/blob/main/nginx/www)`DOMAIN`. E.g. *nginx/www/you.com/index.html*.
3. You can set `ssl_certificate`, and `listen` 443 in [nginx/nginx.conf](https://github.com/nggit/addr/blob/main/nginx/nginx.conf)

## License
MIT License
