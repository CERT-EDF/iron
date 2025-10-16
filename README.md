<p align="center"><img width="120" src="./web/public/favicon.png"></p>
<h2 align="center">Iron</h2>

<div align="center">

![Status](https://img.shields.io/badge/status-active-success?style=for-the-badge)
![Powered By: EDF](https://img.shields.io/badge/Powered_By-CERT_EDF-FFFF33.svg?style=for-the-badge)
[![License: MIT](https://img.shields.io/badge/License-MIT-2596be.svg?style=for-the-badge)](/LICENSE)

</div>

<p align="center">Unified cases, seamless integrations</p>
<br>

<div align="center">

![Demo](./.github/screenshot.png)

</div>

# Introduction

Iron is a minimalist synchronization tool designed to simplify the cases management within the [CERT-EDF/fusion](https://github.com/CERT-EDF/fusion) framework, acting as a centralized interface to create and manage cases, ensuring consistency across services.

Iron pulls together services into a unified, cohesive system.

Iron supports the following services:
- [CERT-EDF/carbon](https://github.com/CERT-EDF/carbon): minimalist digital logbook
- [CERT-EDF/helium](https://github.com/CERT-EDF/helium): minimalist forensic collections manager
- [CERT-EDF/neon](https://github.com/CERT-EDF/neon): minimalist malware database management
- [dfir-iris](https://github.com/dfir-iris): incident responders platform

<br>

## Getting Started

> [!NOTE]
> Iron is part of the [CERT-EDF/fusion](https://github.com/CERT-EDF/fusion) framework. This section will guide you for the standalone usage.

Deployment is designed to be simple using Docker.
```bash
export GIT_TAG="$(git describe --tags)"
docker compose up -d
```

Basic HTTP example using Nginx:
```nginx
server {
    listen 80;
    server_name iron.domain.lan;

    access_log  /var/log/nginx/iron.access.log;
    error_log  /var/log/nginx/iron.error.log

    proxy_http_version 1.1;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    location /api {
      proxy_pass http://127.0.0.1:8010;
      client_max_body_size 4G;
      proxy_buffering off;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
      proxy_set_header Host $host;
    }

    location / {
      proxy_pass http://127.0.0.1:8020;
    }
  }
```

<br>

## Configuration

Refer to the documentation in

- [iron.dist.yml](https://github.com/CERT-EDF/iron/blob/main/server/iron.dist.yml)
- [constant.dist.yml](https://github.com/CERT-EDF/iron/blob/main/server/constant.dist.yml)

<br>

## License

Distributed under the MIT License.

<br>

## Contributing

Contributions are welcome, see [CONTRIBUTING.md](https://github.com/CERT-EDF/iron/blob/main/CONTRIBUTING.md) for more information.

<br>

## Security

To report a (suspected) security issue, see [SECURITY.md](https://github.com/CERT-EDF/iron/blob/main/SECURITY.md) for more information.
