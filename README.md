# mldmon

A Discord bot for managing mldkyt's Discord server

WORKS ON MY MACHINE: This project is mainly intended to be used by mldkyt for their Discord bot. I won't support with hosting this bot for any personal reasons.

## Features

- Yuri posting
- Yaoi posting
- DMs without DMing
- User commands for mldkyt

## Authorizing yuribot

For the bot to work and because I don't care, you need to authorize yuribot, to do so, run

```bash
docker compose run --rm -it --entrypoint sh mldmon
```

Then in the bash window run

```bash
uv run auth.py
```

and fill out the parameters. This will authorize yuribot for posting!
