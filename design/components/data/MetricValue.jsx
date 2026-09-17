import React from 'react';

/** A percentage or word-state in a table cell, coloured by threshold. */
export function MetricValue({ value, tone, mono = false, style, ...rest }) {
  let hue = 'var(--text-secondary)';
  if (tone) hue = `var(--state-${tone})`;
  else if (typeof value === 'string' && value.endsWith('%')) {
    const n = parseInt(value, 10);
    hue = n >= 80 ? 'var(--state-pass)' : n >= 50 ? 'var(--state-warn)' : 'var(--state-fail)';
  } else if (value === 'excluded' || value === 'structural') hue = 'var(--state-neutral)';
  return (
    <span style={{ fontFamily: mono || typeof value !== 'string' || !value.endsWith('%') ? 'var(--font-mono)' : 'var(--font-mono)', fontSize: 'var(--ui-base)', color: hue, ...style }} {...rest}>{value}</span>
  );
}
