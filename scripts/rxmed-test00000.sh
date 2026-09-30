#!/bin/bash

set -e

cd "$(dirname "$0")/.."

echo "Building RxMed..."
docker compose build

echo "Running BBUser00000 medication test..."
docker compose run --rm \
    --entrypoint python3 \
    rxmed \
    /app/src/rxmed_decoder.py \
    /app/Resources/Tests/BBUser00000_meds_parsed.json \
    /app/data/BBUser00000_meds_decoded.json

echo
echo "Output: data/BBUser00000_meds_decoded.json"
