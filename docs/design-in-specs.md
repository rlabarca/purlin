# Design in specs

For designers, and for the engineers who build from their mocks.

A design in Purlin is a versioned file, checked by pull request. It is never a live
connection to a design tool. That is the whole idea: a screen someone signed off on is a file
at a commit, so the screen a rule was signed against can be fetched again a year later.

## Where designs live

```
designs/<feature>/
```

Any exported format the team reads: PNG, PDF, SVG, or an HTML prototype. Export from whatever
tool produced the screens; Purlin reads the files, not the tool.

A designer has two ways in, and neither needs git knowledge:

- **Open a pull request** against `designs/<feature>/` with the new exports. A designer with a
  checkout, or with the git host's web upload, does this directly.
- **Hand the images to an assistant** that can read the repository and open a pull request for
  them, such as Claude Desktop with the git host connected. The assistant puts the files in
  the right folder and opens the pull request; the designer reads the rendered diff.

Purlin 0.10.0 ships no importer for any design tool. Exporting is a manual step, once per
change, and it is the step that makes the design a versioned artifact.

## The design anchor

A design anchor pins the exports and carries the rules they imply. It is an ordinary anchor
whose `> Source:` names local file globs instead of a repository:

```markdown
# Anchor: checkout_design

> Description: The checkout screens, as exported on 2026-08-14.
> Source: designs/checkout/*.png, designs/checkout/*.pdf
> Pinned: 9f2c1ab4e7d0
> Type: design

## Rules

- RULE-1: The checkout page shows the order total above the pay button [origin: design]

## Proof

- PROOF-1 (RULE-1): Load /checkout with one item in the basket; verify the text "Order total" appears above the button labelled "Pay" @e2e
```

`> Pinned:` is the hash of the named files, not a commit. Feature specs name the anchor with
`> Requires: checkout_design`, and its rules are counted with theirs. The full anchor grammar
is in [specs-and-anchors.md](specs-and-anchors.md).

`purlin:spec` reads the images in `designs/<feature>/` and drafts rules about what a person
would see on the screen, each tagged `[origin: design]`. Those rules belong to the designer:
an engineer may add a rule beside one and say in the pull request why the neighbour looks
wrong, but may not rewrite it or delete it.

## What a design proof looks like

A proof for a design rule is an end-to-end observable: a route, a state, visible text, an
element present. Never a selector, never a class name, never a pixel value.

| Write this | Not this |
|------------|----------|
| Load `/checkout` with one item; verify the text "Order total" appears above the button labelled "Pay" | Verify `.cart-total` renders above `#pay-btn` |
| Load `/checkout` with an empty basket; verify the text "Your basket is empty" | Verify the empty-state component mounts |

A proof that names a selector, a class or a pixel value is reported as
`implementation_coupling`: a refactor would break it without the screen changing. A rule only
a person's eye can settle is `@manual`, and its evidence is a signature with a one-line note
rather than a test.

## Screenshots as evidence

A test that captures a screenshot writes it to:

```
.purlin/runtime/attachments/<feature>/<PROOF-N>.png
```

That directory is runtime, so it is not committed. `purlin:audit` hashes each capture into
the record, and CI keeps the images as a build artifact. The record is what carries the claim;
the image is what a person looks at.

The review brief puts the pinned mock beside the screenshot the test captured, so signing a
design rule means reading the two images side by side and deciding whether the software shows
what the design shows. The walk is in [review-and-signing.md](review-and-signing.md).

## A new export stales the signatures

Re-exporting a screen changes the files, which changes the anchor's `> Pinned:` hash, which
stales every signature bound to that anchor's rules. That is the intended effect: a screen
that changed is a screen someone has to look at again.

The change surfaces in three places, in this order:

- `purlin:drift design` names the files that moved and the `origin: design` rules whose
  signatures went stale.
- `purlin:status` shows those rules' signed cell as `stale`.
- `purlin:sign` puts them on the review list, ordered by risk.

Advance the pin with `purlin:anchor sync <name>` when the anchor lives in another repository,
or commit the new hash with the exports when the anchor is local.

## Retired

Live design-tool sources, `> Visual-Reference:`, `> Visual-Hash:` and the visual hash
comparison are gone. A spec that still carries one of those fields parses, the field is
ignored, and the file is named once in the run's warnings.

## Next

- The anchor grammar in full: [specs-and-anchors.md](specs-and-anchors.md)
- Who does what: [working-together.md](working-together.md)
