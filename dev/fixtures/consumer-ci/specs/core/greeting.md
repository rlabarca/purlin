# Feature: greeting

> Scope: greeting.py, tests/test_greeting.py
> Stack: python/stdlib
> Description: The one feature of the consumer-CI fixture project. RULE-1 is a claim any host can
>   prove; RULE-2 is a claim only an Ubuntu 24.04 host can prove, so the project has exactly one
>   proof awaiting the `ubuntu-24` runner until that runner commits its scoped proof file back.

## Rules

- RULE-1: `greet(name)` returns `Hello, <name>!`, and `Hello, world!` when the name is empty, so the greeting has one shape and an absent name is answered rather than crashed
- RULE-2: On an Ubuntu 24.04 host, `platform_tag()` returns `linux`. The value is the host's own report of what it is, so no other platform can stand in for it: this is the claim the `ubuntu-24` runner exists to prove

## Proof

- PROOF-1 (RULE-1): Call `greet("Ada")` and verify it returns exactly `Hello, Ada!`; call `greet("")` and verify it returns exactly `Hello, world!` @unit
- PROOF-2 (RULE-2): Call `platform_tag()` on the `ubuntu-24` runner and verify it returns exactly `linux` @unit @on(ubuntu-24)
