#!/usr/bin/env bash
set -x
(exec kill $(ps aux |awk '/celery/ {print $2}')) 2>/dev/null &
