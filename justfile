
set dotenv-load := true

db action:
    #!/usr/bin/env bash
    CMD="{{ action }}"
    case "$CMD" in
        "up")   FINAL_CMD="up -d" ;;
        "logs") FINAL_CMD="logs -f" ;;
        *)      FINAL_CMD="$CMD" ;;
    esac
    docker compose $FINAL_CMD

bot:
    uv run main.py

web:
    uv run webmain.py
