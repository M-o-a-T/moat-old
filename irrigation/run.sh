#!/bin/sh -xe
cd "$(dirname "$0")"
export DJANGO_SETTINGS_MODULE="settings"
P="$(pwd)"
export PYTHONPATH=$P/../dabroker:$P/..:$P
(
./manage.py runserver 0.0.0.0:58000 &
./manage2.py runschedule Schleiermacher+Hardenberg &
while sleep 300 ; do ./manage.py genschedule -s Schleiermacher+Hardenberg ; done &
) > /tmp/rainman.log 2>&1
