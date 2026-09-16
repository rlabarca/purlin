Every verify run writes one record per feature here, and commits it.

CI writes the records that count under this project's `strong` gate; a
person's push to this folder is refused by the git host's file-path rule.
