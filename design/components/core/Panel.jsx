import React from 'react';

/** The one container in the system: hairline box, no shadow, no rounding beyond 4px. */
export function Panel({ children, tone = 'default', padding = 'var(--space-6)', style, ...rest }) {
  const tones = {
    default: { background: 'var(--surface-1)', border: '1px solid var(--border-hairline)' },
    sunken: { background: 'var(--surface-sunken)', border: '1px solid var(--border-hairline)' },
    accent: { background: 'transparent', border: '1.5px solid var(--border-accent)' },
    veil: { background: 'var(--surface-2)', border: '1.5px solid var(--border-default)' },
  };
  return (
    <div style={{ borderRadius: 'var(--radius-sm)', padding, boxSizing: 'border-box', ...tones[tone], ...style }} {...rest}>
      {children}
    </div>
  );
}
