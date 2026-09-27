# Writing style

How Purlin writes: every doc, skill, reference, agent definition, CLI message, dashboard label
and commit message. This page is the one home of the wording rules.

## The rules

**Voice.** Plain and declarative. Purlin explains a process, so every sentence does one job.
"One line saying what the software has to do", not "Define your requirements at the atomic
level."

**Person.** Second person for the reader's actions ("you commit it yourself", "before you
push"), third person for the system's ("Purlin breaks your code on purpose", "the audit writes
its findings for each rule it reached"). First person never appears. The product does not say
"we".

**Casing.** Sentence case for titles, buttons and body. Uppercase is reserved for state badges
("PASSED", "STRONG", "SIGNED"). Command names are always lowercase with the colon:
`purlin:audit`, never `Purlin Audit`.

**Limits stated.** Say what Purlin cannot do as plainly as what it can: "Purlin can't prove code
is right. It gives you a paper trail." State the gap rather than skip it.

**Exact numbers.** "42 specs", "71% test strength", "Twelve rules changed. Two signatures went
stale." Figures are exact and unrounded, and they usually close a section rather than open it.

**Machine text in monospace.** Anything the machine produced, commands, rule ids, file paths,
shas, gates, cell words and transcripts, is set in monospace: backticks in Markdown, Courier New
on a page. Anything a person wrote is in the running typeface. Readers use the typeface to tell
whose claim they are reading.

**No emoji.** Not in the docs, not in the dashboard, not in the CLI output, not in a test or a
fixture.

**No superlatives.** No "seamless", "powerful" or "revolutionise", no exclamation marks, no
rhetorical questions, and no sentence that describes a benefit without naming the mechanism.

## Sentence shapes

- Definitions: "*Gate*: the one project setting, `passed`, `strong` or `signed`."
- Consequences: "If any of the three change, it no longer counts."
- Instructions: "Run it at the start of a session and before a release."
