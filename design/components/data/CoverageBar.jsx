import React from 'react';

/** "19/19 ▬▬▬▬" — the ratio and its bar, always side by side. */
export function CoverageBar({ covered = 0, total = 0, width = 110, showRatio = true, tone, style, ...rest }) {
  const pct = total ? Math.round((covered / total) * 100) : 0;
  const hue = tone ? `var(--state-${tone})` : pct === 100 ? 'var(--state-pass)' : pct >= 60 ? 'var(--state-warn)' : 'var(--state-fail)';
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-4)', ...style }} {...rest}>
      {showRatio ? <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--ui-base)', color: 'var(--text-primary)' }}>{covered}/{total}</span> : null}
      <span style={{ width, height: 5, background: 'var(--border-hairline)', borderRadius: 'var(--radius-pill)', overflow: 'hidden', display: 'inline-block' }}>
        <span style={{ display: 'block', width: pct + '%', height: '100%', background: hue, transition: 'width var(--duration-slow) var(--ease-out)' }} />
      </span>
    </span>
  );
}
