# eVigils RxMed

## Purpose

`eVigils-RxMeds` is the medication decoding service used by the eVigils CMS Blue Button medication-history path.

CMSLoader extracts medication fill information from CMS Blue Button PDE data and sends the parsed medication records to RxMed. RxMed converts the identifiers in those records into information suitable for an eVigils patient medication list.

RxMed does not own patient identity, CMS authorization, or patient medication storage.

## Current Processing

For each CMS medication record RxMed:

1. Resolves the NDC against the local RxNav-in-a-Box service.
2. Preserves the RxCUI when RxNav supplies one.
3. Resolves prescriber and pharmacy NPIs through NPPES.
4. Groups known medications by RxCUI.
5. Groups unresolved medications by NDC because equivalence cannot safely be inferred.
6. Keeps the most recent dispense record for each medication.
7. Returns the resulting medication list sorted by most recent dispense date.

The latest retained fill supplies the quantity, days supply, prescriber, pharmacy, and NDC for that medication.

Claim IDs and fill numbers are not part of the patient medication-list output.

RxMed does not attempt to determine whether a medication is currently active or discontinued. CMS PDE data does not provide sufficient information to make that determination.

## Unknown or Unavailable Data

RxMed must never guess a medication identity.

When an NDC cannot be resolved:

```json
{
    "name": "Not provided",
    "rxcui": "",
    "ndc": "00551541928"
}
```

When an NPI cannot be resolved, the original identifier is preserved and the name is returned as `"Not provided"`.

Patient-facing output does not use RxNav status values and does not return `null` for these fields.

## Current Data Sources

RxNav is local to VM423 and is currently accessed through the Docker network:

```text
http://nginx/REST/ndcstatus.json
```

NPPES is currently accessed through:

```text
https://npiregistry.cms.hhs.gov/api/
```

Both services are used only for lookup operations during normal RxMed processing.

## Concurrency

Normal RxMed processing is read-only.

Multiple medication requests may therefore execute concurrently. Request data and decoded medication data must remain request-local; RxMed must not maintain patient-specific processing state.

The RxNav and NPPES endpoints are managed as a synchronized pair. At the beginning of a medication request, RxMed obtains one endpoint snapshot. That request must use the same snapshot for its complete lifetime.

Synchronization protects only reading or replacing the endpoint references. It must not serialize the actual RxNav or NPPES queries.

## Future Dataset / Service Switching

RxNav data will eventually be updated automatically. Future NPPES handling may also change or use a locally maintained data source.

An update must not cause a medication request to use two different data-source versions.

The required behavior is:

```text
Request A starts -> endpoint/data version A -> finishes using A
Request B starts -> endpoint/data version A -> finishes using A

                         switch A -> B

Request C starts -> endpoint/data version B -> finishes using B
Request D starts -> endpoint/data version B -> finishes using B
```

The endpoint switch itself must be synchronized and atomic from the point of view of a new RxMed request.

A request that has already obtained version A must continue to use version A even if the current endpoint is switched to version B while that request is executing.

Therefore the future update mechanism must not destroy or make the old service/data version unavailable until every request holding the old snapshot has completed.

The exact update implementation is intentionally deferred. Possible implementation details include versioned containers/services and reference counting of active endpoint snapshots. The important architectural requirement is that the current RxMed request interface is already based on a request-local endpoint snapshot so this can be implemented without changing medication-processing semantics.

## Current Development Status

The current test fixture is:

```text
Resources/Tests/BBUser00000_meds_parsed.json
```

The test command is:

```bash
./scripts/rxmed-test00000.sh
```

The current test reads 38 CMS medication claims and produces 5 collapsed medication records.

The next implementation stage is to expose the decoder as a persistent service so CMSLoader can submit medication records and receive the decoded medication list directly.
