import React from 'react';

/** Triangle + name, the expandable spec identifier in the first column. */
export function DisclosureRow({ label, open = false, onToggle, mono = false, style, ...rest }) {
  return (
    <span onClick={onToggle} style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-4)', cursor: onToggle ? 'pointer' : 'default', ...style }} {...rest}>
      <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>{open ? '\u25BC' : '\u25B6'}</span>
      <span style={{ fontFamily: mono ? 'var(--font-mono)' : 'var(--font-sans)', fontSize: 'var(--ui-lg)', color: 'var(--text-primary)' }}>{label}</span>
    </span>
  );
}
