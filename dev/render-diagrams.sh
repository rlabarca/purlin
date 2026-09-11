#!/usr/bin/env bash
# Regenerate assets/lifecycle-*.svg from assets/src/*.mmd.
#
# The SVGs used to be committed with no source, so nobody could change them: the
# node positions and edge paths are computed by Mermaid's layout engine and are
# not hand-editable. The .mmd files in assets/src/ are now the source of record.
#
# Two things commonly get in the way, both fixable without disabling TLS checks:
#
#   1. `npm install` fails with UNABLE_TO_GET_ISSUER_CERT_LOCALLY behind a
#      TLS-inspecting proxy. Export the machine's trust store and point Node at it:
#        security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain >  /tmp/ca-bundle.pem
#        security find-certificate -a -p /Library/Keychains/System.keychain            >> /tmp/ca-bundle.pem
#        export NODE_EXTRA_CA_CERTS=/tmp/ca-bundle.pem
#
#   2. Puppeteer's bundled Chromium download fails for the same reason. Skip it and
#      use an installed browser:
#        export PUPPETEER_SKIP_DOWNLOAD=1
#        export PURLIN_CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
#
# Then:  npm install @mermaid-js/mermaid-cli && bash dev/render-diagrams.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$ROOT/assets/src"
OUT_DIR="$ROOT/assets"

MMDC="${MMDC:-$(command -v mmdc || true)}"
if [[ -z "$MMDC" ]]; then
  echo "mmdc not found. Install it, then re-run:" >&2
  echo "  npm install @mermaid-js/mermaid-cli && export MMDC=\$PWD/node_modules/.bin/mmdc" >&2
  exit 2
fi

CHROME="${PURLIN_CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
CFG="$(mktemp)"
if [[ -x "$CHROME" ]]; then
  printf '{ "executablePath": "%s", "args": ["--no-sandbox"] }\n' "$CHROME" > "$CFG"
else
  printf '{ "args": ["--no-sandbox"] }\n' > "$CFG"
fi

rc=0
for f in "$SRC_DIR"/*.mmd; do
  out="$OUT_DIR/$(basename "${f%.mmd}").svg"
  if "$MMDC" -i "$f" -o "$out" -b transparent -p "$CFG" >/dev/null 2>&1; then
    echo "  rendered $(basename "$out")"
  else
    echo "  FAILED   $(basename "$f")" >&2; rc=1
  fi
done
rm -f "$CFG"
exit $rc
