#!/usr/bin/env python3

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path


RXNAV_URL = "http://nginx/REST/ndcstatus.json"
NPPES_URL = "https://npiregistry.cms.hhs.gov/api/"

_nppes_cache = {}


def get_json(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "eVigils-RxMed/1.0"}
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def decode_ndc(ndc):
    url = RXNAV_URL + "?" + urllib.parse.urlencode({"ndc": ndc})

    try:
        result = get_json(url)

    except Exception as error:
        raise RuntimeError(
            f"RxNav request failed for NDC {ndc}: {error}"
        ) from error

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


def valid_npi(npi):
    return isinstance(npi, str) and len(npi) == 10 and npi.isdigit()


def select_location(addresses):
    if not addresses:
        return None

    for address in addresses:
        if address.get("address_purpose") == "LOCATION":
            return address

    return addresses[0]


def select_taxonomy(taxonomies):
    if not taxonomies:
        return None

    for taxonomy in taxonomies:
        if taxonomy.get("primary"):
            return taxonomy

    return taxonomies[0]


def decode_npi(npi):
    if npi in _nppes_cache:
        return _nppes_cache[npi]

    if not valid_npi(npi):
        result = {
            "npi": npi,
            "status": "UNKNOWN"
        }
        _nppes_cache[npi] = result
        return result

    url = NPPES_URL + "?" + urllib.parse.urlencode({
        "version": "2.1",
        "number": npi
    })

    try:
        response = get_json(url)
    except Exception:
        result = {
            "npi": npi,
            "status": "UNKNOWN"
        }
        _nppes_cache[npi] = result
        return result

    results = response.get("results", [])

    if not results:
        result = {
            "npi": npi,
            "status": "UNKNOWN"
        }
        _nppes_cache[npi] = result
        return result

    provider = results[0]
    basic = provider.get("basic", {})
    enumeration_type = provider.get("enumeration_type")
    address = select_location(provider.get("addresses", []))
    taxonomy = select_taxonomy(provider.get("taxonomies", []))

    result = {
        "npi": npi
    }

    if enumeration_type == "NPI-1":
        parts = [
            basic.get("first_name"),
            basic.get("middle_name"),
            basic.get("last_name")
        ]
        name = " ".join(part for part in parts if part)

        credential = basic.get("credential")
        if credential:
            name = f"{name}, {credential}" if name else credential

        result["name"] = name or None

    elif enumeration_type == "NPI-2":
        result["name"] = basic.get("organization_name")

    else:
        result["name"] = (
            basic.get("organization_name")
            or basic.get("name")
        )

    if taxonomy:
        result["specialty"] = taxonomy.get("desc")

    if address:
        result["address"] = address.get("address_1")
        if address.get("address_2"):
            result["address_2"] = address.get("address_2")
        result["city"] = address.get("city")
        result["state"] = address.get("state")
        result["zip"] = address.get("postal_code")
        result["phone"] = address.get("telephone_number")

    result = {
        key: value
        for key, value in result.items()
        if value is not None
    }

    _nppes_cache[npi] = result
    return result


def decode_claim(record):
    decoded = dict(record)

    decoded["medication"] = decode_ndc(record["ndc"])
    decoded["prescriber"] = decode_npi(record.get("prescriber_npi"))
    decoded["pharmacy"] = decode_npi(record.get("pharmacy_npi"))

    return decoded


def medication_key(record):
    medication = record["medication"]
    rxcui = medication.get("rxcui")

    if rxcui:
        return ("RXCUI", rxcui)

    return ("NDC", medication["ndc"])


def collapse_medications(records):
    latest = {}

    for record in records:
        key = medication_key(record)
        previous = latest.get(key)

        if (
            previous is None
            or record["dispensed_date"] > previous["dispensed_date"]
        ):
            latest[key] = record

    medications = []

    for record in latest.values():
        medications.append({
            "medication": record["medication"],
            "last_dispensed": record["dispensed_date"],
            "quantity": record["quantity"],
            "days_supply": record["days_supply"],
            "prescriber": record["prescriber"],
            "pharmacy": record["pharmacy"]
        })

    medications.sort(
        key=lambda item: item["last_dispensed"],
        reverse=True
    )

    return medications


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

    decoded_claims = [
        decode_claim(record)
        for record in records
    ]

    medications = collapse_medications(decoded_claims)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(medications, file, indent=4)
        file.write("\n")

    print(f"Read {len(records)} medication claims")
    print(f"Produced {len(medications)} medication records")
    print(f"Output: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
