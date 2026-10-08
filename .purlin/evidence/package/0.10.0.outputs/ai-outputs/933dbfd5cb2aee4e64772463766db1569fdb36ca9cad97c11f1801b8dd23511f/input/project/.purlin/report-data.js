const PURLIN_DATA = {
  "branch": "main",
  "commit": "0b6425b53343c3f634c6c7374ba48e0c813e8bc3",
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
          "committed": false,
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
        "not_audited": 8,
        "partial": 0,
        "passed": 8,
        "proofs": 12,
        "proofs_without_test": 0,
        "proofs_without_test_ids": [],
        "rules": 8,
        "spot_checked": 0,
        "strong": 0,
        "untested": 0,
        "weak": 0
      },
      "rules": [
        {
          "audit": null,
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
              "evidence": null,
              "findings": [],
              "reasons": [
                "no audit has read this rule"
              ],
              "word": "not audited"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": true,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
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
          "audit": null,
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
              "evidence": null,
              "findings": [],
              "reasons": [
                "no audit has read this rule"
              ],
              "word": "not audited"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": true,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
            "strong": false,
            "weak": false
          },
          "id": "RULE-2",
          "left": null,
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
          "audit": null,
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
              "evidence": null,
              "findings": [],
              "reasons": [
                "no audit has read this rule"
              ],
              "word": "not audited"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": true,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
            "strong": false,
            "weak": false
          },
          "id": "RULE-3",
          "left": null,
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
          "audit": null,
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
              "evidence": null,
              "findings": [],
              "reasons": [
                "no audit has read this rule"
              ],
              "word": "not audited"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": true,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
            "strong": false,
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
          "audit": null,
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
              "evidence": null,
              "findings": [],
              "reasons": [
                "no audit has read this rule"
              ],
              "word": "not audited"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": true,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
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
          "audit": null,
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
              "evidence": null,
              "findings": [],
              "reasons": [
                "no audit has read this rule"
              ],
              "word": "not audited"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": true,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
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
          "audit": null,
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
              "evidence": null,
              "findings": [],
              "reasons": [
                "no audit has read this rule"
              ],
              "word": "not audited"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": true,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
            "strong": false,
            "weak": false
          },
          "id": "RULE-7",
          "left": null,
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
          "audit": null,
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
              "evidence": null,
              "findings": [],
              "reasons": [
                "no audit has read this rule"
              ],
              "word": "not audited"
            }
          },
          "feature": "sample_intake",
          "flags": {
            "audit_out_of_date": false,
            "by_hand": false,
            "failing": false,
            "manual": false,
            "no_proof": false,
            "not_audited": true,
            "out_of_date": false,
            "partial": false,
            "spot_checked": false,
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
  "generated_at": "2026-10-07T22:00:36Z",
  "generated_by": "sync_status",
  "information": [],
  "last_line": null,
  "left": [
    {
      "command": "purlin:test --commit",
      "count": 1,
      "kind": "to_commit",
      "text": "1 feature whose results are not committed"
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
      "not_audited": 8,
      "out_of_date": 0,
      "spot_checked": 0,
      "strong": 0,
      "weak": 0
    },
    "audit_out_of_date": 0,
    "by_hand": 0,
    "failing": 0,
    "features": 1,
    "incomplete": 0,
    "manual": 0,
    "not_audited": 8,
    "partial": 0,
    "passed": 8,
    "proofs": 12,
    "proofs_without_test": 0,
    "proofs_without_test_ids": [],
    "rules": 8,
    "sentence": "8 rules. 8 pass their tests.",
    "spot_checked": 0,
    "steps": {
      "by_hand": 0,
      "graded": 0,
      "passed": 8
    },
    "strong": 0,
    "untested": 0,
    "weak": 0
  },
  "version": "0.10.0",
  "warnings": []
};
