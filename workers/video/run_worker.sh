#!/usr/bin/env bash
set -x
celery --app video worker -l info -c 4