# Feature: open_page

> Description: The opener `purlin:status --open` runs once the status has written the
>   dashboard page: it hands `purlin-report.html` to the default browser by its `file:`
>   address, on Windows, macOS and Linux alike. Where no browser can be reached, as on a
>   CI runner or over SSH, it prints the page's path instead and fails nothing.
> Scope: scripts/report/open_page.py
> Stack: python/stdlib, webbrowser, pathlib
> Highest-Rule: 4
> Highest-Proof: 5

## Rules

- RULE-1: The opener hands the project's `purlin-report.html` to the default browser and prints `Opened <path> in the default browser.`, `<path>` the page's absolute path, and exits 0
- RULE-2: Where the browser reports it opened nothing, or the variable `CI` is set, the opener prints `Dashboard: <path>. Open it in a browser.` and exits 0, and with `CI` set it hands the page to no browser at all
- RULE-3: Where the project has no page, the opener prints `purlin-report.html: no page yet. Run purlin:status, then purlin:status --open.`, hands nothing to a browser, and exits 1
- RULE-4: The address the browser is given is the page's absolute path as a `file:` address, every character a URL cannot carry as itself percent-encoded, so a folder with a space or a letter outside ASCII in its name opens the same on every operating system

## Proof

- PROOF-1 (RULE-1): A project holding its page runs the opener with a browser that reports it opened the address; the browser is given exactly one address, the opener prints `Opened <path> in the default browser.` and exits 0
- PROOF-2 (RULE-2): The same project runs the opener with a browser that reports it opened nothing; it prints `Dashboard: <path>. Open it in a browser.` and exits 0
- PROOF-3 (RULE-2): The same project runs the opener with `CI` set to `true`; no browser is given any address, it prints `Dashboard: <path>. Open it in a browser.` and exits 0
- PROOF-4 (RULE-3): A project with no `purlin-report.html` runs the opener; it prints `purlin-report.html: no page yet. Run purlin:status, then purlin:status --open.`, no browser is given any address, and it exits 1
- PROOF-5 (RULE-4): A project in a folder named `my café` runs the opener; the address the browser is given begins `file:`, holds `my%20caf%C3%A9/purlin-report.html`, and holds no space
