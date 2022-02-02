#!/bin/sh

set -e

# activate our virtual environment here
. /venv/bin/activate

exec uvicorn platform_registry.main:app --host 0.0.0.0 \
     --port 8080 --reload \
     --log-config platform_registry/config/log.yaml
