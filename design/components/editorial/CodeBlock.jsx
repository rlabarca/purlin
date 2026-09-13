import React from 'react';

/** Terminal well: sunken panel, Courier, cream on deep navy, with optional diff lines. */
export function CodeBlock({ children, lines, tone = 'sunken', size = 'var(--type-body-sm)', style, ...rest }) {
  const render = () => {
    if (!lines) return children;
    return lines.map((l, i) => {
      const t = typeof l === 'string' ? l : l.text;
      const kind = typeof l === 'string' ? (t.startsWith('-') ? 'del' : t.startsWith('+') ? 'add' : 'plain') : l.kind || 'plain';
      const col = kind === 'del' ? 'var(--state-fail)' : kind === 'add' ? 'var(--state-pass)' : kind === 'muted' ? 'var(--text-muted)' : kind === 'accent' ? 'var(--accent)' : 'var(--text-primary)';
      return <div key={i} style={{ color: col, whiteSpace: 'pre' }}>{t}</div>;
    });
  };
  return (
    <pre
      style={{
        margin: 0, fontFamily: 'var(--font-mono)', fontSize: size, lineHeight: 1.55,
        color: 'var(--text-primary)', padding: 'var(--space-6)',
        background: tone === 'sunken' ? 'var(--surface-sunken)' : 'transparent',
        border: '1.5px solid ' + (tone === 'accent' ? 'var(--border-accent)' : 'var(--border-default)'),
        borderRadius: 'var(--radius-sm)', overflowX: 'auto', ...style,
      }}
      {...rest}
    >
      {render()}
    </pre>
  );
}
