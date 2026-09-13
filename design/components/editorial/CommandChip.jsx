import React from 'react';

/** A purlin: command set in Courier, blush on dark — the deck's slide-corner marker. */
export function CommandChip({ children, tone = 'secondary', size = 'var(--type-body-lg)', style, ...rest }) {
  const hue = tone === 'accent' ? 'var(--accent)' : tone === 'muted' ? 'var(--text-muted)' : 'var(--text-secondary)';
  return <span style={{ fontFamily: 'var(--font-mono)', fontSize: size, color: hue, whiteSpace: 'nowrap', ...style }} {...rest}>{children}</span>;
}
