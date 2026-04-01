# Figma Web App Example

Build a weather app from scratch using a Figma design invariant. Six messages from start to verified.

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- Purlin plugin installed (`claude plugin install purlin`)
- Figma MCP available (for design extraction)

## Step 1: Create the Project and Initialize

```bash
mkdir weather-app && cd weather-app
git init
npm init -y
npm install react react-dom tailwindcss
```

Then start Claude Code in the project directory:

```bash
claude
```

And initialize Purlin:

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

Claude reads the Figma file via MCP and creates an invariant:

```
specs/_invariants/i_design_weather.md
```

```markdown
# Invariant: i_design_weather

> Type: design
> Source: figma.com/design/abc123/Weather-App-Design
> Pinned: 2026-04-01T14:30:00Z

## Rules
- RULE-1: Temperature display uses 48px Inter Bold
- RULE-2: Background gradient shifts by condition (sunny=#FDB813, cloudy=#94A3B8, rainy=#3B82F6)
- RULE-3: Weather icon is 64x64px, centered above temperature
- RULE-4: City name uses 20px Inter Medium, white, top-left
- RULE-5: 5-day forecast cards use 8px border-radius, 16px padding
- RULE-6: All spacing uses 8px grid

## Proof
- PROOF-1 (RULE-1): Render temperature; verify font-size is 48px and font-weight is 700 @e2e
- PROOF-2 (RULE-2): Render with condition="sunny"; verify gradient starts with #FDB813 @e2e
- PROOF-3 (RULE-3): Render weather icon; verify 64x64px and centered in parent @e2e
- PROOF-4 (RULE-4): Render city name; verify 20px, white, top-left @e2e
- PROOF-5 (RULE-5): Render forecast card; verify 8px radius and 16px padding @e2e
- PROOF-6 (RULE-6): Render layout; verify spacing values are multiples of 8px @e2e
```

The invariant is read-only — the gate hook prevents edits. Rules come from Figma, not from the developer.

## Step 3: Write a Feature Spec

```
I need a feature that shows current weather for a city using the OpenWeatherMap API
```

Claude writes the spec:

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

The spec requires `i_design_weather` — so `sync_status` will include the design rules in coverage for this feature.

## Step 4: Build It

```
build it
```

Claude reads the spec and the Figma design (via MCP for full visual context), then:

- Writes `src/components/WeatherDisplay.jsx` — React component matching Figma layout
- Writes `src/api/weather.js` — API client with caching
- Writes `src/utils/cache.js` — simple TTL cache
- Writes tests with proof markers for both feature rules and design invariant rules:

```javascript
// Feature proofs
it("fetches from OpenWeatherMap [proof:current_weather:PROOF-1:RULE-1:default]", async () => {
  const mock = mockApi("/weather");
  await fetchWeather("Austin");
  expect(mock).toHaveBeenCalledWith(expect.stringContaining("q=Austin"));
});

// Design invariant proofs
it("temperature uses 48px Inter Bold [proof:i_design_weather:PROOF-1:RULE-1:default]", () => {
  render(<WeatherDisplay city="Austin" temp={73} />);
  const temp = screen.getByTestId("temperature");
  expect(getComputedStyle(temp).fontSize).toBe("48px");
  expect(getComputedStyle(temp).fontWeight).toBe("700");
});
```

## Step 5: Test It

```
run the tests
```

```
purlin:unit-test

11 tests passed. Proof files written.

Coverage:
  current_weather: 5/5 rules proved
  i_design_weather: 6/6 rules proved
```

## Step 6: Ship It

```
verify and ship
```

```
purlin:verify

All tests pass. 11/11 rules proved across 2 specs.
verify: [Complete:all] features=2 vhash=f7a2b9c1

Committed verification receipt.
```

## What Just Happened

In 6 messages:

1. `create a new weather app project` — project scaffolded
2. `here's our design system: <figma URL>` — design rules extracted as read-only invariant
3. `I need a feature that shows current weather...` — spec written with rules and proofs
4. `build it` — code + tests written, Figma referenced for visual context
5. `run the tests` — proof files emitted, coverage reported
6. `verify and ship` — verification receipt committed

The design invariant ensures every feature that requires it proves the design rules. If a designer updates the Figma file, run `purlin:invariant sync` — `sync_status` shows which proofs are stale.

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
