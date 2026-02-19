# Agentic DevOps Core

A project-agnostic, spec-driven development framework for AI-collaborative software engineering.

## Overview

Agentic DevOps Core is a workflow engine designed to maximize the effectiveness of LLM-based agents (Architects and Builders) in the software development lifecycle. It operates on the core principle that **"Code is Disposable, but Specifications are Eternal."**

By colocating technical implementation knowledge with behavioral specifications (Gherkin), the framework ensures that system context is never lost and that codebases can be reliably rebuilt or refactored by AI agents with minimal human intervention.

## Core Concepts

### 1. Spec-Driven Development
The project's state is defined 100% by specification files:
*   **Architectural Policies (`arch_*.md`):** Defining the "Constitution" and constraints of the system.
*   **Living Specifications (`*.md`):** Behavioral requirements (Gherkin) coupled with Implementation Notes (Tribal Knowledge).

### 2. Role Separation
The framework defines two distinct agent roles:
*   **The Architect:** Owns "The What and The Why." Designs specifications and enforces architectural integrity.
*   **The Builder:** Owns "The How." Implements code and tests based on specifications and documents discoveries.

### 3. Knowledge Colocation
Instead of separate documentation or global logs, implementation discoveries, hardware constraints, and design decisions are stored directly within the feature specifications they pertain to.

## Setup & Configuration

1.  **Initialize the Environment:**
    Copy the sample configuration folder to your project root:
    ```bash
    cp -r agentic_devops.sample .agentic_devops
    ```

2.  **Agent Context:**
    Point your AI agents (Architect and Builder) to the instructions located in `.agentic_devops/`:
    *   **Architect:** `.agentic_devops/ARCHITECT_INSTRUCTIONS.md`
    *   **Builder:** `.agentic_devops/BUILDER_INSTRUCTIONS.md`

3.  **Customize Config:**
    Edit `.agentic_devops/config.json` to set your preferred ports or enable Meta-Mode (`is_meta_agentic_dev: true`) if developing the framework itself.

## Directory Structure

*   `features/`: Meta-specifications for the Agentic Workflow itself.
*   `tools/`: Python-based DevOps tools that support the workflow (CDD Monitor, Software Map, etc.).
*   `ARCHITECT_INSTRUCTIONS.md`: The "Constitution" for the Architect role.
*   `BUILDER_INSTRUCTIONS.md`: The "Protocol" for the Builder role.
*   `HOW_WE_WORK.md`: The high-level philosophy and lifecycle.

## Feature Map
<!-- MERMAID_START -->
```mermaid
flowchart TD


    subgraph Agent_Instructions [" "]
        title_Agent_Instructions["AGENT INSTRUCTIONS"]
        agent_architect_instructions["Agent: Architect Instructions<br/><small>agent_architect_instructions.md</small>"]
        title_Agent_Instructions ~~~ agent_architect_instructions
        agent_builder_instructions["Agent: Builder Instructions<br/><small>agent_builder_instructions.md</small>"]
        title_Agent_Instructions ~~~ agent_builder_instructions
    end

    subgraph DevOps_Tools [" "]
        title_DevOps_Tools["DEVOPS TOOLS"]
        cdd_status_monitor["Tool: CDD Monitor<br/><small>cdd_status_monitor.md</small>"]
        title_DevOps_Tools ~~~ cdd_status_monitor
        software_map_generator["Tool: Software Map<br/><small>software_map_generator.md</small>"]
        title_DevOps_Tools ~~~ software_map_generator
    end

    subgraph Process [" "]
        title_Process["PROCESS"]
        arch_agentic_workflow["Arch: Agentic Workflow<br/><small>arch_agentic_workflow.md</small>"]
        title_Process ~~~ arch_agentic_workflow
        proc_history_management["Proc: History Management<br/><small>proc_history_management.md</small>"]
        title_Process ~~~ proc_history_management
        proc_release_protocol["Proc: Release Protocol<br/><small>proc_release_protocol.md</small>"]
        title_Process ~~~ proc_release_protocol
    end

    %% Relationships
    arch_agentic_workflow --> agent_architect_instructions
    arch_agentic_workflow --> agent_builder_instructions
    arch_agentic_workflow --> cdd_status_monitor
    arch_agentic_workflow --> proc_history_management
    arch_agentic_workflow --> proc_release_protocol
    arch_agentic_workflow --> software_map_generator

    %% Styling Definitions
    classDef default fill:#e1f5fe,stroke:#01579b,stroke-width:1px,color:black;
    classDef release fill:#f96,stroke:#333,stroke-width:2px,color:black,font-weight:bold;
    classDef hardware fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px,color:black;
    classDef ui fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1px,color:black;
    classDef process fill:#f1f8e9,stroke:#558b2f,stroke-width:1px,color:black;
    classDef subgraphTitle fill:none,stroke:none,color:#111,font-size:32px,font-weight:bold;

    %% Style Applications
    class title_Agent_Instructions subgraphTitle;
    class title_DevOps_Tools subgraphTitle;
    class title_Process subgraphTitle;
    class arch_agentic_workflow process;
    class proc_history_management process;
    class proc_release_protocol process;
```
<!-- MERMAID_END -->

## Agentic Evolution

| Version | Milestone | Workflow Changes |
| :--- | :--- | :--- |
| v1.0.1 | Port Isolation & Spec Refinement | Configurable ports for tool isolation; Meta-mode support; Refined instruction specs. |
| v1.0.0 | Framework Bootstrap | Isolated workflow from project context; Generalized role definitions. |

## License

This project is licensed under the MIT License.
