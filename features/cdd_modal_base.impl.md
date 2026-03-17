# Implementation Notes: CDD Modal Base

**[DISCOVERY]** (RESOLVED) Modal body base font size was 13px but `design_modal_standards.md` specifies 14px (inherited from `design_visual_standards.md` Section 2.3, Inter 14px). Title was 21px fixed but spec says 4pts above body = 18px with scaling. Fixed: body now 14px, title 18px (using calc with --modal-font-adjust), headings h1=17px/h2=15px/h3=13px/code=12px. All non-body elements (title, metadata, tabs) now also scale with the font-adjust slider. Step Detail inline-styled content updated to use calc() for scaling.
