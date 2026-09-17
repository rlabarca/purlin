import React from 'react';

/** The Purlin truss mark, as supplied in the deck. Never redraw it. */
const LIGHT_SRC = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='165 130 670 330' width='670' height='330'%3E%3Cg stroke='%238F5626' stroke-width='2' fill='none'%3E%3Cline x1='500' y1='130' x2='500' y2='460' stroke-dasharray='8,8'/%3E%3Cline x1='500' y1='145' x2='170' y2='409'/%3E%3Cline x1='500' y1='145' x2='830' y2='409'/%3E%3Cline x1='400' y1='210' x2='400' y2='255'/%3E%3Cline x1='600' y1='210' x2='600' y2='255'/%3E%3C/g%3E%3Cpolyline points='400,280 500,390 600,280' fill='none' stroke='%230C3444' stroke-width='14'/%3E%3Cpath d='M 500 160 L 190 408 L 190 440 L 810 440 L 810 408 Z M 500 200 L 262.5 390 L 737.5 390 Z' fill-rule='evenodd' fill='%230C3444'/%3E%3C/svg%3E";

export function Logo({ variant = 'lockup', size = 40, color = 'var(--text-primary)', tone = 'dark', src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='165 130 670 330' width='670' height='330'%3E%3Cg stroke='%23C0793F' stroke-width='2' fill='none'%3E%3Cline x1='500' y1='130' x2='500' y2='460' stroke-dasharray='8,8'/%3E%3Cline x1='500' y1='145' x2='170' y2='409'/%3E%3Cline x1='500' y1='145' x2='830' y2='409'/%3E%3Cline x1='400' y1='210' x2='400' y2='255'/%3E%3Cline x1='600' y1='210' x2='600' y2='255'/%3E%3C/g%3E%3Cpolyline points='400,280 500,390 600,280' fill='none' stroke='%23E4DDD4' stroke-width='14'/%3E%3Cpath d='M 500 160 L 190 408 L 190 440 L 810 440 L 810 408 Z M 500 200 L 262.5 390 L 737.5 390 Z' fill-rule='evenodd' fill='%23E4DDD4'/%3E%3C/svg%3E", style, ...rest }) {
  const resolved = tone === 'light' ? LIGHT_SRC : src;
  const mark = <img src={resolved} alt="Purlin" style={{ display: 'block', height: size, width: 'auto' }} />;
  if (variant === 'mark') return <span style={{ display: 'inline-flex', ...style }} {...rest}>{mark}</span>;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-3)', ...style }} {...rest}>
      {mark}
      <span style={{ fontFamily: 'var(--font-sans)', fontSize: size * 0.7, lineHeight: 1, letterSpacing: 'var(--tracking-hero)', color }}>purlin</span>
    </span>
  );
}
