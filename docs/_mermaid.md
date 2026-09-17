# The mermaid init block

For anyone writing or editing a diagram in these docs.

Every diagram in the doc set is mermaid, and every mermaid fence opens with the same init
block pasted as its first line. It sets the brand palette: navy ground, cream text, copper
accent, hairline borders. GitHub renders mermaid but reads no stylesheet, so the block
travelling with the diagram is what makes it render in the brand.

Paste this line, unchanged, directly under the opening ` ```mermaid ` of every diagram:

```
%%{init: {"theme": "base", "themeVariables": {"background": "#0C3444", "primaryColor": "#092936", "primaryTextColor": "#E4DDD4", "primaryBorderColor": "#C0793F", "lineColor": "#C0793F", "secondaryColor": "#0C3444", "tertiaryColor": "#092936", "fontFamily": "Arial", "textColor": "#E4DDD4"}}}%%
```

At most one diagram per doc, and only where the picture shows a mechanism a paragraph would
have to describe step by step. A diagram that restates a list is not worth its space.

The only other images in these docs are the five dashboard screenshots under `docs/images/`,
used by [dashboard.md](dashboard.md).
