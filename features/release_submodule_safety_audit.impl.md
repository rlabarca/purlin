# Implementation Notes: Purlin Submodule Safety Audit

This feature has no automated test coverage. Verification is performed by PM mode
during the release process per the scenarios above. The QA column will always be `N/A`.

The seven check categories map directly to `features/submodule_bootstrap.md` Sections 2.10–2.14
(Categories 1–6) and the Submodule Compatibility Mandate in `HOW_WE_WORK_OVERRIDES.md`
(Category 7). When new submodule safety requirements are added to `submodule_bootstrap.md`,
this feature spec MUST be updated to add a corresponding check category.

Remediation ownership: PM mode audits and halts; Engineer mode fixes code. PM mode
does not modify tool scripts — all code corrections go to Engineer mode via the spec. The audit
findings themselves serve as Engineer mode's action items once this feature is in TESTING state.
