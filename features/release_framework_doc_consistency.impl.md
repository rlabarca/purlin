# Implementation Notes: Framework Documentation Consistency

This step is positioned immediately after `purlin.instruction_audit` in Purlin's release config, so override consistency (`purlin.instruction_audit`) and instruction-internal consistency (this step) run together before the broader doc check.

This step's scope intentionally excludes `.purlin/` override files — those are covered by `purlin.instruction_audit`. This step focuses on the base instruction layer.
