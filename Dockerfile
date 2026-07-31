FROM python:3.11-alpine

WORKDIR /app

RUN apk add --no-cache postgresql17 postgresql17-dev git bash gcc
RUN pip3 install --upgrade uv

COPY pyproject.toml .
COPY uv.lock .

RUN uv sync

COPY webmain.py .
COPY main.py .
COPY constants.py .
COPY database.py .
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

ENTRYPOINT ["sh", "docker-entrypoint.sh"]
