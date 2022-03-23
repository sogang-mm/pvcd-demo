#!/usr/bin/env bash
set -x
ip="${1:-0}"
port="${2:-8001}"
python /workspace/manage.py runserver $ip:$port
