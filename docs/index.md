# Purlin Documentation

Purlin is an agentic development framework that coordinates four AI agents -- PM, Architect, Builder, and QA -- through structured specs, automated critics, and a real-time dashboard. These guides cover agent interaction, dashboard features, end-to-end workflows, and multi-machine collaboration.

---

## Agent Use

* [PM Agent Guide](pm-agent-guide.md) -- Practical guide for product managers using the PM agent to create feature specs from ideas, Figma designs, and live pages.
* [Parallel Execution in the Builder](parallel-execution-guide.md) -- How the Builder agent parallelizes independent features within a delivery plan phase using git worktrees.

## CDD Dashboard

* [Reading the CDD Status Grid](status-grid-guide.md) -- How to read the status grid showing every feature's current state across all four roles.
* [Spec Map Guide](spec-map-guide.md) -- Interactive dependency graph that visualizes feature prerequisites and category groupings.
* [Agent Configuration Guide](agent-configuration-guide.md) -- Dashboard panel for controlling each agent's model, optimization effort, permissions, and auto-start behavior.

## Workflow & Process

* [Installing and Updating Purlin](installation-guide.md) -- Adding Purlin to a new project, joining an existing team, and updating to a newer version.
* [The Critic and CDD](critic-and-cdd-guide.md) -- How the Critic coordination engine and CDD Monitor work together to direct agents and inform humans.
* [Purlin Testing Workflow Guide](testing-workflow-guide.md) -- Taking a feature from idea through spec, implementation, and verified automated regression coverage.

## Collaboration

* [Branch Collaboration Guide](branch-collaboration-guide.md) -- Multi-machine workflow for sharing branches between a PM and engineer through a shared remote repository.
