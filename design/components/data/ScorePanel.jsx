import React from 'react';
import { Panel } from '../core/Panel.jsx';

/** The oversized percentage pair — proof design / proof integrity. */
export function ScorePanel({ value, label, detail, tone = 'pass', style, ...rest }) {
  const hue = tone === 'pass' ? 'var(--state-pass)' : tone === 'fail' ? 'var(--state-fail)' : tone === 'warn' ? 'var(--state-warn)' : 'var(--text-primary)';
  return (
    <Panel style={{ padding: 'var(--space-10) var(--space-6)', textAlign: 'center', ...style }} {...rest}>
      <div style={{ fontFamily: 'var(--font-sans)', fontSize: 56, fontWeight: 'var(--weight-bold)', lineHeight: 1, color: hue }}>{value}</div>
      <div style={{ marginTop: 'var(--space-3)', fontSize: 'var(--ui-sm)', letterSpacing: 'var(--tracking-label)', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>{label}</div>
      {detail ? <div style={{ marginTop: 'var(--space-2)', fontFamily: 'var(--font-mono)', fontSize: 'var(--ui-sm)', color: hue }}>{detail}</div> : null}
    </Panel>
  );
}
