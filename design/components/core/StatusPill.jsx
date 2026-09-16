import React from 'react';

const map = {
  passed: { label: 'PASSED', hue: 'var(--state-pass)', solid: false },
  signed: { label: 'SIGNED', hue: 'var(--state-pass)', solid: true },
  failed: { label: 'FAILED', hue: 'var(--state-fail)', solid: false },
  weak: { label: 'WEAK', hue: 'var(--state-warn)', solid: false },
  stale: { label: 'STALE', hue: 'var(--state-fail)', solid: false },
  'not required': { label: 'NOT REQUIRED', hue: 'var(--state-idle)', solid: false },
  drafted: { label: 'DRAFTED', hue: 'var(--state-idle)', solid: false },
};

/** The rule-cell badge. Solid fill means a person signed; outline means a machine computed it. */
export function StatusPill({ status = 'passed', children, style, ...rest }) {
  const s = map[status] || map.passed;
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
