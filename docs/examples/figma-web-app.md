# Figma Web App Example

Build a weather app from scratch using a Figma design invariant. Six messages from start to verified.

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- Figma MCP available (for design extraction)

## Step 1: Create the Project and Initialize

```bash
mkdir weather-app && cd weather-app
git init
claude plugin marketplace add git@bitbucket.org:rlabarca/purlin.git --scope project
```

Then start Claude Code, install Purlin, and set up the project:

```bash
claude
```

```
/plugin install purlin@purlin
```

Exit and restart for autocomplete, then set up the project:

```bash
exit
claude
```

```
create a new React weather app project
```

Claude scaffolds the project. Then initialize:

```
purlin:init
```

Output:
```
Detected: package.json → JavaScript/Jest
Created: .purlin/config.json
Created: specs/
Created: specs/_invariants/
Scaffolded: jest proof reporter in jest.config.js
```

## Step 2: Add a Figma Design Invariant

Share your Figma link:

```
here's our design system: figma.com/design/abc123/Weather-App-Design
```

Claude reads the Figma file via MCP, captures a reference screenshot, and creates a thin invariant with one visual match rule. The invariant doesn't extract individual CSS values — the LLM reads Figma directly during build for full fidelity. See [references/figma_extraction_criteria.md](../../references/figma_extraction_criteria.md) for the extraction criteria.

```
specs/_invariants/i_design_weather.md
```

```markdown
# Invariant: i_design_weather

> Type: design
> Source: figma.com/design/abc123/Weather-App-Design
> Visual-Reference: figma://abc123/0-1
> Pinned: 2026-04-01T14:30:00Z

## What it does
Visual design constraints for the weather app, sourced from Figma.

## Rules
- RULE-1: Implementation must visually match the Figma design at the referenced node

## Proof
- PROOF-1 (RULE-1): Render component at same viewport size as Figma frame, capture screenshot, compare against Figma screenshot; verify visual match within configured threshold @e2e
```

The invariant is read-only — the gate hook prevents edits. One rule, one proof. The visual reference IS the spec.

## Step 3: Write a Feature Spec

```
I need a feature that shows current weather for a city using the OpenWeatherMap API
```

Claude writes the spec. Behavioral requirements come from the PM, not the Figma invariant:

```markdown
# Feature: current_weather

> Requires: i_design_weather
> Scope: src/components/WeatherDisplay.jsx, src/api/weather.js, src/utils/cache.js
> Stack: react/tailwind, axios, openweathermap-api

## What it does
Fetches and displays the current weather for a given city using the
OpenWeatherMap API. Shows temperature, condition, and icon matching
the design system.

## Rules
- RULE-1: Fetches weather data from OpenWeatherMap /weather endpoint
- RULE-2: Displays temperature in Fahrenheit, rounded to nearest integer
- RULE-3: Shows weather condition text ("Sunny", "Cloudy", "Rainy")
- RULE-4: Handles API errors — shows "Unable to load weather" message
- RULE-5: Caches responses for 10 minutes to avoid rate limiting

## Proof
- PROOF-1 (RULE-1): Mock API; call fetchWeather("Austin"); verify GET to /weather?q=Austin
- PROOF-2 (RULE-2): Return temp_f=72.6 from mock; verify display shows "73°F"
- PROOF-3 (RULE-3): Return condition="Clouds"; verify display shows "Cloudy"
- PROOF-4 (RULE-4): Return HTTP 500; verify "Unable to load weather" displayed
- PROOF-5 (RULE-5): Call fetchWeather("Austin") twice in 10 min; verify 1 API call
```

The spec requires `i_design_weather` — so `sync_status` includes the visual match rule in coverage. The feature must pass both its behavioral tests AND the visual comparison.

## Step 4: Build It

```
build it
```

Claude reads the spec and the Figma design directly via MCP for full visual fidelity. The invariant says "match the design" — so the builder reads the visual reference, not extracted rules:

- Reads Figma via MCP — gets the full design context (layout, colors, typography, spacing)
- Writes `src/components/WeatherDisplay.jsx` — React component matching Figma layout
- Writes `src/api/weather.js` — API client with caching
- Writes `src/utils/cache.js` — simple TTL cache
- Writes tests with proof markers for both feature rules and design invariant rules:

```javascript
// Feature proofs (behavioral)
it("fetches from OpenWeatherMap [proof:current_weather:PROOF-1:RULE-1:default]", async () => {
  const mock = mockApi("/weather");
  await fetchWeather("Austin");
  expect(mock).toHaveBeenCalledWith(expect.stringContaining("q=Austin"));
});

// Design invariant proof (visual comparison)
it("matches Figma design [proof:i_design_weather:PROOF-1:RULE-1:e2e]", async () => {
  const page = await browser.newPage();
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/weather/austin");
  const screenshot = await page.screenshot();
  expect(screenshot).toMatchSnapshot("i_design_weather.png", { threshold: 0.05 });
});
```

## Step 5: Test It

```
run the tests
```

```
purlin:unit-test

6 tests passed. Proof files written.

Coverage:
  current_weather: 5/5 rules proved
  i_design_weather: 1/1 rules proved
```

## Step 6: Ship It

```
verify and ship
```

```
purlin:verify

All tests pass. 6/6 rules proved across 2 specs.
verify: [Complete:all] features=2 vhash=f7a2b9c1

Committed verification receipt.
```

## What Just Happened

In 6 messages:

1. `create a new weather app project` — project scaffolded
2. `here's our design system: <figma URL>` — thin design invariant created (one visual match rule)
3. `I need a feature that shows current weather...` — spec written with behavioral rules
4. `build it` — code + tests written, Figma read directly for visual fidelity
5. `run the tests` — proof files emitted, coverage reported
6. `verify and ship` — verification receipt committed

The design invariant ensures every feature that requires it proves the visual match via screenshot comparison. Behavioral requirements live in the feature spec. If a designer updates the Figma file, run `purlin:invariant sync` — `sync_status` shows which proofs are stale.

## Later: Checking a Deployed Version

In CI:

```yaml
on: deploy
  - run: purlin:invariant sync --check-only  # fail if design changed
  - run: purlin:verify --audit               # re-run all tests from scratch
```

```
Clean-room re-execution: all tests pass.
vhash MATCH — CI independently confirms verification.
Deploy approved.
```
