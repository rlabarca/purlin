# Feature: greeting

> Scope: greeting.py, tests/test_greeting.py
> Stack: python/stdlib
> Description: The one feature of the consumer-CI fixture project. RULE-1 is a claim any host can
>   prove, so its proof carries no `@env` tag. RULE-2 is a claim only a Linux host can prove, so
>   its proof carries `@env(linux)` and reaches Recorded only when a Linux job's record says it
>   passed. The fixture is therefore the smallest project that needs a matrix.

## Rules

- RULE-1: `greet(name)` returns `Hello, <name>!`, and `Hello, world!` when the name is empty, so the greeting has one shape and an absent name is answered rather than crashed
- RULE-2: On a Linux host, `os_tag()` returns `linux`. The value is the host's own report of what it is, so no other operating system can stand in for it: this is the claim the Linux job exists to prove

## Proof

- PROOF-1 (RULE-1): Call `greet("Ada")` and verify it returns exactly `Hello, Ada!`; call `greet("")` and verify it returns exactly `Hello, world!` @unit
- PROOF-2 (RULE-2): Call `os_tag()` on a Linux runner and verify it returns exactly `linux` @unit @env(linux)
