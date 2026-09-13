import React from 'react';

const pad = { sm: '4px 12px', md: '7px 16px', lg: '10px 22px' };
const fs = { sm: 'var(--ui-xs)', md: 'var(--ui-sm)', lg: 'var(--ui-base)' };

/** Outline-pill button — the dashboard's "Remote: 7 awaiting" control. */
export function Button({ children, variant = 'outline', tone = 'accent', size = 'md', disabled, style, ...rest }) {
  const hue = tone === 'accent' ? 'var(--accent)'
    : tone === 'pass' ? 'var(--state-pass)'
    : tone === 'fail' ? 'var(--state-fail)'
    : 'var(--text-secondary)';
  const base = {
    display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)',
    fontFamily: 'var(--font-sans)', fontSize: fs[size], lineHeight: 1.2,
    letterSpacing: '.01em', padding: pad[size], borderRadius: 'var(--radius-pill)',
    border: '1.5px solid transparent', cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.45 : 1, background: 'transparent', color: hue,
    transition: 'background var(--duration-fast) var(--ease-standard),color var(--duration-fast) var(--ease-standard),border-color var(--duration-fast) var(--ease-standard)',
  };
  const variants = {
    outline: { borderColor: hue },
    solid: { background: hue, color: 'var(--accent-contrast)', borderColor: hue },
    ghost: { borderColor: 'transparent', color: 'var(--text-secondary)' },
  };
  return <button disabled={disabled} style={{ ...base, ...variants[variant], ...style }} {...rest}>{children}</button>;
}
