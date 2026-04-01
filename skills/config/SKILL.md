---
name: config
description: Read or write Purlin configuration
---

View or change Purlin settings via the `purlin_config` MCP tool.

## Usage

```
purlin:config                       Show all settings
purlin:config <key>                 Show a specific setting
purlin:config <key> <value>         Set a value
```

## Show All Settings

Call `purlin_config` with `action: "read"` (no key). Display the full config:

```
Purlin Configuration (.purlin/config.json):

  version: 2.0.0
  test_framework: auto
  spec_dir: specs
```

## Read a Setting

Call `purlin_config` with `action: "read"`, `key: "<key>"`.

```
purlin:config test_framework
→ test_framework: auto
```

## Write a Setting

Call `purlin_config` with `action: "write"`, `key: "<key>"`, `value: <value>`.

```
purlin:config test_framework pytest
→ Set test_framework = "pytest"
```

## Config File

The config file is `.purlin/config.json`. Default contents (from `templates/config.json`):

```json
{
  "version": "2.0.0",
  "test_framework": "auto",
  "spec_dir": "specs"
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `version` | string | `"2.0.0"` | Purlin config version |
| `test_framework` | string | `"auto"` | Test framework: `"auto"`, `"pytest"`, `"jest"`, `"shell"` |
| `spec_dir` | string | `"specs"` | Directory containing spec files |
