#!/usr/bin/env sh
set -e
# prepare data directory if needed
mkdir -p /data
# prepare configuration directory if needed
mkdir -p /conf
if [ ! -f /conf/iron.yml ]; then
    cp /tpl/iron.dist.yml /conf/iron.yml
fi
if [ ! -f /conf/constant.yml ]; then
    cp /tpl/constant.dist.yml /conf/constant.yml
fi
# prepare analyzer directory if needed
mkdir -p /analyzer
# exec depending on ROLE
case "${ROLE}" in
    server)
        exec /venv/bin/iron-server --config /conf/iron.yml
        ;;
    synchronizer)
        exec /venv/bin/iron-synchronizer --config /conf/iron.yml
        ;;
    *)
        exec "$@"
        ;;
esac
