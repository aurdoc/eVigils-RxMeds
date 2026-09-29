FROM python:3.13-slim

WORKDIR /app

COPY src/ /app/src/

ENTRYPOINT ["python3", "/app/src/rxmed_decoder.py"]
