FROM python:3.11-alpine

WORKDIR /app

COPY pyproject.toml .

RUN pip3 install --upgrade uv
RUN uv sync

COPY main.py .
COPY constants.py .
COPY rom/ rom/.
COPY cogs/ cogs/.
COPY util/ util/.

ENTRYPOINT ["python3", "main.py"]
