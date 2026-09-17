import React from 'react';

/** The deck's 1px cream rule at 30% — the separator under every slide title. */
export function Divider({ tone = 'hairline', style, ...rest }) {
  const c = tone === 'accent' ? 'var(--border-accent)' : tone === 'strong' ? 'var(--border-strong)' : 'var(--border-default)';
  return <div role="separator" style={{ height: 1, background: c, width: '100%', ...style }} {...rest} />;
}
