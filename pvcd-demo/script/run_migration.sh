#!/usr/bin/env bash
set -x
python /workspace/manage.py makemigrations
python /workspace/manage.py migrate
