# Policy: Local Node.js Web App

> Label: "Architecture: Local Node.js Web App"
> Category: "Architecture"

## Purpose

Defines the structural and technology constraints for this project: a lightweight, locally-run Node.js web application. All features must conform to these constraints to ensure consistency and simplicity.

## Architecture Invariants

### Runtime

- The server MUST run on Node.js using Express.
- The app MUST serve on localhost (default port 3000).
- No build step or bundler is required — plain HTML, CSS, and vanilla JS only.

### Data Persistence

- Data MUST be written to local JSON files in a `data/` directory at the project root.
- Writes MUST append to an array in the target file; they MUST NOT overwrite existing entries.
- File uploads MUST be stored in an `uploads/` directory at the project root.
- Upload file size MUST NOT exceed 5MB.

### Frontend

- HTML pages MUST be served as static files or rendered server-side via Express.
- No frontend framework (React, Vue, etc.) is permitted.
- Styling MUST use plain CSS. Tailwind or CSS-in-JS is FORBIDDEN.
- Inter font MUST be loaded from Google Fonts.

## Scenarios

No automated or manual scenarios. This is a policy anchor node — its "scenarios" are
process invariants enforced by instruction files and tooling.
