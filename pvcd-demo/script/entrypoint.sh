#!/usr/bin/env bash
set -x
service ssh start

source ./script/run_migration.sh
python manage.py loaddata reference.vcdb.json

source ./script/run_celery.sh
#bash ./script/run_gunicorn.sh
source ./script/run_django.sh


