# The trial behind model routing

This page gives the evidence for [model routing](../references/formats/routing_format.md):
what it costs and whether the software it builds is as good. It is one trial, measured on
26 Oct 2026.

## The trial

One feature, a three-part order fulfilment system (inventory, orders, invoicing), built
from start to finish twice with Purlin at `f17af3e1a`, each part specified,
built and tested in turn, then one audit over all three. The same requirement and the same answers
in both.

The three requirements, one `spec` each:

- **inventory:** products with stock on hand and a low-stock threshold; restock, reserve and release;
  a reservation below zero available is refused with a reason; low-stock listing.
- **orders:** orders of one or more lines that reserve stock for every line or none, naming the line
  that failed; placed → paid → shipped → delivered only; placed or paid orders can be cancelled,
  releasing their stock.
- **invoicing:** invoices for paid orders from a price list; tax by region (UK 20%, DE 19%,
  export 0%); one discount code per order, a percentage or a fixed amount, with an expiry date;
  totals rounded half up to the cent; a daily CSV export.

| | Off | On |
|---|---|---|
| Session | Opus 5.5 throughout | Sonnet 5.5, set by `purlin:route on` |
| Commands | `/purlin:spec`, `/purlin:build`, ... | `/spec`, `/build`, ... |
| spec | Opus, in the session | one Opus runner subagent per part; the session shows its draft and passes the answer back |
| build, test, audit | Opus | Sonnet, the session's own model |
| The audit's planted bugs | Opus | Opus |

Costs are API list-price equivalents from the session transcripts, at Claude Code's own rates and
the interactive cache price; on a subscription they show how fast usage limits are drawn.

## Result

| | Off | On | Difference |
|---|---|---|---|
| Setup: init, route on | $0.17 | $0.21 | +$0.04 |
| spec ×3 | $1.22 | $1.68 | +$0.46 |
| build ×3 | $1.23 | $0.62 | −$0.61 |
| test ×3 | $0.31 | $0.09 | −$0.22 |
| audit | $0.24 | $0.07 | −$0.17 |
| **Total** | **$3.17** | **$2.67** | **−16%** |
| Rules, proofs | 38, 69 | 35, 55 | |
| Rules passing their tests | 38 of 38 | 35 of 35 | |
| Rules strong after the audit | 35 of 38 (92%) | 30 of 35 (86%) | |

Routing costs more for spec, which runs once per part, and less for build, test and audit, which
make up most of the work. Every rule passes in both.

## Step by step

| Part | Step | Off: Opus | On | On: what ran |
|---|---|---|---|---|
| setup | `init`, then yes to the commit | $0.17 | $0.14 | Sonnet |
| | `route on`, then the answers | | $0.07 | Sonnet |
| inventory | spec: draft | $0.25 | $0.38 | Opus runner $0.29 (start-up 13,000 tokens), session showing the draft $0.09 |
| | spec: your answer, save, commit | $0.17 | $0.22 | Opus runner $0.17, session $0.05 |
| | build, then yes to the test command | $0.47 | $0.24 | Sonnet |
| | test | $0.09 | $0.02 | Sonnet |
| orders | spec: draft | $0.19 | $0.34 | Opus runner $0.27, session $0.07 |
| | spec: your answer, save, commit | $0.18 | $0.17 | Opus runner $0.13, session $0.04 |
| | build | $0.34 | $0.16 | Sonnet |
| | test | $0.10 | $0.03 | Sonnet |
| invoicing | spec: draft | $0.24 | $0.45 | Opus runner $0.35, session $0.10 |
| | spec: your answer, save, commit | $0.20 | $0.12 | Opus runner $0.06, session $0.06 |
| | build | $0.42 | $0.22 | Sonnet |
| | test | $0.12 | $0.04 | Sonnet |
| all | audit | $0.24 | $0.07 | Sonnet; planted bugs on Opus |
| | **Total** | **$3.17** | **$2.67** | |

## Quality

Four checks, run on the builds above and the booking builds, with no new build:

| Check | Order system: off, on | Booking: off, on |
|---|---|---|
| Requirement checks, the same for both | 28 of 28, 28 of 28 | 28 of 28, 28 of 28 |
| Requirement clauses with a rule in the spec | 24 of 24, 24 of 24 | 10 of 10, 10 of 10 |
| Differential test: operations, differences | 39,428 operations, 1 kind | 40,000 operations, 0 |
| Rules strong after the audit | 35 of 38 (92%), 30 of 35 (86%) | 11 of 13 (85%), 8 of 9 (89%) |

- **Requirement checks.** Written from the requirement sentences, not from either build's spec,
  and run against both builds through the same adapters.
- **Spec coverage.** Each clause of each requirement, such as "a second code is refused with a
  reason", traced to the rule that holds it. Every clause has one in all four specs; "Python 3 with
  no third-party packages" is in each spec's `Stack` line. Each spec adds a few rules of its own,
  such as a SKU added twice.
- **Differential test.** 2,000 random sequences of operations, the same into both builds, compared
  after each operation: accepted or refused, then stock, order states, invoice totals and room
  listings. Messages are not compared.
- **Audit.** The weak rules are tests that miss one assertion, such as a refused call leaving a
  value unchecked, not faults in the code: on the order system off had 3, on 5; on booking off had
  2, on 1. The strength follows the tests each build wrote, not the model.

The one difference: a discount code applied to an order already invoiced. Off refuses it, from a
rule its spec added (invoicing RULE-15); on accepts it, and the invoice is unchanged. The
requirement says nothing about it, and both answers leave every total the same. With that case set
aside, 39,692 operations gave no difference.

Both specs were written on Opus. On this feature, routing saved 16% with no loss in what the
software does.

## Where the difference comes from

- **spec costs more routed (+$0.46).** Each part starts a fresh Opus runner, about 7,000 to 13,000
  tokens before it does any work, and the Sonnet session reads the draft and shows it. The spec
  work itself is Opus in both.
- **build costs half (−$0.61).** The same code and tests are written on Sonnet at half Opus's price,
  in the same session, with no switch of model.
- **test and audit cost a quarter or less (−$0.39).** Both mostly start a Purlin script and read the
  result, which Sonnet does as well as Opus.

## How it was measured

- Claude Code saves each session's transcript with the model and tokens of every call; these
  were totalled step by step, a subagent's calls included.
- Rates per million tokens, as Claude Code applies them: Opus 5.5 $4 input, $20 output, $0.20 cache
  read; Sonnet 5.5 $2, $10, $0.10. A cache write is 1.25 times input.
- Checked against Claude Code's own session totals: the same to the cent.

## On a smaller feature

The meeting room booking module, one part with one spec, one build and one test, came to $1.05
routed against $1.09 off, spec to audit: about even. With a single build there is little for the
cheaper models to save against the Opus runner's start-up for spec. The larger the feature, the
more builds and test runs there are, and the more routing saves.

## What this does not show

- **One run each.** A model writes a different spec each time (38 rules off, 35 on), so part of the
  saving may come from that.
- **Behaviour only.** The checks test what the software does, not how readable its code is.
