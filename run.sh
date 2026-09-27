#!/bin/sh

set -e
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

exec "$PYTHON" src/main.py "$@"