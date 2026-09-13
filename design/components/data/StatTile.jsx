import React from 'react';
import { Panel } from '../core/Panel.jsx';

const hues = { pass: 'var(--state-pass)', warn: 'var(--state-warn)', fail: 'var(--state-fail)', neutral: 'var(--state-neutral)', idle: 'var(--state-idle)', primary: 'var(--text-primary)', accent: 'var(--accent)' };

/** Headline count with a caps label and an optional footnote. The dashboard's top row. */
export function StatTile({ value, label, note, tone = 'primary', align = 'center', style, ...rest }) {
  return (
    <Panel style={{ padding: 'var(--space-6) var(--space-5)', textAlign: align, ...style }} {...rest}>
      <div style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--ui-metric-xl)', fontWeight: 'var(--weight-bold)', lineHeight: 1, color: hues[tone] }}>{value}</div>
      <div style={{ marginTop: 'var(--space-3)', fontFamily: 'var(--font-sans)', fontSize: 'var(--ui-sm)', letterSpacing: 'var(--tracking-label)', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>{label}</div>
      {note ? <div style={{ marginTop: 'var(--space-2)', fontFamily: 'var(--font-mono)', fontSize: 'var(--ui-xs)', color: 'var(--text-muted)' }}>{note}</div> : null}
    </Panel>
  );
}
