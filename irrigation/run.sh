#!/bin/sh -xe
cd /daten/src/git/homevent/irrigation/
export DJANGO_SETTINGS_MODULE="settings"
export PYTHONPATH=$(pwd)/..:$(pwd)
(
python manage.py runserver 0.0.0.0:58000 &
python manage.py runschedule Schleiermacher+Hardenberg &
) > /tmp/rainman.log
