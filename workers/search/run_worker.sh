#!/usr/bin/env bash
set -x
celery --app search worker -l info -c 4