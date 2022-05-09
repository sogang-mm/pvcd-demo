#!/usr/bin/env bash
set -x
ip="${1:-0}"
port="${2:-8080}"
gunicorn pvcd_demo.wsgi --bind $ip:$port

