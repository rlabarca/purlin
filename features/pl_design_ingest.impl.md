# Implementation Notes: /pl-design-ingest

## Architecture

This is a Claude skill/command feature. The implementation consists of:

1. **Skill definition** (`.claude/commands/pl-design-ingest.md`): PM-only workflow guiding the LLM through artifact ingestion, token mapping, and feature file updates.
2. **Helper functions** (`tools/test_pl_design_ingest.py`): Self-contained helpers that implement the underlying operations the skill depends on. These are defined inline in the test file per the project's convention for skill features.
3. **Critic integration**: `parse_visual_spec` from the critic module validates Visual Specification sections including reference type detection (local, figma, live).

### Key Helper Functions

| Function | Purpose |
|----------|---------|
| `store_local_artifact` | Copies local image/PDF to `features/design/<stem>/` |
| `create_visual_spec_section` | Inserts/updates `## Visual Specification` with screen block |
| `read_design_anchors` | Parses `design_*.md` files to extract token tables |
| `map_color_to_token` | Reverse-maps hex color to anchor token name |
| `generate_token_map` | Maps observed Figma values to project tokens |
| `generate_brief_json` | Writes structured `brief.json` for Builder consumption |
| `is_figma_mcp_available` | Detects Figma MCP tools in session |
| `generate_figma_no_mcp_token_map` | Placeholder token map when MCP unavailable |
| `generate_figma_mcp_token_map` | Full token map from MCP metadata |
| `detect_identity_tokens` | Auto-detects matching Figma/project token names |
| `extract_annotations` | Filters behavioral notes from Figma annotations |

### Test Quality Audit
Evaluated via Haiku subagent (2026-03-18)
- Scenario: Ingest Local Image Artifact -> TestIngestLocalImageArtifact -> ALIGNED
- Scenario: Ingest Figma URL Without MCP -> TestIngestFigmaURLWithoutMCP -> ALIGNED
- Scenario: Figma MCP Auto-Setup When Processing Figma URL -> TestFigmaMCPAutoSetupWhenProcessingFigmaURL -> PARTIAL (constant string check for setup command is borderline AP-2, but the constant IS the implementation artifact)
- Scenario: Figma MCP Extracts Design Context Directly -> TestFigmaMCPExtractsDesignContextDirectly -> ALIGNED
- Scenario: Ingest Live Web Page URL -> TestIngestLiveWebPageURL -> ALIGNED
- Scenario: Re-Process Updated Artifact -> TestReProcessUpdatedArtifact -> ALIGNED
- Scenario: Anchor Inheritance Token Mapping -> TestAnchorInheritanceTokenMapping -> ALIGNED
- Scenario: No Design Anchor Fallback -> TestNoDesignAnchorFallback -> ALIGNED
- Scenario: Identity Token Auto-Detection During Figma Ingestion -> TestIdentityTokenAutoDetectionDuringFigmaIngestion -> ALIGNED
- Scenario: Annotation Extraction Pre-Populates Behavioral Context -> TestAnnotationExtractionPrePopulatesBehavioralContext -> ALIGNED
- Scenario: Code Connect Data Extracted Into Brief -> TestCodeConnectDataExtractedIntoBrief -> ALIGNED
- Scenario: Figma Dev Status Extracted During Ingestion -> TestFigmaDevStatusExtractedDuringIngestion -> ALIGNED
- Scenario: Dev Status Not Available Silently Omitted -> TestDevStatusNotAvailableSilentlyOmitted -> ALIGNED
