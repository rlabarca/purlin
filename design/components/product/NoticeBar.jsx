import React from 'react';

/** Full-width collapsed notice — "▶ 1 uncommitted file". */
export function NoticeBar({ count, children, tone = 'warn', open = false, onToggle, style, ...rest }) {
  return (
    <div
      onClick={onToggle}
      style={{
        display: 'flex', alignItems: 'center', gap: 'var(--space-4)',
        padding: 'var(--space-5) var(--space-6)', background: 'var(--surface-1)',
        border: '1px solid var(--border-hairline)', borderRadius: 'var(--radius-sm)',
        cursor: onToggle ? 'pointer' : 'default', ...style,
      }}
      {...rest}
    >
      <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>{open ? '\u25BC' : '\u25B6'}</span>
      {count != null ? <span style={{ color: `var(--state-${tone})`, fontWeight: 'var(--weight-bold)' }}>{count}</span> : null}
      <span style={{ color: 'var(--text-primary)', fontSize: 'var(--ui-lg)' }}>{children}</span>
    </div>
  );
}
