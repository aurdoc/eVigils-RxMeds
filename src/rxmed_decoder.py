#!/usr/bin/env python3

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path


RXNAV_URL = "http://nginx/REST/ndcstatus.json"


def decode_ndc(ndc):
    url = RXNAV_URL + "?" + urllib.parse.urlencode({"ndc": ndc})

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            result = json.load(response)

    except Exception as error:
        raise RuntimeError(f"RxNav request failed for NDC {ndc}: {error}") from error

    status = result.get("ndcStatus", {})
    rxcui = status.get("rxcui")
    name = status.get("conceptName")

    if not rxcui or not name:
        return {
            "name": None,
            "rxcui": None,
            "ndc": ndc,
            "status": "UNKNOWN"
        }

    return {
        "name": name,
        "rxcui": rxcui,
        "ndc": ndc
    }


def decode_medication(record):
    decoded = dict(record)

    decoded["medication"] = decode_ndc(record["ndc"])

    return decoded


def main():
    if len(sys.argv) != 3:
        print(
            f"Usage: {sys.argv[0]} input.json output.json",
            file=sys.stderr
        )
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    with input_path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    decoded = [
        decode_medication(record)
        for record in records
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(decoded, file, indent=4)
        file.write("\n")

    print(f"Decoded {len(decoded)} medication records")
    print(f"Output: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())