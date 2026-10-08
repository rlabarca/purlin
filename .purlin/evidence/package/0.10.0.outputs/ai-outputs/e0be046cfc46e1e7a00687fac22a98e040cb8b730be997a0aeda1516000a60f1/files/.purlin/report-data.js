const PURLIN_DATA = {
  "branch": "main",
  "commit": "7ea32d8bbaa4632375312258192dc566c413255c",
  "dirty": false,
  "evidence": {
    "sample_intake": {
      "local": {
        "macos": {
          "at": "2026-10-07T22:06:28Z",
          "commit": "7ea32d8bbaa4632375312258192dc566c413255c",
          "current": true,
          "path": ".purlin/evidence/local/sample_intake.json",
          "result": "pass"
        }
      }
    }
  },
  "features": [
    {
      "broken": [],
      "category": "intake",
      "current": true,
      "description": "What the receiving bench does with one sample: it refuses a sample it cannot identify, works out the sample's age, flags one that is too old or too warm, and gives each accepted sample an accession number.",
      "evidence": {
        "ci": null,
        "local": {
          "committed": false,
          "path": ".purlin/evidence/local/sample_intake.json",
          "platforms": {
            "macos": {
              "at": "2026-10-07T22:06:28Z",
              "commit": "7ea32d8bbaa4632375312258192dc566c413255c",
              "current": true
            }
          }
        }
      },
      "incomplete": false,
      "incomplete_reason": null,
      "is_anchor": false,
      "name": "sample_intake",
      "pinned": null,
      "rollup": {
        "audit_out_of_date": 0,
        "by_hand": 0,
        "failing": 0,
        "incomplete": false,
        "manual": 0,
        "not_audited": 0,
        "partial": 0,
        "passed": 8,
        "proofs": 12,
        "proofs_without_test": 0,
        "proofs_without_test_ids": [],
        "rules": 8,
        "spot_checked": 0,
        "strong": 4,
        "untested": 0,
        "weak": 4
      },
      "rules": [
        {
          "audit": {
            "at": "2026-10-07T22:07:08Z",
            "bugs": {
              "PROOF-1": {
                "after": "        if barcode is None or (barcode and not barcode.strip()):",
                "aim": "plain",
                "before": "        if barcode is None or not barcode.strip():",
                "bug_key": "2b2ae76e97c37b9c0634cb0dc7deaa35ea78831d5db8ef32ed66e940e2c32dbd",
                "case": "a sample with the empty barcode is handed in; the proof says it is refused with `barcode is required`; the changed code refuses it with `barcode  is not LC- and 8 digits`",
                "file": "src/intake.py",
                "line": 30,
                "result": "caught",
                "why": ""
              },
              "PROOF-2": {
                "after": "        if barcode is None or not barcode:",
                "aim": "plain",
                "before": "        if barcode is None or not barcode.strip():",
                "bug_key": "82a466ea8a73d753c94b4c51ea95c85ef5ee7e3fb74ffac8e5cb1aef5b739633",
                "case": "a sample with a barcode of three spaces is handed in; the proof says it is refused with `barcode is required`; the changed code refuses it with `barcode     is not LC- and 8 digits`",
                "file": "src/intake.py",
                "line": 30,
                "result": "caught",
                "why": ""
              }
            },
            "commit": "7ea32d8bbaa4632375312258192dc566c413255c",
            "explanation": [
              "PROOF-1: the test hands in the empty barcode, expects the refusal and compares its whole message with `barcode is required`, so it observes the case and the value the proof names.",
              "PROOF-2: the test hands in a barcode of three spaces, expects the refusal and compares its whole message with `barcode is required`, so it observes the case and the value the proof names.",
              "The spot tests found nothing, and both tests take their expected message from a literal and not from the code.",
              "The rule also speaks of a sample with no barcode at all, and neither proof hands in a sample whose barcode is missing rather than empty."
            ],
            "findings": [],
            "model": "claude-opus-5-5",
            "no_bug": [],
            "notes": [],
            "out_of_date": [],
            "path": ".purlin/evidence/local/sample_intake.json",
            "verdict": "strong"
          },
          "bucket": "passed",
          "carried": {},
          "cells": {
            "passed": {
              "counts": true,
              "current": true,
              "missing_env": [],
              "missing_models": [],
              "nothing_to_check": [],
              "platforms": {
                "macos": {
                  "at": "2026-10-07T22:06:28Z",
                  "source": "local",
                  "word": "passed"
                }
              },
              "reasons": [],
              "source": "local",
              "word": "passed"
            },
            "strong": {
              "evidence": ".purlin/evidence/local/sample_intake.json",
              "findings": [],
              "reasons": [],
              "word": "strong"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": false,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
            "strong": true,
            "weak": false
          },
          "id": "RULE-1",
          "left": null,
          "machines": {
            "macos": "Richs-MacBook-Pro.local"
          },
          "proof_hash": "cfa328471c72bcdf104dce36452f50d73764f5b910336e46b6c297d025d00242",
          "proofs": [
            {
              "ai": [],
              "carried": {},
              "env": null,
              "graded": null,
              "id": "PROOF-1",
              "manual": false,
              "models": [],
              "result": "passed",
              "runs": null,
              "slow": false,
              "tests": [
                {
                  "file": "tests/test_intake.py",
                  "name": "test_an_empty_barcode_is_refused",
                  "result": "pass"
                }
              ],
              "text": "A sample with the barcode `` (empty) is handed in; it is refused with `barcode is required`"
            },
            {
              "ai": [],
              "carried": {},
              "env": null,
              "graded": null,
              "id": "PROOF-2",
              "manual": false,
              "models": [],
              "result": "passed",
              "runs": null,
              "slow": false,
              "tests": [
                {
                  "file": "tests/test_intake.py",
                  "name": "test_a_barcode_of_spaces_is_refused",
                  "result": "pass"
                }
              ],
              "text": "A sample with the barcode of three spaces is handed in; it is refused with `barcode is required`"
            }
          ],
          "rule_hash": "717e2209592ab202cf255da93eead3115b5a0e47818f2ae74c73a6a9387cd800",
          "test_hash": "d76ef5900a0ffc1f94847092db89a0dd98941dea8e500cd0e9b19d57de0af0c7",
          "test_hash_kind": "test",
          "tests": [],
          "text": "A sample with no barcode, or a barcode of spaces only, is refused with `barcode is required`"
        },
        {
          "audit": {
            "at": "2026-10-07T22:07:08Z",
            "bugs": {
              "PROOF-3": {
                "after": "        self.received[barcode] = dict(record, status='received')",
                "aim": "past the test",
                "before": "        self.received[barcode] = record",
                "bug_key": "52b4f3abef5ca195b65c9921c08b70c130961db6cd3c4a2c9c302752a86a85e8",
                "case": "a sample with the barcode LC-12345678 is handed in; the proof says it is stored with the status accepted; the changed code stores it with the status received",
                "file": "src/intake.py",
                "line": 52,
                "result": "survived",
                "test_key": "5e02b4541f7a210ccd5d6a945686a03eeefad30668d5be574e907645730fd944",
                "why": ""
              },
              "PROOF-4": {
                "after": "BARCODE = re.compile(r'^LC-\\d{7,8}$')",
                "aim": "plain",
                "before": "BARCODE = re.compile(r'^LC-\\d{8}$')",
                "bug_key": "5bf11b150c2a3db38633c3e2514979a6d267ea149d4960aa604c7fa3f0bd0dc9",
                "case": "a sample with the seven-digit barcode LC-1234567 is handed in; the proof says it is refused with barcode LC-1234567 is not LC- and 8 digits; the changed code accepts it and refuses nothing",
                "file": "src/intake.py",
                "line": 5,
                "result": "caught",
                "why": ""
              }
            },
            "commit": "7ea32d8bbaa4632375312258192dc566c413255c",
            "explanation": [
              "PROOF-3: the test hands in `LC-12345678` and compares the status of the record the intake returns with `accepted`, and it never reads what the bench stored, so a stored record with another status still passes.",
              "PROOF-4: the test hands in the seven-digit barcode `LC-1234567`, expects a refusal and compares the whole message with the one the proof names, so a sample that is accepted or refused with other words fails it.",
              "The spot tests found nothing, and each test does compare a value its proof names, so they miss only that PROOF-3's test reads the returned record and not the stored one."
            ],
            "findings": [
              "PROOF-3: the test still passes when src/intake.py:52 reads \"self.received[barcode] = dict(record, status='received')\"",
              "PROOF-3: the AI says this breaks: a sample with the barcode LC-12345678 is handed in; the proof says it is stored with the status accepted; the changed code stores it with the status received"
            ],
            "model": "claude-opus-5-5",
            "no_bug": [],
            "notes": [],
            "out_of_date": [],
            "path": ".purlin/evidence/local/sample_intake.json",
            "verdict": "weak"
          },
          "bucket": "passed",
          "carried": {},
          "cells": {
            "passed": {
              "counts": true,
              "current": true,
              "missing_env": [],
              "missing_models": [],
              "nothing_to_check": [],
              "platforms": {
                "macos": {
                  "at": "2026-10-07T22:06:28Z",
                  "source": "local",
                  "word": "passed"
                }
              },
              "reasons": [],
              "source": "local",
              "word": "passed"
            },
            "strong": {
              "evidence": ".purlin/evidence/local/sample_intake.json",
              "findings": [
                "PROOF-3: the test still passes when src/intake.py:52 reads \"self.received[barcode] = dict(record, status='received')\"",
                "PROOF-3: the AI says this breaks: a sample with the barcode LC-12345678 is handed in; the proof says it is stored with the status accepted; the changed code stores it with the status received"
              ],
              "reasons": [
                "PROOF-3: the test still passes when src/intake.py:52 reads \"self.received[barcode] = dict(record, status='received')\"",
                "PROOF-3: the AI says this breaks: a sample with the barcode LC-12345678 is handed in; the proof says it is stored with the status accepted; the changed code stores it with the status received"
              ],
              "word": "weak"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": false,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
            "strong": false,
            "weak": true
          },
          "id": "RULE-2",
          "left": "to_strengthen",
          "machines": {
            "macos": "Richs-MacBook-Pro.local"
          },
          "proof_hash": "87ec580d6901a3f23e21e028a2065397e29a3bd9a543537f706ce1d86d1d11a3",
          "proofs": [
            {
              "ai": [],
              "carried": {},
              "env": null,
              "graded": null,
              "id": "PROOF-3",
              "manual": false,
              "models": [],
              "result": "passed",
              "runs": null,
              "slow": false,
              "tests": [
                {
                  "file": "tests/test_intake.py",
                  "name": "test_eight_digits_are_accepted",
                  "result": "pass"
                }
              ],
              "text": "A sample with the barcode `LC-12345678` is handed in; it is stored with the status `accepted`"
            },
            {
              "ai": [],
              "carried": {},
              "env": null,
              "graded": null,
              "id": "PROOF-4",
              "manual": false,
              "models": [],
              "result": "passed",
              "runs": null,
              "slow": false,
              "tests": [
                {
                  "file": "tests/test_intake.py",
                  "name": "test_seven_digits_are_refused",
                  "result": "pass"
                }
              ],
              "text": "A sample with the barcode `LC-1234567`, seven digits, is handed in; it is refused with `barcode LC-1234567 is not LC- and 8 digits`"
            }
          ],
          "rule_hash": "533a032619c3daf45c3ef5b9e79b55a4d7c0ed839d7330b9a2c107bec09f2de1",
          "test_hash": "e911a7cd4450ec194831493379c67d32db0cd0dcb734a6b93c532210939a73b4",
          "test_hash_kind": "test",
          "tests": [],
          "text": "A barcode is `LC-` followed by exactly 8 digits; any other is refused with `barcode <barcode> is not LC- and 8 digits`"
        },
        {
          "audit": {
            "at": "2026-10-07T22:07:08Z",
            "bugs": {
              "PROOF-5": {
                "after": "    return round(seconds / 3600)",
                "aim": "past the test",
                "before": "    return int(seconds // 3600)",
                "bug_key": "1dc970279f6b61523c8ff4e416d1b2c80c8923c55706949f184aacf8aafac544",
                "case": "a sample collected 2026-03-01T08:00 and received 2026-03-02T09:30; the proof says its age is 25 hours; the changed code gives 26",
                "file": "src/intake.py",
                "line": 17,
                "result": "survived",
                "test_key": "fd5623f6a7e09317a54476ccb09b284a6623b4bed03c85c055ffe6a54925240d",
                "why": ""
              }
            },
            "commit": "7ea32d8bbaa4632375312258192dc566c413255c",
            "explanation": [
              "PROOF-5: the test takes in the sample the proof names, but compares the record's age with what age_hours() returns for the same two times, not with the proof's 25.",
              "PROOF-5: intake() gets its age from age_hours(), so a change to how the hours are rounded moves both sides of the comparison together and the test still passes.",
              "PROOF-5: the spot tests found nothing because the test asserts on intake()'s record and takes the expected value from a different function, age_hours(), although that function is the code that holds the rule."
            ],
            "findings": [
              "PROOF-5: the test still passes when src/intake.py:17 reads \"return round(seconds / 3600)\"",
              "PROOF-5: the AI says this breaks: a sample collected 2026-03-01T08:00 and received 2026-03-02T09:30; the proof says its age is 25 hours; the changed code gives 26"
            ],
            "model": "claude-opus-5-5",
            "no_bug": [],
            "notes": [],
            "out_of_date": [],
            "path": ".purlin/evidence/local/sample_intake.json",
            "verdict": "weak"
          },
          "bucket": "passed",
          "carried": {},
          "cells": {
            "passed": {
              "counts": true,
              "current": true,
              "missing_env": [],
              "missing_models": [],
              "nothing_to_check": [],
              "platforms": {
                "macos": {
                  "at": "2026-10-07T22:06:28Z",
                  "source": "local",
                  "word": "passed"
                }
              },
              "reasons": [],
              "source": "local",
              "word": "passed"
            },
            "strong": {
              "evidence": ".purlin/evidence/local/sample_intake.json",
              "findings": [
                "PROOF-5: the test still passes when src/intake.py:17 reads \"return round(seconds / 3600)\"",
                "PROOF-5: the AI says this breaks: a sample collected 2026-03-01T08:00 and received 2026-03-02T09:30; the proof says its age is 25 hours; the changed code gives 26"
              ],
              "reasons": [
                "PROOF-5: the test still passes when src/intake.py:17 reads \"return round(seconds / 3600)\"",
                "PROOF-5: the AI says this breaks: a sample collected 2026-03-01T08:00 and received 2026-03-02T09:30; the proof says its age is 25 hours; the changed code gives 26"
              ],
              "word": "weak"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": false,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
            "strong": false,
            "weak": true
          },
          "id": "RULE-3",
          "left": "to_strengthen",
          "machines": {
            "macos": "Richs-MacBook-Pro.local"
          },
          "proof_hash": "f0707b934ef616be87b0ca4ace6a030affbc7624207aa49b1f239c9988318573",
          "proofs": [
            {
              "ai": [],
              "carried": {},
              "env": null,
              "graded": null,
              "id": "PROOF-5",
              "manual": false,
              "models": [],
              "result": "passed",
              "runs": null,
              "slow": false,
              "tests": [
                {
                  "file": "tests/test_intake.py",
                  "name": "test_age_is_whole_hours",
                  "result": "pass"
                }
              ],
              "text": "A sample collected at `2026-03-01T08:00` is received at `2026-03-02T09:30`; its age is `25` hours"
            }
          ],
          "rule_hash": "327f24dc4a33ea49e3a44f28174158f467f3f421121cc8e88fb85db8772688c8",
          "test_hash": "b592b4f2ae81f99d818fbb9f1fd9931d3d7577e830bf5ade51c004f87781c8ae",
          "test_hash_kind": "test",
          "tests": [],
          "text": "A sample's age is the whole hours between collection and receipt, rounded down"
        },
        {
          "audit": {
            "at": "2026-10-07T22:07:08Z",
            "bugs": {
              "PROOF-6": {
                "after": "        if age > MAX_AGE_HOURS + 1:",
                "aim": "plain",
                "before": "        if age > MAX_AGE_HOURS:",
                "bug_key": "37989b10ab8f0f969ad5855469553a1f2d466b593d9a9fbb39ec1ae50b088080",
                "case": "a sample collected at 2026-03-01T08:00 and received at 2026-03-04T09:00, 73 hours later; the proof says it is stored as expired; the changed code stores it as accepted",
                "file": "src/intake.py",
                "line": 40,
                "result": "caught",
                "why": ""
              },
              "PROOF-7": {
                "after": "        if age >= MAX_AGE_HOURS:",
                "aim": "past the test",
                "before": "        if age > MAX_AGE_HOURS:",
                "bug_key": "38e32c5d42187b0575d793209c19731319f4b025053c28ffe4ec1d7f689b9b53",
                "case": "a sample collected at 2026-03-01T08:00 and received at 2026-03-04T08:00, exactly 72 hours later; the proof says it is stored as accepted; the changed code stores it as expired",
                "file": "src/intake.py",
                "line": 40,
                "result": "survived",
                "test_key": "28beb7a6f940377fbd62866e904e092b0fd82683e4e03199f9cd49949cc8a5a4",
                "why": ""
              }
            },
            "commit": "7ea32d8bbaa4632375312258192dc566c413255c",
            "explanation": [
              "PROOF-6: the test receives the sample at 2026-03-04T09:00, 73 hours after collection, and compares the stored status with expired, which is the proof's case and its result.",
              "PROOF-7: the test receives the sample at 2026-03-04T07:00, 71 hours after collection, not at the 2026-03-04T08:00 the proof names, so it never observes a sample exactly 72 hours old.",
              "PROOF-7: a limit that expires a sample at exactly 72 hours still passes this test, because a 71-hour sample is accepted either way.",
              "RULE-4: the 72-hour boundary the rule states is checked from the expired side only, at 73 hours, and the accepted side is checked one hour short of it."
            ],
            "findings": [
              "PROOF-7: the test still passes when src/intake.py:40 reads \"if age >= MAX_AGE_HOURS:\"",
              "PROOF-7: the AI says this breaks: a sample collected at 2026-03-01T08:00 and received at 2026-03-04T08:00, exactly 72 hours later; the proof says it is stored as accepted; the changed code stores it as expired"
            ],
            "model": "claude-opus-5-5",
            "no_bug": [],
            "notes": [],
            "out_of_date": [],
            "path": ".purlin/evidence/local/sample_intake.json",
            "verdict": "weak"
          },
          "bucket": "passed",
          "carried": {},
          "cells": {
            "passed": {
              "counts": true,
              "current": true,
              "missing_env": [],
              "missing_models": [],
              "nothing_to_check": [],
              "platforms": {
                "macos": {
                  "at": "2026-10-07T22:06:28Z",
                  "source": "local",
                  "word": "passed"
                }
              },
              "reasons": [],
              "source": "local",
              "word": "passed"
            },
            "strong": {
              "evidence": ".purlin/evidence/local/sample_intake.json",
              "findings": [
                "PROOF-7: the test still passes when src/intake.py:40 reads \"if age >= MAX_AGE_HOURS:\"",
                "PROOF-7: the AI says this breaks: a sample collected at 2026-03-01T08:00 and received at 2026-03-04T08:00, exactly 72 hours later; the proof says it is stored as accepted; the changed code stores it as expired"
              ],
              "reasons": [
                "PROOF-7: the test still passes when src/intake.py:40 reads \"if age >= MAX_AGE_HOURS:\"",
                "PROOF-7: the AI says this breaks: a sample collected at 2026-03-01T08:00 and received at 2026-03-04T08:00, exactly 72 hours later; the proof says it is stored as accepted; the changed code stores it as expired"
              ],
              "word": "weak"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": false,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
            "strong": false,
            "weak": true
          },
          "id": "RULE-4",
          "left": "to_strengthen",
          "machines": {
            "macos": "Richs-MacBook-Pro.local"
          },
          "proof_hash": "39145f8b511425424f9585f309d17e7bfd0e3186a30442e970b031ab6b749ddc",
          "proofs": [
            {
              "ai": [],
              "carried": {},
              "env": null,
              "graded": null,
              "id": "PROOF-6",
              "manual": false,
              "models": [],
              "result": "passed",
              "runs": null,
              "slow": false,
              "tests": [
                {
                  "file": "tests/test_intake.py",
                  "name": "test_73_hours_is_expired",
                  "result": "pass"
                }
              ],
              "text": "A sample collected at `2026-03-01T08:00` is received at `2026-03-04T09:00`, 73 hours later; it is stored as `expired`"
            },
            {
              "ai": [],
              "carried": {},
              "env": null,
              "graded": null,
              "id": "PROOF-7",
              "manual": false,
              "models": [],
              "result": "passed",
              "runs": null,
              "slow": false,
              "tests": [
                {
                  "file": "tests/test_intake.py",
                  "name": "test_72_hours_is_accepted",
                  "result": "pass"
                }
              ],
              "text": "A sample collected at `2026-03-01T08:00` is received at `2026-03-04T08:00`, exactly 72 hours later; it is stored as `accepted`"
            }
          ],
          "rule_hash": "dfc3398f228e3423e0e90ec7b5abbea807818a8f4573f5e8434f1a46b2a4e019",
          "test_hash": "5818142b3155b47851e9ecad8057f75b9ae8bd3fec55b290f0f315b5af737aa1",
          "test_hash_kind": "test",
          "tests": [],
          "text": "A sample more than 72 hours old at receipt is stored as `expired`; one exactly 72 hours old is not"
        },
        {
          "audit": {
            "at": "2026-10-07T22:07:08Z",
            "bugs": {
              "PROOF-8": {
                "after": "FROZEN_MAX_C = -19.0",
                "aim": "plain",
                "before": "FROZEN_MAX_C = -20.0",
                "bug_key": "169273e3468407bb8144f335701dbbc46a76d2c270f9d3fecb09d9507160bbf5",
                "case": "a frozen sample received at -19.9 C; the proof says it is stored as temperature excursion; the changed code stores it as accepted",
                "file": "src/intake.py",
                "line": 7,
                "result": "caught",
                "why": ""
              },
              "PROOF-9": {
                "after": "                and temperature_c >= FROZEN_MAX_C:",
                "aim": "plain",
                "before": "                and temperature_c > FROZEN_MAX_C:",
                "bug_key": "4504af421d948eb22a09e8e089808cf2b498b4eeb492c9866dbdb51cd5cac768",
                "case": "a frozen sample received at -20.0 C; the proof says it is stored as accepted; the changed code stores it as temperature excursion",
                "file": "src/intake.py",
                "line": 43,
                "result": "caught",
                "why": ""
              }
            },
            "commit": "7ea32d8bbaa4632375312258192dc566c413255c",
            "explanation": [
              "PROOF-8: the test receives a frozen sample at -19.9 C and compares the returned record's status with `temperature excursion`, which is the case and the value the proof names.",
              "PROOF-9: the test receives a frozen sample at -20.0 C and compares the returned record's status with `accepted`, which is the boundary and the value the proof names.",
              "PROOF-8 and PROOF-9: both tests read the record that intake returns and not the one the bench keeps, so a difference between the two would go unseen.",
              "The spot tests found nothing, and each test holds one failable comparison against a literal taken from its proof."
            ],
            "findings": [],
            "model": "claude-opus-5-5",
            "no_bug": [],
            "notes": [],
            "out_of_date": [],
            "path": ".purlin/evidence/local/sample_intake.json",
            "verdict": "strong"
          },
          "bucket": "passed",
          "carried": {},
          "cells": {
            "passed": {
              "counts": true,
              "current": true,
              "missing_env": [],
              "missing_models": [],
              "nothing_to_check": [],
              "platforms": {
                "macos": {
                  "at": "2026-10-07T22:06:28Z",
                  "source": "local",
                  "word": "passed"
                }
              },
              "reasons": [],
              "source": "local",
              "word": "passed"
            },
            "strong": {
              "evidence": ".purlin/evidence/local/sample_intake.json",
              "findings": [],
              "reasons": [],
              "word": "strong"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": false,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
            "strong": true,
            "weak": false
          },
          "id": "RULE-5",
          "left": null,
          "machines": {
            "macos": "Richs-MacBook-Pro.local"
          },
          "proof_hash": "1e7f78654553b9ae9de8921fdf56ee9bb14a7b24eb746ea3bc66e2f46d761b1f",
          "proofs": [
            {
              "ai": [],
              "carried": {},
              "env": null,
              "graded": null,
              "id": "PROOF-8",
              "manual": false,
              "models": [],
              "result": "passed",
              "runs": null,
              "slow": false,
              "tests": [
                {
                  "file": "tests/test_intake.py",
                  "name": "test_a_warm_frozen_sample_is_an_excursion",
                  "result": "pass"
                }
              ],
              "text": "A `frozen` sample is received at `-19.9` C; it is stored as `temperature excursion`"
            },
            {
              "ai": [],
              "carried": {},
              "env": null,
              "graded": null,
              "id": "PROOF-9",
              "manual": false,
              "models": [],
              "result": "passed",
              "runs": null,
              "slow": false,
              "tests": [
                {
                  "file": "tests/test_intake.py",
                  "name": "test_a_frozen_sample_at_minus_20_is_accepted",
                  "result": "pass"
                }
              ],
              "text": "A `frozen` sample is received at `-20.0` C; it is stored as `accepted`"
            }
          ],
          "rule_hash": "9ab3acd59d1d3bac1b240ac0a133a451bfe7adeae5362df0d5eeca5147060822",
          "test_hash": "923f14c6f1082e59768aa7c85d3389128e7aae8209e81a94d219028c0353ab3c",
          "test_hash_kind": "test",
          "tests": [],
          "text": "A `frozen` sample received warmer than -20.0 C is stored as `temperature excursion`; one at -20.0 C or colder is not"
        },
        {
          "audit": {
            "at": "2026-10-07T22:07:08Z",
            "bugs": {
              "PROOF-10": {
                "after": "            raise IntakeError('received before collection')",
                "aim": "plain",
                "before": "            raise IntakeError('received before collected')",
                "bug_key": "51a6e4ea92b5d7e04e9612b25c1b6b6ad7f0bbb3120ece831162af3af3a2dd5c",
                "case": "a sample collected at 2026-03-02T08:00 and received at 2026-03-01T08:00; the proof says it is refused with received before collected; the changed code refuses it with received before collection",
                "file": "src/intake.py",
                "line": 37,
                "result": "caught",
                "why": ""
              }
            },
            "commit": "7ea32d8bbaa4632375312258192dc566c413255c",
            "explanation": [
              "PROOF-10: the test takes in a sample collected at 2026-03-02T08:00 and received at 2026-03-01T08:00, expects a refusal and compares its whole message with `received before collected`, which is the case and the result the proof names.",
              "PROOF-10: a sample that is accepted instead, or refused with any other message, fails the test, so the test leaves no way past it and the planted change is the plainest one.",
              "The spot tests found nothing, and the test holds an exact comparison on a literal taken from the proof, not from the code."
            ],
            "findings": [],
            "model": "claude-opus-5-5",
            "no_bug": [],
            "notes": [],
            "out_of_date": [],
            "path": ".purlin/evidence/local/sample_intake.json",
            "verdict": "strong"
          },
          "bucket": "passed",
          "carried": {},
          "cells": {
            "passed": {
              "counts": true,
              "current": true,
              "missing_env": [],
              "missing_models": [],
              "nothing_to_check": [],
              "platforms": {
                "macos": {
                  "at": "2026-10-07T22:06:28Z",
                  "source": "local",
                  "word": "passed"
                }
              },
              "reasons": [],
              "source": "local",
              "word": "passed"
            },
            "strong": {
              "evidence": ".purlin/evidence/local/sample_intake.json",
              "findings": [],
              "reasons": [],
              "word": "strong"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": false,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
            "strong": true,
            "weak": false
          },
          "id": "RULE-6",
          "left": null,
          "machines": {
            "macos": "Richs-MacBook-Pro.local"
          },
          "proof_hash": "e33464d4f4c1c4f10d1164ad40da6febcc2f8acabc8cad822ad398e06cc411fe",
          "proofs": [
            {
              "ai": [],
              "carried": {},
              "env": null,
              "graded": null,
              "id": "PROOF-10",
              "manual": false,
              "models": [],
              "result": "passed",
              "runs": null,
              "slow": false,
              "tests": [
                {
                  "file": "tests/test_intake.py",
                  "name": "test_received_before_collected_is_refused",
                  "result": "pass"
                }
              ],
              "text": "A sample collected at `2026-03-02T08:00` is received at `2026-03-01T08:00`; it is refused with `received before collected`"
            }
          ],
          "rule_hash": "7727dc52ba9e80d4f21903a3bd9a3882fcd3adeb2e880b65ccbcb275e50524b3",
          "test_hash": "1f357c8b93a6d1b2a7a3a68078e03f17ddc4a6cb02ded0379bbc6f6c5db64f16",
          "test_hash_kind": "test",
          "tests": [],
          "text": "A sample received before it was collected is refused with `received before collected`"
        },
        {
          "audit": {
            "at": "2026-10-07T22:07:08Z",
            "bugs": {
              "PROOF-11": {
                "after": "            accession = '%s-%d-%04d' % (site, received.year, number)",
                "aim": "past the test",
                "before": "            accession = '%s-%d-%05d' % (site, received.year, number)",
                "bug_key": "c4988b10c2f1092d14880c9f5dc19b9db8e332a6ef0634a9885ee0c4fa2a61b2",
                "case": "two samples from the site BOS received in 2026; the proof says BOS-2026-00001 then BOS-2026-00002; the changed code gives BOS-2026-0001 then BOS-2026-0002",
                "file": "src/intake.py",
                "line": 49,
                "result": "survived",
                "test_key": "5d12aa941db70988972c724f5bd27e013f1058bad30d10fc0ef864bd9bde781c",
                "why": ""
              }
            },
            "commit": "7ea32d8bbaa4632375312258192dc566c413255c",
            "explanation": [
              "PROOF-11: the test receives two BOS samples and prints both accession numbers, but compares neither with `BOS-2026-00001` or `BOS-2026-00002`, so any accession number, or none, still passes.",
              "The finding \"the test checks nothing\" holds: the body has no assertion and calls no helper that could assert, so the test fails only if intake raises an error.",
              "PROOF-11: the test never shows that the times it passes fall in 2026, so the year part of the number is not observed either."
            ],
            "findings": [
              "tests/test_intake.py::test_accession_numbers_count_up: the test checks nothing.",
              "PROOF-11: the test still passes when src/intake.py:49 reads \"accession = '%s-%d-%04d' % (site, received.year, number)\"",
              "PROOF-11: the AI says this breaks: two samples from the site BOS received in 2026; the proof says BOS-2026-00001 then BOS-2026-00002; the changed code gives BOS-2026-0001 then BOS-2026-0002"
            ],
            "model": "claude-opus-5-5",
            "no_bug": [],
            "notes": [
              "PROOF-11 names no failure case or boundary, such as a second site starting again at 1 or a sample that is not accepted getting no number, so the rule's \"for each site\" and \"accepted\" are proved in one direction only."
            ],
            "out_of_date": [],
            "path": ".purlin/evidence/local/sample_intake.json",
            "verdict": "weak"
          },
          "bucket": "passed",
          "carried": {},
          "cells": {
            "passed": {
              "counts": true,
              "current": true,
              "missing_env": [],
              "missing_models": [],
              "nothing_to_check": [],
              "platforms": {
                "macos": {
                  "at": "2026-10-07T22:06:28Z",
                  "source": "local",
                  "word": "passed"
                }
              },
              "reasons": [],
              "source": "local",
              "word": "passed"
            },
            "strong": {
              "evidence": ".purlin/evidence/local/sample_intake.json",
              "findings": [
                "tests/test_intake.py::test_accession_numbers_count_up: the test checks nothing.",
                "PROOF-11: the test still passes when src/intake.py:49 reads \"accession = '%s-%d-%04d' % (site, received.year, number)\"",
                "PROOF-11: the AI says this breaks: two samples from the site BOS received in 2026; the proof says BOS-2026-00001 then BOS-2026-00002; the changed code gives BOS-2026-0001 then BOS-2026-0002"
              ],
              "reasons": [
                "tests/test_intake.py::test_accession_numbers_count_up: the test checks nothing.",
                "PROOF-11: the test still passes when src/intake.py:49 reads \"accession = '%s-%d-%04d' % (site, received.year, number)\"",
                "PROOF-11: the AI says this breaks: two samples from the site BOS received in 2026; the proof says BOS-2026-00001 then BOS-2026-00002; the changed code gives BOS-2026-0001 then BOS-2026-0002"
              ],
              "word": "weak"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": false,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
            "strong": false,
            "weak": true
          },
          "id": "RULE-7",
          "left": "to_strengthen",
          "machines": {
            "macos": "Richs-MacBook-Pro.local"
          },
          "proof_hash": "90327c47cbcee495ff380c7e7962cf47b944f168a179ecba560d3fce6ea09e69",
          "proofs": [
            {
              "ai": [],
              "carried": {},
              "env": null,
              "graded": null,
              "id": "PROOF-11",
              "manual": false,
              "models": [],
              "result": "passed",
              "runs": null,
              "slow": false,
              "tests": [
                {
                  "file": "tests/test_intake.py",
                  "name": "test_accession_numbers_count_up",
                  "result": "pass"
                }
              ],
              "text": "Two samples from the site `BOS` are received in 2026; the first gets `BOS-2026-00001` and the second `BOS-2026-00002`"
            }
          ],
          "rule_hash": "2b0158213571b9cdbaac666e3436f794ee3898e68db6f02f9ef791985ce36cf4",
          "test_hash": "784ac4e6c68e504baccfa3e667ea7c077ad77487dd0cd5f603eba417946833b5",
          "test_hash_kind": "test",
          "tests": [],
          "text": "Each accepted sample gets the accession number `<site>-<year of receipt>-<sequence>`, the sequence five digits wide and counted from 1 for each site"
        },
        {
          "audit": {
            "at": "2026-10-07T22:07:08Z",
            "bugs": {
              "PROOF-12": {
                "after": "            raise IntakeError('barcode %s is already received' % barcode)",
                "aim": "plain",
                "before": "            raise IntakeError('barcode %s was already received' % barcode)",
                "bug_key": "0540a1e79104dc57d965cdbdc7fc3724ab39f9796fb27087c41c668797d87acb",
                "case": "the barcode LC-12345678 handed in twice; the proof says the second is refused with `barcode LC-12345678 was already received`; the changed code refuses it with `barcode LC-12345678 is already received`",
                "file": "src/intake.py",
                "line": 35,
                "result": "caught",
                "why": ""
              }
            },
            "commit": "7ea32d8bbaa4632375312258192dc566c413255c",
            "explanation": [
              "PROOF-12: the test hands in `LC-12345678` twice, expects the second to raise an intake error and compares the error's whole message with the literal `barcode LC-12345678 was already received`, which is the case and the result the proof names.",
              "PROOF-12: the expected message is a literal written in the test and not taken from the code, so a second intake that is accepted, or refused with any other wording, fails the test.",
              "PROOF-12: the spot tests found nothing, and the test leaves no way past it, since it reads both the refusal and its exact message."
            ],
            "findings": [],
            "model": "claude-opus-5-5",
            "no_bug": [],
            "notes": [],
            "out_of_date": [],
            "path": ".purlin/evidence/local/sample_intake.json",
            "verdict": "strong"
          },
          "bucket": "passed",
          "carried": {},
          "cells": {
            "passed": {
              "counts": true,
              "current": true,
              "missing_env": [],
              "missing_models": [],
              "nothing_to_check": [],
              "platforms": {
                "macos": {
                  "at": "2026-10-07T22:06:28Z",
                  "source": "local",
                  "word": "passed"
                }
              },
              "reasons": [],
              "source": "local",
              "word": "passed"
            },
            "strong": {
              "evidence": ".purlin/evidence/local/sample_intake.json",
              "findings": [],
              "reasons": [],
              "word": "strong"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": false,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
            "strong": true,
            "weak": false
          },
          "id": "RULE-8",
          "left": null,
          "machines": {
            "macos": "Richs-MacBook-Pro.local"
          },
          "proof_hash": "65a7b0038c96b7ed55049db07b1433044718ae9a3400e669a8fbf29fb3bada3f",
          "proofs": [
            {
              "ai": [],
              "carried": {},
              "env": null,
              "graded": null,
              "id": "PROOF-12",
              "manual": false,
              "models": [],
              "result": "passed",
              "runs": null,
              "slow": false,
              "tests": [
                {
                  "file": "tests/test_intake.py",
                  "name": "test_a_barcode_received_twice_is_refused",
                  "result": "pass"
                }
              ],
              "text": "The barcode `LC-12345678` is handed in twice; the second is refused with `barcode LC-12345678 was already received`"
            }
          ],
          "rule_hash": "2968ad68626b3c79681bde638d5fd7280d376e7ae2d03e7975fcf79dc6713d54",
          "test_hash": "15e19cfd8423f2f4ef074bf3625829b8f7f357649b4b252e83da52356cdf9702",
          "test_hash_kind": "test",
          "tests": [],
          "text": "A barcode already received is refused with `barcode <barcode> was already received`"
        }
      ],
      "scope": [
        "src/intake.py"
      ],
      "source": null,
      "source_path": null,
      "spec_path": "specs/intake/sample_intake.md"
    }
  ],
  "generated_at": "2026-10-07T22:07:09Z",
  "generated_by": "sync_status",
  "information": [],
  "last_line": null,
  "left": [
    {
      "command": "purlin:test --commit",
      "count": 1,
      "kind": "to_commit",
      "text": "1 feature whose results are not committed"
    },
    {
      "command": "purlin:build",
      "count": 4,
      "kind": "to_strengthen",
      "text": "4 rules to strengthen"
    }
  ],
  "met": false,
  "notices": [],
  "os_words": {
    "linux": {
      "short": "Lin",
      "word": "Linux/Unix"
    },
    "macos": {
      "short": "Mac",
      "word": "macOS"
    },
    "windows": {
      "short": "Win",
      "word": "Windows"
    }
  },
  "project": "project",
  "schema_version": 20,
  "signoff": {
    "commit": null,
    "since": null,
    "version": null,
    "word": "not signed"
  },
  "summary": {
    "audit": {
      "not_audited": 0,
      "out_of_date": 0,
      "spot_checked": 0,
      "strong": 4,
      "weak": 4
    },
    "audit_out_of_date": 0,
    "by_hand": 0,
    "failing": 0,
    "features": 1,
    "incomplete": 0,
    "manual": 0,
    "not_audited": 0,
    "partial": 0,
    "passed": 8,
    "proofs": 12,
    "proofs_without_test": 0,
    "proofs_without_test_ids": [],
    "rules": 8,
    "sentence": "8 rules. 8 pass their tests. The audit found 4 of 8 rules strong (50%): 4 strong, 4 weak.",
    "spot_checked": 0,
    "steps": {
      "by_hand": 0,
      "graded": 0,
      "passed": 8
    },
    "strong": 4,
    "untested": 0,
    "weak": 4
  },
  "version": "0.10.0",
  "warnings": []
};
