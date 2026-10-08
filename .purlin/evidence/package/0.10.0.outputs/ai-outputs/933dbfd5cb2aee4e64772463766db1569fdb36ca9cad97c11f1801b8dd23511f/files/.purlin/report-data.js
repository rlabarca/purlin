const PURLIN_DATA = {
  "branch": "main",
  "commit": "deed9e23cde6b03e5c1e9a1d8551714cac611464",
  "dirty": false,
  "evidence": {
    "sample_intake": {
      "local": {
        "macos": {
          "at": "2026-10-07T22:00:36Z",
          "commit": "0b6425b53343c3f634c6c7374ba48e0c813e8bc3",
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
          "committed": true,
          "path": ".purlin/evidence/local/sample_intake.json",
          "platforms": {
            "macos": {
              "at": "2026-10-07T22:00:36Z",
              "commit": "0b6425b53343c3f634c6c7374ba48e0c813e8bc3",
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
        "spot_checked": 4,
        "strong": 1,
        "untested": 0,
        "weak": 3
      },
      "rules": [
        {
          "audit": {
            "at": "2026-10-07T22:00:38Z",
            "bugs": {
              "PROOF-1": {
                "after": null,
                "aim": "plain",
                "before": null,
                "bug_key": "2b2ae76e97c37b9c0634cb0dc7deaa35ea78831d5db8ef32ed66e940e2c32dbd",
                "case": "",
                "file": null,
                "line": null,
                "result": "not made",
                "why": "it holds none"
              },
              "PROOF-2": {
                "after": null,
                "aim": "plain",
                "before": null,
                "bug_key": "82a466ea8a73d753c94b4c51ea95c85ef5ee7e3fb74ffac8e5cb1aef5b739633",
                "case": "",
                "file": null,
                "line": null,
                "result": "not made",
                "why": "it holds none"
              }
            },
            "commit": "0b6425b53343c3f634c6c7374ba48e0c813e8bc3",
            "explanation": [
              "PROOF-5: the test takes its expected age from the code."
            ],
            "findings": [],
            "model": "claude-fake-1",
            "no_bug": [
              "No bug was planted: the model's answer for PROOF-1 could not be used: it holds none.",
              "No bug was planted: the model's answer for PROOF-2 could not be used: it holds none."
            ],
            "notes": [],
            "out_of_date": [],
            "path": ".purlin/evidence/local/sample_intake.json",
            "verdict": "spot-checked"
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
                  "at": "2026-10-07T22:00:36Z",
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
              "reasons": [
                "The spot tests found nothing. No bug was planted: the model's answer for PROOF-1 could not be used: it holds none. No bug was planted: the model's answer for PROOF-2 could not be used: it holds none."
              ],
              "word": "spot-checked"
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
            "spot_checked": true,
            "strong": false,
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
            "at": "2026-10-07T22:00:38Z",
            "bugs": {
              "PROOF-3": {
                "after": "        return record",
                "aim": "past the test",
                "before": "        self.received[barcode] = record\n        return record",
                "bug_key": "52b4f3abef5ca195b65c9921c08b70c130961db6cd3c4a2c9c302752a86a85e8",
                "case": "a sample with the barcode `LC-12345678` is handed in; the proof names it stored with the status `accepted`; the changed code returns a record with status `accepted` but never stores it, so the bench's `received` stays empty",
                "file": "src/intake.py",
                "line": 52,
                "result": "survived",
                "test_key": "5e02b4541f7a210ccd5d6a945686a03eeefad30668d5be574e907645730fd944",
                "why": ""
              },
              "PROOF-4": {
                "after": null,
                "aim": "plain",
                "before": null,
                "bug_key": "5bf11b150c2a3db38633c3e2514979a6d267ea149d4960aa604c7fa3f0bd0dc9",
                "case": "",
                "file": null,
                "line": null,
                "result": "not made",
                "why": "it holds none"
              }
            },
            "commit": "0b6425b53343c3f634c6c7374ba48e0c813e8bc3",
            "explanation": [
              "PROOF-5: the test takes its expected age from the code."
            ],
            "findings": [
              "PROOF-3: the test still passes when src/intake.py:52 reads \"return record\"",
              "PROOF-3: the AI says this breaks: a sample with the barcode `LC-12345678` is handed in; the proof names it stored with the status `accepted`; the changed code returns a record with status `accepted` but never stores it, so the bench's `received` stays empty"
            ],
            "model": "claude-fake-1",
            "no_bug": [
              "No bug was planted: the model's answer for PROOF-4 could not be used: it holds none."
            ],
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
                  "at": "2026-10-07T22:00:36Z",
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
                "PROOF-3: the test still passes when src/intake.py:52 reads \"return record\"",
                "PROOF-3: the AI says this breaks: a sample with the barcode `LC-12345678` is handed in; the proof names it stored with the status `accepted`; the changed code returns a record with status `accepted` but never stores it, so the bench's `received` stays empty"
              ],
              "reasons": [
                "PROOF-3: the test still passes when src/intake.py:52 reads \"return record\"",
                "PROOF-3: the AI says this breaks: a sample with the barcode `LC-12345678` is handed in; the proof names it stored with the status `accepted`; the changed code returns a record with status `accepted` but never stores it, so the bench's `received` stays empty"
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
            "at": "2026-10-07T22:00:38Z",
            "bugs": {
              "PROOF-5": {
                "after": "    return int(round(seconds / 3600))",
                "aim": "past the test",
                "before": "    return int(seconds // 3600)",
                "bug_key": "1dc970279f6b61523c8ff4e416d1b2c80c8923c55706949f184aacf8aafac544",
                "case": "a sample received 25 and a half hours after it was collected; the proof names no age; the changed code gives 26 hours where the code gave 25",
                "file": "src/intake.py",
                "line": 17,
                "result": "survived",
                "test_key": "fd5623f6a7e09317a54476ccb09b284a6623b4bed03c85c055ffe6a54925240d",
                "why": ""
              }
            },
            "commit": "0b6425b53343c3f634c6c7374ba48e0c813e8bc3",
            "explanation": [
              "PROOF-5: the test takes its expected age from the code."
            ],
            "findings": [
              "PROOF-5: the test still passes when src/intake.py:17 reads \"return int(round(seconds / 3600))\"",
              "PROOF-5: the AI says this breaks: a sample received 25 and a half hours after it was collected; the proof names no age; the changed code gives 26 hours where the code gave 25"
            ],
            "model": "claude-fake-1",
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
                  "at": "2026-10-07T22:00:36Z",
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
                "PROOF-5: the test still passes when src/intake.py:17 reads \"return int(round(seconds / 3600))\"",
                "PROOF-5: the AI says this breaks: a sample received 25 and a half hours after it was collected; the proof names no age; the changed code gives 26 hours where the code gave 25"
              ],
              "reasons": [
                "PROOF-5: the test still passes when src/intake.py:17 reads \"return int(round(seconds / 3600))\"",
                "PROOF-5: the AI says this breaks: a sample received 25 and a half hours after it was collected; the proof names no age; the changed code gives 26 hours where the code gave 25"
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
          "proof_hash": "82bb269a77511b7203f966545b396be30152f744b26caf0dd6e8ff63ae9c07d5",
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
              "text": "A sample received the day after it was collected has its age in whole hours"
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
            "at": "2026-10-07T22:00:38Z",
            "bugs": {
              "PROOF-6": {
                "after": "MAX_AGE_HOURS = 73",
                "aim": "plain",
                "before": "MAX_AGE_HOURS = 72",
                "bug_key": "37989b10ab8f0f969ad5855469553a1f2d466b593d9a9fbb39ec1ae50b088080",
                "case": "a sample collected at 2026-03-01T08:00 and received at 2026-03-04T09:00, 73 hours later; the proof names it stored as `expired`; the changed code stores it as `accepted`",
                "file": "src/intake.py",
                "line": 6,
                "result": "caught",
                "why": ""
              },
              "PROOF-7": {
                "after": null,
                "aim": "plain",
                "before": null,
                "bug_key": "38e32c5d42187b0575d793209c19731319f4b025053c28ffe4ec1d7f689b9b53",
                "case": "",
                "file": null,
                "line": null,
                "result": "not made",
                "why": "it holds none"
              }
            },
            "commit": "0b6425b53343c3f634c6c7374ba48e0c813e8bc3",
            "explanation": [
              "PROOF-5: the test takes its expected age from the code."
            ],
            "findings": [],
            "model": "claude-fake-1",
            "no_bug": [
              "No bug was planted: the model's answer for PROOF-7 could not be used: it holds none."
            ],
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
                  "at": "2026-10-07T22:00:36Z",
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
          "id": "RULE-4",
          "left": null,
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
            "at": "2026-10-07T22:00:38Z",
            "bugs": {
              "PROOF-8": {
                "after": null,
                "aim": "plain",
                "before": null,
                "bug_key": "169273e3468407bb8144f335701dbbc46a76d2c270f9d3fecb09d9507160bbf5",
                "case": "",
                "file": null,
                "line": null,
                "result": "not made",
                "why": "it holds none"
              },
              "PROOF-9": {
                "after": null,
                "aim": "plain",
                "before": null,
                "bug_key": "4504af421d948eb22a09e8e089808cf2b498b4eeb492c9866dbdb51cd5cac768",
                "case": "",
                "file": null,
                "line": null,
                "result": "not made",
                "why": "it holds none"
              }
            },
            "commit": "0b6425b53343c3f634c6c7374ba48e0c813e8bc3",
            "explanation": [
              "PROOF-5: the test takes its expected age from the code."
            ],
            "findings": [],
            "model": "claude-fake-1",
            "no_bug": [
              "No bug was planted: the model's answer for PROOF-8 could not be used: it holds none.",
              "No bug was planted: the model's answer for PROOF-9 could not be used: it holds none."
            ],
            "notes": [],
            "out_of_date": [],
            "path": ".purlin/evidence/local/sample_intake.json",
            "verdict": "spot-checked"
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
                  "at": "2026-10-07T22:00:36Z",
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
              "reasons": [
                "The spot tests found nothing. No bug was planted: the model's answer for PROOF-8 could not be used: it holds none. No bug was planted: the model's answer for PROOF-9 could not be used: it holds none."
              ],
              "word": "spot-checked"
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
            "spot_checked": true,
            "strong": false,
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
            "at": "2026-10-07T22:00:38Z",
            "bugs": {
              "PROOF-10": {
                "after": null,
                "aim": "plain",
                "before": null,
                "bug_key": "51a6e4ea92b5d7e04e9612b25c1b6b6ad7f0bbb3120ece831162af3af3a2dd5c",
                "case": "",
                "file": null,
                "line": null,
                "result": "not made",
                "why": "it holds none"
              }
            },
            "commit": "0b6425b53343c3f634c6c7374ba48e0c813e8bc3",
            "explanation": [
              "PROOF-5: the test takes its expected age from the code."
            ],
            "findings": [],
            "model": "claude-fake-1",
            "no_bug": [
              "No bug was planted: the model's answer for PROOF-10 could not be used: it holds none."
            ],
            "notes": [],
            "out_of_date": [],
            "path": ".purlin/evidence/local/sample_intake.json",
            "verdict": "spot-checked"
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
                  "at": "2026-10-07T22:00:36Z",
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
              "reasons": [
                "The spot tests found nothing. No bug was planted: the model's answer for PROOF-10 could not be used: it holds none."
              ],
              "word": "spot-checked"
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
            "spot_checked": true,
            "strong": false,
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
            "at": "2026-10-07T22:00:38Z",
            "bugs": {
              "PROOF-11": {
                "after": null,
                "aim": "plain",
                "before": null,
                "bug_key": "c4988b10c2f1092d14880c9f5dc19b9db8e332a6ef0634a9885ee0c4fa2a61b2",
                "case": "",
                "file": null,
                "line": null,
                "result": "not made",
                "why": "it holds none"
              }
            },
            "commit": "0b6425b53343c3f634c6c7374ba48e0c813e8bc3",
            "explanation": [
              "PROOF-5: the test takes its expected age from the code."
            ],
            "findings": [
              "tests/test_intake.py::test_accession_numbers_count_up: the test checks nothing."
            ],
            "model": "claude-fake-1",
            "no_bug": [
              "No bug was planted: the model's answer for PROOF-11 could not be used: it holds none."
            ],
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
                  "at": "2026-10-07T22:00:36Z",
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
                "tests/test_intake.py::test_accession_numbers_count_up: the test checks nothing."
              ],
              "reasons": [
                "tests/test_intake.py::test_accession_numbers_count_up: the test checks nothing."
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
            "at": "2026-10-07T22:00:38Z",
            "bugs": {
              "PROOF-12": {
                "after": null,
                "aim": "plain",
                "before": null,
                "bug_key": "0540a1e79104dc57d965cdbdc7fc3724ab39f9796fb27087c41c668797d87acb",
                "case": "",
                "file": null,
                "line": null,
                "result": "not made",
                "why": "it holds none"
              }
            },
            "commit": "0b6425b53343c3f634c6c7374ba48e0c813e8bc3",
            "explanation": [
              "PROOF-5: the test takes its expected age from the code."
            ],
            "findings": [],
            "model": "claude-fake-1",
            "no_bug": [
              "No bug was planted: the model's answer for PROOF-12 could not be used: it holds none."
            ],
            "notes": [],
            "out_of_date": [],
            "path": ".purlin/evidence/local/sample_intake.json",
            "verdict": "spot-checked"
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
                  "at": "2026-10-07T22:00:36Z",
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
              "reasons": [
                "The spot tests found nothing. No bug was planted: the model's answer for PROOF-12 could not be used: it holds none."
              ],
              "word": "spot-checked"
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
            "spot_checked": true,
            "strong": false,
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
  "generated_at": "2026-10-07T22:00:53Z",
  "generated_by": "sync_status",
  "information": [],
  "last_line": "Every rule passes its tests on the committed evidence. Optional: sign this version with purlin:sign",
  "left": [
    {
      "command": "purlin:build",
      "count": 3,
      "kind": "to_strengthen",
      "text": "3 rules to strengthen"
    }
  ],
  "met": true,
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
      "spot_checked": 4,
      "strong": 1,
      "weak": 3
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
    "sentence": "8 rules. 8 pass their tests. The audit found 1 of 8 rules strong (12%): 1 strong, 3 weak, 4 spot-checked.",
    "spot_checked": 4,
    "steps": {
      "by_hand": 0,
      "graded": 0,
      "passed": 8
    },
    "strong": 1,
    "untested": 0,
    "weak": 3
  },
  "version": "0.10.0",
  "warnings": []
};
