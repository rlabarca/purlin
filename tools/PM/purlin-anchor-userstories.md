---
name: purlin-anchor-userstories
description: >
  Write and edit Purlin specs and anchors in a git repository from Claude Desktop, with no
  checkout, through a GitHub or Azure DevOps connector. Use this whenever the user wants to
  turn a sentence, a PRD, a ticket, pasted acceptance criteria or uploaded design images into
  rules and proofs under a project's specs/ folder, or wants to change rules that are already
  there. Mentions of "Purlin", "spec", "anchor", "user stories", "acceptance criteria",
  "rules and proofs" or "spec-driven development" all reach this skill.
---

# Purlin specs for a product manager

A Purlin spec is one Markdown file holding **rules**, one line each saying what the software
has to do, and **proofs**, one line each saying how a rule is observed. This skill writes and
edits those files through the repository connector and opens a pull request. The product
manager never clones the repository and never runs git.

Every change lands as a pull request. Never commit to the default branch.

## What to collect first

1. **The repository URL.** The project itself, or a separate anchor repository holding specs
   shared by several projects. Both work the same way here.
2. **The path.** `specs/<category>/<name>.md` for a feature, or `specs/_anchors/<name>.md`
   for an anchor, which is a spec for something shared across features. List `specs/` through
   the connector and ask whether this is an edit or a new file.
3. **The material.** A sentence, a PRD, a ticket, pasted acceptance criteria, or uploaded
   design images.

If the repository has no `specs/` folder, say so and ask before creating the first file there.
Create no other folder.

## Step 1: read what is already in the repository

Read through the connector. Do not clone.

- The target spec, when it exists.
- `.purlin/config.json`, for the `gate` value and for whether a signer list is set.
- The other specs in the same folder, so a new rule does not repeat one that exists.

Rule ids continue the sequence in the file and are never reused, not even a vacant number. A
retired rule leaves its number empty and the rules that remain keep the numbers they had,
because renumbering would repoint every test and every signature that names the old id.

## Step 2: write the rules and proofs

A spec is two sections and a few metadata lines:

```markdown
# Feature: checkout

> Description: What this feature does and why it exists, in plain sentences.
> Scope: src/checkout/, src/cart.py
> Requires: design_tokens

## Rules

- RULE-1: Reject an order whose cart is empty [risk: high] [origin: pm] [criterion: US-12]
- RULE-2: Show the tax line before the total [risk: low] [origin: design]

## Proof

- PROOF-1 (RULE-1): POST an order with no line items; verify HTTP 400 @integration
- PROOF-2 (RULE-2): Load the cart page with one item; verify the tax line reads "Tax" above
  the total @e2e
```

Tag every rule you write with `[origin: pm]`, and carry the upstream id across as
`[criterion: <id>]` whenever the material has one: a ticket number, a story id, a row in a
requirements sheet. Set `[risk: high]`, `[risk: medium]` or `[risk: low]` on each rule by what
a wrong answer costs; the default when the tag is absent is `low`. Under the `signed` gate risk
and origin are both required, so write them every time. Risk is read at the `strong` gate and
above: it decides at which risk a model review runs and at which risk a person has to sign.

Tag a proof with its tier: no tag for pure logic, `@integration` when it needs a database, the
network or the filesystem, `@e2e` when it needs a browser or the full stack, `@manual` when a
person's judgment is the only instrument and no test can settle it. At most one
`@env(windows)`, `@env(macos)` or `@env(linux)` per proof, and only when the operating system
is part of the claim.

**The quality bar.** Before you propose a rule, check it against the four failures that keep a
rule out of the pipeline:

- **No expected value.** The proof names no number, string or constant, so almost any test
  satisfies it. Name the status code, the text, the count.
- **A vague verb.** "Works", "correctly", "properly", "as expected". Replace the verb with the
  observation.
- **No trigger.** Nothing runs before the assertion. Name the request, the render or the click
  that produces what you then assert on.
- **A tier that does not match.** An `@e2e` proof described as a function call is neither.

Write a proof that names a rejection, an error or a boundary for every rule that says reject,
block, limit or expire. A high-risk rule proved in one direction only is sent back.

## The owner comment rule

A rule tagged `[origin: eng]` or `[origin: qa]` belongs to the engineer or to QA. Never edit
its text, its risk or its proofs, and never delete it, even when the product manager asks and
even when it looks wrong. Leave the rule exactly as it is, and put the proposed change in a
pull request comment instead:

> RULE-4 is `origin: eng`. Proposed: "Lock the account for fifteen minutes after five failed
> attempts" rather than ten. Reason: the policy changed on 12 September. Edit it here if you
> agree.

Say in the chat which rules you left alone and why. A rule with `[origin: pm]`, or with no
origin tag at all on a spec the product manager owns, you edit directly.

## Design images

When the product manager uploads mocks, screenshots, a PDF or an HTML prototype, commit the
files to `designs/<feature>/` in the same pull request and write `[origin: design]` rules about
what a person would see: the text, the order of the elements, the states present. Never write a
rule or a proof that names a CSS selector, a class or a pixel value; a refactor breaks it
without changing behaviour, and the free checks report it as `implementation_coupling`.

A design is a versioned file read and merged by pull request, never a live connection to a
design tool. There is no importer: the files the product manager uploads are the design.

## Step 3: show the draft, then open the pull request

Print the whole file in the chat and wait. Iterate until the product manager says it is ready.
Then, through the connector:

1. Create a branch, `spec/<name>`.
2. Commit the spec with the message `spec(<name>): <what changed>`, and the design files, when
   there are any, with `chore: add designs for <name>`.
3. Open the pull request against the default branch, with the rule ids in the title and the
   list of what changed in the body.
4. Post the owner comments from the previous section on the lines they concern.
5. Give the product manager the pull request URL and say who has to review it.

## Step 4: say what happens next

Close with what the product manager will see, in this order:

- The pull request renders the diff. Reading it and merging it is the whole review.
- CI runs `purlin:audit` on the branch and again after the merge. It writes a record, posts the
  same rollup as a pull request comment, and publishes the dashboard as a build artifact linked
  from that comment. Open the artifact to see every rule's cells.
- `purlin:drift pm`, which the engineer runs in the checkout, lists the criteria that have no
  rule yet, the pm-origin rules that changed, and the rules the engineer added.
- A new rule's spec status is `drafted` until a proof names it, and `ready` once one does. From
  there it answers up to three questions, each one a cell: `passed`, then `strong`, then
  `signed`. How far it must go before a change can merge is the project's gate: `passed`,
  `strong` or `signed`.

## Limits, stated plainly

- This skill writes specs. It does not write code, run tests, or sign anything.
- It cannot tell whether a rule is worth having. It can only tell whether a rule can be proved.
- An anchor pinned from another repository carries `> Source:` and `> Pinned:` lines. Never
  edit that copy in the consuming project: change it in the repository it came from, and the
  engineer advances the pin.
