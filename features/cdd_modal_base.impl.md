# Implementation Notes: CDD Modal Base

**[DISCOVERY]** Modal body base font size is 13px in `serve.py` (line ~2122), but `design_modal_standards.md` specifies 14px (inherited from `design_visual_standards.md` Section 2.3, Inter 14px). Title is 21px but should be 22px (14+8). All body heading offsets (+3/+1/-1/-2 from base) also need +1px adjustment. Tests in `test_cdd_modal_base.py` assert the current 13px/21px values and will need updating. (Severity: HIGH)
