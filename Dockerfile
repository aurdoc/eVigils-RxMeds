FROM python:3.13-slim

WORKDIR /app

COPY src/ /app/src/

EXPOSE 8080

ENTRYPOINT ["python3", "/app/src/rxmed_server.py"]
