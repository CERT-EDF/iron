#!/usr/bin/env sh
set -e
# prepare data directory if needed
mkdir -p /data
# prepare configuration directory if needed
mkdir -p /conf
if [ ! -f /conf/proxy.yml ]; then
    cp /tpl/proxy.dist.yml /conf/proxy.yml
fi
# exec depending on ROLE
case "${ROLE}" in
    proxy)
        exec /venv/bin/iron-x-iris --config /conf/proxy.yml
        ;;
    *)
        exec "$@"
        ;;
esac
