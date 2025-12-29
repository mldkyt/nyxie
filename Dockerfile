FROM python:3.11-alpine

WORKDIR /app

RUN apk add --no-cache postgresql17 postgresql17-dev

COPY pyproject.toml .

RUN pip3 install --upgrade uv
RUN uv sync

COPY logger.py .
COPY main.py .
COPY constants.py .
COPY database.py .
COPY rom/ rom/.
COPY cogs/ cogs/.
COPY util/ util/.
COPY alembic.ini .
COPY alembic/ alembic/.

COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["sh", "docker-entrypoint.sh"]
