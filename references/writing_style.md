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
the command to run next; a project whose tests are met ends on `purlin:sign`.

**Systems by their names.** Wherever a person reads an operating system it is `Windows`,
`macOS` or `Linux/Unix`, and in the dashboard's small boxes `Win`, `Mac` or `Lin`. The stored
words, `windows`, `macos` and `linux`, are machine text: a spec's `@env(...)` and the evidence
use them, and a person reads them only there.

**No emoji.** Not in the docs, not in the dashboard, not in the CLI output, not in a test or a
fixture.

**No superlatives.** No "seamless", "powerful" or "revolutionise", no exclamation marks, no
rhetorical questions, and no sentence that describes a benefit without naming the mechanism.

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
