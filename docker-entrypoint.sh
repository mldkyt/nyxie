#!/usr/bin/bash

echo "==> Running migrations"
uv run alembic upgrade head

if [[ "$1" == "web" ]]; then
  echo "==> Starting obsidian (Web)"
  uv run gunicorn -w 4 -b 0.0.0.0 'webmain:app'
else
  echo "==> Starting obsidian"
  uv run main.py
fi
