# Policy: Release Process

> Label: "Policy: Release Process"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_critic.md

## 1. Purpose

This policy establishes the governance rules and invariants for the Purlin release checklist system. All features that implement release process tooling anchor here.

## 2. Invariants

### 2.1 Step ID Namespacing
*   All release checklist step IDs MUST be unique across the global and local namespaces within a given project.
*   Global step IDs MUST use the `purlin.` prefix. This namespace is reserved exclusively for steps defined in Purlin's own `tools/release/global_steps.json`.
*   Local step IDs MUST NOT use the `purlin.` prefix. Consumer projects SHOULD use a short project-specific namespace (e.g., `myproject.deploy_staging`) or a plain name (e.g., `deploy_staging`).
*   Attempting to define a local step with a `purlin.` ID is an error; the tooling MUST reject it.

### 2.2 Immutability of Global Steps in Consumer Projects
*   Consumer projects MUST NOT modify `tools/release/global_steps.json`. In a submodule deployment, this file resides inside the submodule directory and is subject to the Submodule Immutability Mandate.
*   Only Purlin's own Architect agent modifies global steps. Consumer-project Architects create and manage local steps exclusively.
*   The CDD Dashboard and CLI tooling treat `global_steps.json` as a read-only data source at runtime.

### 2.3 Local Config as Single Source of Truth
*   The local config file (`.purlin/release/config.json`) is the authoritative, ordered list of steps that constitute a project's release process.
*   Ordering and enable/disable state are determined solely by the local config. The global step definition order is informational, not authoritative.
*   If the local config does not exist, the system behaves as if all known steps are enabled and ordered by their declaration order in `global_steps.json` followed by `local_steps.json`.

### 2.4 Push-to-Remote Toggleability
*   The `purlin.push_to_remote` global step MUST be enabled by default in the auto-generated local config.
*   Projects MAY disable it by setting `enabled: false` in their local config. This supports air-gapped environments and projects where a CI/CD pipeline handles delivery.
*   When disabled, the step remains visible in the CDD Dashboard with a dimmed appearance and is not executed during the release process.

### 2.5 Auto-Discovery Safety
*   When a new global step is published by Purlin (via a submodule update), consumer projects automatically receive it on the next tool run without any manual config migration.
*   New steps are appended to the end of the local config with `enabled: true`. They do not displace existing custom ordering.
*   Unknown step IDs in the local config (referencing steps not present in either JSON file) are silently skipped with a warning. They never cause a hard error, ensuring forward compatibility when a global step is removed.

### 2.6 Architect Ownership
*   The `.purlin/release/` directory (both `local_steps.json` and `config.json`) is Architect-owned. The Architect agent creates and maintains these files.
*   The CDD Dashboard MAY write to `config.json` when the user reorders or toggles steps via the UI. This is the only automated write to Architect-owned files permitted.
*   Builders and QA agents do not modify release config files.

## 3. FORBIDDEN Patterns

*   `purlin.` prefix in local step IDs (Invariant 2.1). Pattern: `"id"\s*:\s*"purlin\.[^"]*"` in `.purlin/release/local_steps.json`.