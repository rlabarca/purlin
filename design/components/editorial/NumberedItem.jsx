import React from 'react';
import { Divider } from '../core/Divider.jsx';

/** 01 / Term / definition — the deck's list row, with a hairline above. */
export function NumberedItem({ index, term, children, rule = true, style, ...rest }) {
  return (
    <div style={style} {...rest}>
      {rule ? <Divider /> : null}
      <div style={{ display: 'grid', gridTemplateColumns: '146px 336px 1fr', gap: 'var(--space-6)', alignItems: 'start', padding: 'var(--space-6) 0' }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--type-body)', color: 'var(--text-muted)' }}>{index}</div>
        <div style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--type-caption)', color: 'var(--text-primary)' }}>{term}</div>
        <div style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--type-body)', color: 'var(--text-primary)', lineHeight: 'var(--leading-normal)' }}>{children}</div>
      </div>
    </div>
  );
}
