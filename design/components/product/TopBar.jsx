import React from 'react';
import { Logo } from '../brand/Logo.jsx';

/** Dashboard chrome: mark, freshness line, timestamps, one outline action. */
export function TopBar({ status, statusTone = 'warn', meta = [], actions, logoTone = 'dark', logoSrc = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='165 130 670 330' width='670' height='330'%3E%3Cg stroke='%23C0793F' stroke-width='2' fill='none'%3E%3Cline x1='500' y1='130' x2='500' y2='460' stroke-dasharray='8,8'/%3E%3Cline x1='500' y1='145' x2='170' y2='409'/%3E%3Cline x1='500' y1='145' x2='830' y2='409'/%3E%3Cline x1='400' y1='210' x2='400' y2='255'/%3E%3Cline x1='600' y1='210' x2='600' y2='255'/%3E%3C/g%3E%3Cpolyline points='400,280 500,390 600,280' fill='none' stroke='%23E4DDD4' stroke-width='14'/%3E%3Cpath d='M 500 160 L 190 408 L 190 440 L 810 440 L 810 408 Z M 500 200 L 262.5 390 L 737.5 390 Z' fill-rule='evenodd' fill='%23E4DDD4'/%3E%3C/svg%3E", style, ...rest }) {
  return (
    <header
      style={{
        display: 'flex', alignItems: 'center', gap: 'var(--space-6)',
        height: 'var(--app-bar-h)', padding: '0 var(--space-6)',
        background: 'var(--canvas-deep)', borderBottom: '1px solid var(--border-hairline)',
        ...style,
      }}
      {...rest}
    >
      <Logo size={38} tone={logoTone} src={logoSrc} />
      {status ? (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-3)', color: `var(--state-${statusTone})`, fontSize: 'var(--ui-lg)' }}>
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: 'currentColor' }} />{status}
        </span>
      ) : null}
      <span style={{ flex: 1 }} />
      {meta.map((m, i) => <span key={i} style={{ fontSize: 'var(--ui-base)', color: 'var(--text-muted)' }}>{m}</span>)}
      {actions}
    </header>
  );
}
