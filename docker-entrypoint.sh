#!/usr/bin/bash


if [[ "$1" == "web" ]]; then
    echo "==> Giving migrations time"
    sleep 5
    echo "==> Starting nyxie (Web)"
    uv run gunicorn -w 4 -b 0.0.0.0 'webmain:app'
else
    echo "==> Running migrations"
    uv run alembic upgrade head
    echo "==> Starting nyxie"
    uv run main.py
fi
