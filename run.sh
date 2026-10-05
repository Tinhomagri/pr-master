#!/usr/bin/env bash
# atalho: ./run.sh --project django-ddd --repo t4egroup/123log review 221
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && ./.venv/bin/pip install -q -r requirements.txt; }
exec ./.venv/bin/python -m bot "$@"
