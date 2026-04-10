#!/usr/bin/env bash
f=$(python -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))")
[[ "$f" != *.py ]] && exit 0
uv run ruff check --fix
uv run ruff format
r=0; uv run pytest -q || r=$?
[[ $r -eq 5 ]] && exit 0
exit $r