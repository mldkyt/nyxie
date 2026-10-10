FROM python:3.11-alpine

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apk  apk add --no-cache postgresql17 postgresql17-dev git bash gcc
RUN --mount=type=cache,target=/root/.cache/pip pip3 install --upgrade uv

COPY pyproject.toml .
COPY uv.lock .

RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen

COPY webmain.py .
COPY main.py .
COPY constants.py .
COPY database.py .
COPY auth.py .
COPY cogs/ cogs/.
COPY util/ util/.
COPY alembic.ini .
COPY alembic/ alembic/.
COPY docker/ docker/.
COPY web/ web/.
COPY .git/ .git/.

RUN chmod +x docker/prepare.sh
RUN bash docker/prepare.sh

COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

STOPSIGNAL SIGKILL

ENTRYPOINT ["sh", "docker-entrypoint.sh"]
