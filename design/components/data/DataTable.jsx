import React from 'react';

/** Column-header row for a spec table. */
export function TableHead({ columns = [], style, ...rest }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: columns.map(c => c.width || '1fr').join(' '), gap: 'var(--space-4)', padding: 'var(--space-3) var(--space-6)', borderBottom: '1px solid var(--border-hairline)', ...style }} {...rest}>
      {columns.map((c, i) => (
        <div key={i} style={{ fontSize: 'var(--ui-xs)', letterSpacing: 'var(--tracking-label)', textTransform: 'uppercase', color: 'var(--text-muted)', textAlign: c.align || 'left' }}>
          {c.label}{c.sorted ? ' \u25B2' : ' \u25BE'}
        </div>
      ))}
    </div>
  );
}

/** One spec row. */
export function TableRow({ columns = [], cells = [], selected, onClick, style, ...rest }) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'grid', gridTemplateColumns: columns.map(c => c.width || '1fr').join(' '), gap: 'var(--space-4)',
        alignItems: 'center', padding: 'var(--space-5) var(--space-6)',
        borderBottom: '1px solid var(--border-hairline)',
        background: selected ? 'var(--surface-2)' : 'transparent',
        cursor: onClick ? 'pointer' : 'default', ...style,
      }}
      {...rest}
    >
      {cells.map((cell, i) => <div key={i} style={{ textAlign: columns[i]?.align || 'left', minWidth: 0 }}>{cell}</div>)}
    </div>
  );
}

/** Table shell. */
export function DataTable({ children, style, ...rest }) {
  return <div style={{ width: '100%', ...style }} {...rest}>{children}</div>;
}
