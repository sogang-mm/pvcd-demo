#!/usr/bin/env bash
set -x
service ssh start

bash ./script/run_migration.sh
python manage.py loaddata reference.vcdb.json

bash ./script/run_celery.sh &
#bash ./script/run_django.sh 0 8001
bash ./script/run_gunicorn.sh 0 8080




