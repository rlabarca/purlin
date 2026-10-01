# Feature: install

> Description: The install the README and the getting-started page tell a person to run works.
>   A test reads the install commands out of both pages and runs them, with the real `claude`
>   program, in a fresh project, with the marketplace address swapped for this checkout so the
>   code under test is the code being installed. It then checks, with no model, that the plugin
>   is installed and enabled and that every skill landed, and, with one call to the smallest
>   model, that Claude Code offers every Purlin skill. The model call runs only when the pages,
>   the plugin's manifest or a skill changed since it last passed, as any test does when a run
>   names no feature.
> Scope: README.md, docs/getting-started.md, .claude-plugin/plugin.json, .claude-plugin/marketplace.json, skills/*/SKILL.md
> Highest-Rule: 6
> Highest-Proof: 6

## Rules

- RULE-1: The README and the getting-started page give the same install commands, and the marketplace address in them is this repository's
- RULE-2: Running the pages' install commands in a fresh project, with the address swapped for this checkout, leaves the `purlin` plugin installed and enabled for that project
- RULE-3: After that install, every skill under `skills/` of this checkout is present in the installed plugin, word for word
- RULE-4: After that install, Claude Code offers every Purlin skill to the model in that project
- RULE-5: The install changes nothing outside the fresh project: the person's own Claude Code settings and installed plugins read the same before and after
- RULE-6: A command the pages tell a person to type inside Claude Code has a command-line form the test runs, and the test names any it cannot run

## Proof

- PROOF-1 (RULE-1): The fenced shell lines under "Install" in `README.md` and under step 1 of `docs/getting-started.md` are the same lines, and the address after `claude plugin marketplace add` reads `https://github.com/rlabarca/purlin.git`
- PROOF-2 (RULE-2): In an empty project made by the test, the pages' commands run with the address replaced by this checkout's folder; `claude plugin list` then shows `purlin@purlin` installed and enabled for that project
- PROOF-3 (RULE-3): After the install of PROOF-2, the folder the installed plugin reads its skills from holds a `SKILL.md` for each folder under `skills/` of this checkout, each file the same bytes as the checkout's
- PROOF-4 (RULE-4): After the install of PROOF-2, one prompt to the smallest model, run in that project with `claude -p`, asks it to list the slash commands that start `purlin:`; its answer names every skill folder under `skills/`
- PROOF-5 (RULE-5): The list of installed plugins and marketplaces of the person's own Claude Code, read before and after PROOF-2's install, is the same, and the test's project folder is deleted afterwards
- PROOF-6 (RULE-6): `/plugin install purlin@purlin` runs as `claude plugin install purlin@purlin --scope project`, and `/reload-plugins` is satisfied by starting a new `claude` process; a step typed inside Claude Code with no such form fails the test, naming the step
