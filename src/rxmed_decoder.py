#!/usr/bin/env python3

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path


RXNAV_URL = "http://nginx/REST/ndcstatus.json"
NPPES_URL = "https://npiregistry.cms.hhs.gov/api/"


def get_json(url, parameters, description):
    request_url = url + "?" + urllib.parse.urlencode(parameters)

    try:
        request = urllib.request.Request(
            request_url,
            headers={"User-Agent": "eVigils-RxMed/1.0"}
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)

    except Exception as error:
        raise RuntimeError(f"{description}: {error}") from error


def decode_ndc(ndc):
    result = get_json(
        RXNAV_URL,
        {"ndc": ndc},
        f"RxNav request failed for NDC {ndc}"
    )

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


def provider_name(basic):
    organization = basic.get("organization_name")
    if organization:
        return organization

    parts = [
        basic.get("first_name"),
        basic.get("middle_name"),
        basic.get("last_name")
    ]

    return " ".join(part for part in parts if part) or None


def provider_address(result):
    addresses = result.get("addresses", [])

    address = next(
        (item for item in addresses if item.get("address_purpose") == "LOCATION"),
        None
    )

    if address is None and addresses:
        address = addresses[0]

    if address is None:
        return {}

    return {
        "address_1": address.get("address_1"),
        "address_2": address.get("address_2"),
        "city": address.get("city"),
        "state": address.get("state"),
        "postal_code": address.get("postal_code"),
        "country": address.get("country_name"),
        "phone": address.get("telephone_number")
    }


def provider_specialty(result):
    taxonomies = result.get("taxonomies", [])

    taxonomy = next(
        (item for item in taxonomies if item.get("primary") is True),
        None
    )

    if taxonomy is None and taxonomies:
        taxonomy = taxonomies[0]

    if taxonomy is None:
        return None

    return taxonomy.get("desc")


def decode_npi(identifier):
    identifier = str(identifier) if identifier is not None else ""

    if len(identifier) != 10 or not identifier.isdigit():
        return {
            "identifier": identifier or None,
            "status": "UNKNOWN"
        }

    response = get_json(
        NPPES_URL,
        {
            "version": "2.1",
            "number": identifier
        },
        f"NPPES request failed for NPI {identifier}"
    )

    results = response.get("results", [])
    if not results:
        return {
            "npi": identifier,
            "status": "UNKNOWN"
        }

    result = results[0]
    basic = result.get("basic", {})

    decoded = {
        "npi": result.get("number", identifier),
        "name": provider_name(basic),
        "credential": basic.get("credential"),
        "specialty": provider_specialty(result)
    }

    decoded.update(provider_address(result))

    return decoded


def decode_medication(record, provider_cache):
    decoded = dict(record)

    decoded["medication"] = decode_ndc(record["ndc"])

    prescriber = str(record.get("prescriber_npi", ""))
    pharmacy = str(record.get("pharmacy_npi", ""))

    if prescriber not in provider_cache:
        provider_cache[prescriber] = decode_npi(prescriber)

    if pharmacy not in provider_cache:
        provider_cache[pharmacy] = decode_npi(pharmacy)

    decoded["prescriber"] = provider_cache[prescriber]
    decoded["pharmacy"] = provider_cache[pharmacy]

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

    provider_cache = {}

    decoded = [
        decode_medication(record, provider_cache)
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
