#!/bin/bash

set -e

cd "$(dirname "$0")/.."

echo "Building RxMed..."
docker compose build

echo "Starting RxMed HTTP service..."
docker compose up -d

echo "Waiting for RxMed..."
sleep 2

mkdir -p data

echo "Running BBUser00000 HTTP medication test..."
curl --fail --silent --show-error \
    -H "Content-Type: application/json" \
    --data-binary @Resources/Tests/BBUser00000_meds_parsed.json \
    http://127.0.0.1:8080/medications/decode \
    -o data/BBUser00000_meds_decoded_http.json

echo
echo "Output: data/BBUser00000_meds_decoded_http.json"
