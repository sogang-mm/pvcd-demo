#!/usr/bin/env bash
set -x
celery --app extractor worker -l info -P gevent