# Figma Web App Example

Build a weather app from scratch using a Figma design anchor. Five messages from start to verified.

**Prerequisites:** Purlin installed and initialized. See the [Installation Guide](../installation-guide.md).

## Step 1: Add a Figma Design Anchor

Share your Figma link:

```
here's our design system: figma.com/design/abc123/Weather-App-Design
```

Claude reads the Figma file via MCP, captures a reference screenshot, and creates a thin anchor with one visual match rule. The anchor doesn't extract individual CSS values -- the LLM reads Figma directly during build for full fidelity. See [references/figma_extraction_criteria.md](../../references/figma_extraction_criteria.md) for the extraction criteria.

```
specs/_anchors/weather_design.md
```

```markdown
# Anchor: weather_design

> Description: Visual design constraints for the weather app, sourced from Figma.
> Type: design
> Source: figma.com/design/abc123/Weather-App-Design
> Visual-Reference: figma://abc123/0-1
> Pinned: 2026-04-01T14:30:00Z

## What it does
Visual design constraints for the weather app, sourced from Figma.

## Rules
- RULE-1: Implementation must visually match the Figma design at the referenced node

## Proof
- PROOF-1 (RULE-1): Render component at same viewport size as Figma frame, capture screenshot, compare against Figma screenshot; verify visual match at design fidelity @e2e
```

One rule, one proof. The visual reference IS the spec.

## Step 2: Write a Feature Spec

```
I need a feature that shows current weather for a city using the OpenWeatherMap API
```

Claude writes the spec. Behavioral requirements come from the PM, not the Figma anchor:

```markdown
# Feature: current_weather

> Description: Displays current weather for a city using the OpenWeatherMap API.
> Requires: weather_design
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
- RULE-4: Handles API errors -- shows "Unable to load weather" message
- RULE-5: Caches responses for 10 minutes to avoid rate limiting

## Proof
- PROOF-1 (RULE-1): Mock API; call fetchWeather("Austin"); verify GET to /weather?q=Austin
- PROOF-2 (RULE-2): Return temp_f=72.6 from mock; verify display shows "73°F"
- PROOF-3 (RULE-3): Return condition="Clouds"; verify display shows "Cloudy"
- PROOF-4 (RULE-4): Return HTTP 500; verify "Unable to load weather" displayed
- PROOF-5 (RULE-5): Call fetchWeather("Austin") twice in 10 min; verify 1 API call
```

The spec requires `weather_design` -- so `purlin:status` includes the visual match rule in coverage. The feature must pass both its behavioral tests AND the visual comparison.

## Step 3: Build It

```
build it
```

Claude reads the spec and the Figma design directly via MCP for full visual fidelity. The anchor says "match the design" -- so the builder reads the visual reference, not extracted rules:

- Reads Figma via MCP -- gets the full design context (layout, colors, typography, spacing)
- Writes `src/components/WeatherDisplay.jsx` -- React component matching Figma layout
- Writes `src/api/weather.js` -- API client with caching
- Writes `src/utils/cache.js` -- simple TTL cache
- Writes tests with proof markers for both feature rules and design anchor rules:

```javascript
// Feature proofs (behavioral)
it("fetches from OpenWeatherMap [proof:current_weather:PROOF-1:RULE-1:default]", async () => {
  const mock = mockApi("/weather");
  await fetchWeather("Austin");
  expect(mock).toHaveBeenCalledWith(expect.stringContaining("q=Austin"));
});

// Design anchor proof (visual comparison)
it("matches Figma design [proof:weather_design:PROOF-1:RULE-1:e2e]", async () => {
  const page = await browser.newPage();
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/weather/austin");
  const screenshot = await page.screenshot();
  expect(screenshot).toMatchSnapshot("weather_design.png", { threshold: 0.05 }); // Jest/Playwright threshold, not a Purlin feature
});
```

> **Note:** The screenshot comparison uses your test framework's snapshot features (here, Jest + Playwright). Purlin provides the spec structure and proof markers; your test framework handles the pixel comparison. See [figma_extraction_criteria.md](../../references/figma_extraction_criteria.md#visual-fidelity-conventions) for threshold conventions.

## Step 4: Test It

```
run the tests
```

```
purlin:unit-test

6 tests passed. Proof files written.

Coverage:
  current_weather: 5/5 rules proved
  weather_design: 1/1 rules proved
```

## Step 5: Ship It

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

In 5 messages:

1. `here's our design system: <figma URL>` -- thin design anchor created (one visual match rule)
2. `I need a feature that shows current weather...` -- spec written with behavioral rules
3. `build it` -- code + tests written, Figma read directly for visual fidelity
4. `run the tests` -- proof files emitted, coverage reported
5. `verify and ship` -- verification receipt committed

The design anchor ensures every feature that requires it proves the visual match via screenshot comparison. Behavioral requirements live in the feature spec. If a designer updates the Figma file, run `purlin:anchor sync` -- `purlin:status` shows which proofs are stale.

## Later: Checking a Deployed Version

In CI:

```yaml
on: deploy
  - run: purlin:anchor sync --check-only  # fail if design changed
  - run: purlin:verify --audit             # re-run all tests from scratch
```

```
Clean-room re-execution: all tests pass.
vhash MATCH -- CI independently confirms verification.
Deploy approved.
```
