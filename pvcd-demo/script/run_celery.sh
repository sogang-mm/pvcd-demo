#!/usr/bin/env bash
set -x
celery --app pvcd_demo worker -c 2 -l info -P gevent