import React from 'react';

const hues = { accent: 'var(--accent)', pass: 'var(--state-pass)', warn: 'var(--state-warn)', fail: 'var(--state-fail)', neutral: 'var(--state-neutral)', muted: 'var(--text-muted)' };

/** Mono chip for machine strings: agent names, gates, risk levels, commit shas. */
export function Tag({ children, tone = 'accent', style, ...rest }) {
  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center',
        fontFamily: 'var(--font-mono)', fontSize: 'var(--ui-sm)',
        padding: '3px 10px', borderRadius: 'var(--radius-sm)',
        border: '1px solid ' + hues[tone], color: hues[tone], background: 'transparent',
        whiteSpace: 'nowrap', ...style,
      }}
      {...rest}
    >
      {children}
    </span>
  );
}
