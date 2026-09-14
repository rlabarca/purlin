# Records

One file per verify run, committed, at
`.purlin/records/<feature>/<timestamp>-<commit7>-<runner>.json`. A record says
what ran, on which commit, what passed and the test strength. The git history of
this folder is the log, so adding a file never conflicts. Verify prunes a
feature's records past the newest three unless a `validated/<name>` tag names
them. You do not edit anything here by hand.
