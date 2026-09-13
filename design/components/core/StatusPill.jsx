import React from 'react';

const map = {
  passing: { label: 'PASSING', hue: 'var(--state-pass)', solid: false },
  verified: { label: 'VERIFIED', hue: 'var(--state-pass)', solid: true },
  failing: { label: 'FAILING', hue: 'var(--state-fail)', solid: false },
  incomplete: { label: 'INCOMPLETE', hue: 'var(--state-warn)', solid: false },
  stale: { label: 'STALE', hue: 'var(--state-warn)', solid: false },
  excluded: { label: 'EXCLUDED', hue: 'var(--state-neutral)', solid: false },
  drafted: { label: 'DRAFTED', hue: 'var(--state-idle)', solid: false },
};

/** The seven-state badge. Solid fill means a human signed; outline means a machine measured. */
export function StatusPill({ status = 'passing', children, style, ...rest }) {
  const s = map[status] || map.passing;
  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: 'var(--font-sans)', fontSize: 'var(--ui-sm)', fontWeight: 'var(--weight-bold)',
        letterSpacing: '.08em', padding: '5px 16px', borderRadius: 'var(--radius-pill)',
        border: '1.5px solid ' + s.hue,
        background: s.solid ? s.hue : 'transparent',
        color: s.solid ? 'var(--canvas-deep)' : s.hue,
        ...style,
      }}
      {...rest}
    >
      {children || s.label}
    </span>
  );
}
