#!/bin/sh
set -eu
next_project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec "$next_project_dir/.venv/bin/python" "$next_project_dir/scripts/run-bounded-lab.py" "$@"
