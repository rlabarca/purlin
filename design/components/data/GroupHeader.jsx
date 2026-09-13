import React from 'react';
import { CoverageBar } from './CoverageBar.jsx';

/** Collapsible group band above a run of spec rows — WORKFLOWS (1), SKILLS (12). */
export function GroupHeader({ title, count, covered, total, summary = [], open = true, onToggle, style, ...rest }) {
  return (
    <div
      onClick={onToggle}
      style={{
        display: 'flex', alignItems: 'center', gap: 'var(--space-5)',
        padding: 'var(--space-5) var(--space-6)', background: 'var(--surface-2)',
        cursor: onToggle ? 'pointer' : 'default', ...style,
      }}
      {...rest}
    >
      <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>{open ? '\u25BC' : '\u25B6'}</span>
      <span style={{ fontFamily: 'var(--font-sans)', fontWeight: 'var(--weight-bold)', fontSize: 'var(--ui-lg)', letterSpacing: 'var(--tracking-label)', color: 'var(--text-primary)' }}>{title}</span>
      {count != null ? <span style={{ color: 'var(--text-muted)', fontSize: 'var(--ui-base)' }}>({count})</span> : null}
      <span style={{ flex: 1 }} />
      {total != null ? <CoverageBar covered={covered} total={total} /> : null}
      <span style={{ display: 'flex', gap: 'var(--space-5)', minWidth: 260 }}>
        {summary.map((s, i) => (
          <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 'var(--ui-base)', color: 'var(--text-primary)' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: `var(--state-${s.tone || 'pass'})` }} />{s.label}
          </span>
        ))}
      </span>
    </div>
  );
}
