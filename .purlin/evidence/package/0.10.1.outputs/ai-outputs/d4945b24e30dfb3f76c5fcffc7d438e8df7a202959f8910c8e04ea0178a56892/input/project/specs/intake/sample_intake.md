# Feature: sample_intake

> Description: What the receiving bench does with one sample: it refuses a sample it cannot
>   identify, works out the sample's age, flags one that is too old or too warm, and gives each
>   accepted sample an accession number.
> Scope: src/intake.py
> Stack: python/stdlib (re, datetime)
> Highest-Rule: 8
> Highest-Proof: 12

## Rules

- RULE-1: A sample with no barcode, or a barcode of spaces only, is refused with `barcode is required`
- RULE-2: A barcode is `LC-` followed by exactly 8 digits; any other is refused with `barcode <barcode> is not LC- and 8 digits`
- RULE-3: A sample's age is the whole hours between collection and receipt, rounded down
- RULE-4: A sample more than 72 hours old at receipt is stored as `expired`; one exactly 72 hours old is not
- RULE-5: A `frozen` sample received warmer than -20.0 C is stored as `temperature excursion`; one at -20.0 C or colder is not
- RULE-6: A sample received before it was collected is refused with `received before collected`
- RULE-7: Each accepted sample gets the accession number `<site>-<year of receipt>-<sequence>`, the sequence five digits wide and counted from 1 for each site
- RULE-8: A barcode already received is refused with `barcode <barcode> was already received`

## Proof

- PROOF-1 (RULE-1): A sample with the barcode `` (empty) is handed in; it is refused with `barcode is required`
- PROOF-2 (RULE-1): A sample with the barcode of three spaces is handed in; it is refused with `barcode is required`
- PROOF-3 (RULE-2): A sample with the barcode `LC-12345678` is handed in; it is stored with the status `accepted`
- PROOF-4 (RULE-2): A sample with the barcode `LC-1234567`, seven digits, is handed in; it is refused with `barcode LC-1234567 is not LC- and 8 digits`
- PROOF-5 (RULE-3): A sample collected at `2026-03-01T08:00` is received at `2026-03-02T09:30`; its age is `25` hours
- PROOF-6 (RULE-4): A sample collected at `2026-03-01T08:00` is received at `2026-03-04T09:00`, 73 hours later; it is stored as `expired`
- PROOF-7 (RULE-4): A sample collected at `2026-03-01T08:00` is received at `2026-03-04T08:00`, exactly 72 hours later; it is stored as `accepted`
- PROOF-8 (RULE-5): A `frozen` sample is received at `-19.9` C; it is stored as `temperature excursion`
- PROOF-9 (RULE-5): A `frozen` sample is received at `-20.0` C; it is stored as `accepted`
- PROOF-10 (RULE-6): A sample collected at `2026-03-02T08:00` is received at `2026-03-01T08:00`; it is refused with `received before collected`
- PROOF-11 (RULE-7): Two samples from the site `BOS` are received in 2026; the first gets `BOS-2026-00001` and the second `BOS-2026-00002`
- PROOF-12 (RULE-8): The barcode `LC-12345678` is handed in twice; the second is refused with `barcode LC-12345678 was already received`
