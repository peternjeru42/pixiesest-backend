#!/bin/sh
set -eu

exec celery -A config worker \
  --loglevel "${CELERY_LOG_LEVEL:-info}" \
  --beat
