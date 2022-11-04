#!/usr/bin/env bash

set -e

if [ "${1}" = "uwsgi" ]; then
  sh ./maketranslations.sh
  python manage.py compilemessages
  python manage.py collectstatic --noinput
fi

exec "${@}"
