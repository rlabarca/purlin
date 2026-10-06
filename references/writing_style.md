# Writing style

How Purlin writes: every doc, skill, reference, agent definition, CLI message, dashboard label
and commit message. This page is the one home of the wording rules.

## The rules

**Voice.** Plain and declarative. Purlin explains a process, so every sentence does one job.
"One line saying what the software has to do", not "Define your requirements at the atomic
level."

**Person.** Second person for the reader's actions ("you commit it yourself", "before you
push"), third person for the system's ("Purlin plants one bug per proof", "the audit writes
its findings for each rule it reached"). First person never appears. The product does not say
"we".

**Casing.** Sentence case for titles, buttons and body. Uppercase is reserved for state badges
("PASSED", "STRONG", "SIGNED"). On the dashboard the design also sets small labels in capitals,
such as `563 RULES TOTAL`. Command names are always lowercase with the colon:
`purlin:audit`, never `Purlin Audit`.

**What is, not what was.** A page says what the software does now. It does not say what an
earlier release did, what a thing replaced or what was taken out, and it does not describe a
missing thing by denying it: say what is there. The history of a release lives in
`RELEASE_NOTES.md` and nowhere else.

**One word per concept.** The word for each concept is the one `references/glossary.md` gives,
and the three roles are product, developer and QA.

**Limits stated.** Say what Purlin cannot do as plainly as what it can: "Purlin can't prove code
is right. It gives you a paper trail." State the gap rather than skip it.

**Exact numbers.** "42 specs", "4 of 5 rules strong (80%)", "40 rules. 35 pass their tests." Figures
are exact and unrounded, and they usually close a section rather than open it.

**Machine text in monospace.** Anything the machine produced, commands, rule ids, file paths,
shas, cell words and transcripts, is set in monospace: backticks in Markdown, Courier New
on a page. Anything a person wrote is in the running typeface. Readers use the typeface to tell
whose claim they are reading.

**Every output says what to do next.** An agent seeking a goal can read any output, know which
rule is affected and what to do, and improve the project by doing it. A command's ending names
the command to run next. A project whose tests are met ends on a line that names `purlin:sign`
as optional.

**Systems by their names.** Wherever a person reads an operating system it is `Windows`,
`macOS` or `Linux/Unix`, and in the dashboard's small boxes `Win`, `Mac` or `Lin`. The stored
words, `windows`, `macos` and `linux`, are machine text: a spec's `@env(...)` and the evidence
use them, and a person reads them only there.

**No emoji.** Not in the docs, not in the dashboard, not in the CLI output, not in a test or a
fixture.

**No superlatives.** No "seamless", "powerful" or "revolutionise", no exclamation marks, no
rhetorical questions, and no sentence that describes a benefit without naming the mechanism.

## A warning's shape

Every warning and every line of information takes one shape, in the terminal and on the
dashboard, so a reader learns it once:

```
<what it is about>: <kind>. <what is wrong>. Run <command>.
```

```
package PROOF-3 (RULE-3): test comment to correct. "sixteen" became "seventeen" after dev/test_export.py:336 last changed (82c91f6). Run purlin:build package.
```

- **What it is about** comes first, as you would look it up: `<spec> PROOF-N (RULE-N)` for a
  proof, `<spec> RULE-N` for a rule, `<spec>` for a spec or an anchor, and the thing itself, a
  tag or a file, where the line is about no one spec.
- **The kind** is 2 to 5 words, the same every time. Where the status names that work under
  `Left to do`, the kind is that name: `test comment to correct`, `spec to repair`.
- **What is wrong** is short. A reworded proof shows the words that changed alone, each side
  cut to 8 words with ` ...`, or `was reworded` where the two wordings share too little. A rule
  or a proof is never printed whole.
- **What to run** is last. Where nothing is to be run, the last sentence says what to do.
- It is one line, and a path or a name is never cut.

On the dashboard the name is in the machine typeface and the kind is a label. Three or more of
one kind fold into one notice that opens on the kind:
`proof line not read: 4 specs, export, invoice and 2 more. Run purlin:status for each.`

## Short and plain

Purlin's slides are the model. A doc page may say more than a slide, and it says it the same way.

- One idea in a sentence. Two ideas are two sentences.
- The concrete example before the abstract statement, or in place of it.
- Where a slide covers the same thing, the page uses the slide's words for it.
- A page says what the reader needs for the next thing they do. Detail few readers need goes
  last, or on the page a link names.
- Nothing true that a reader needs is cut, and every statement is what the code does.

- Before: "It names what is done, what is seen and the value that settles it, such as the
  message `Account locked`."
- After: "A test checks an exact result, like the message `Account locked`."

## Sentence shapes

- Definitions: "*Evidence*: what a run leaves behind for each feature, one file per source."
- Consequences: "If the test fails, the rule is left to do as `to fix`."
- Instructions: "Run it at the start of a session and before a sign-off."
