import React from 'react';

const tones = {
  accent: 'var(--text-accent)',
  secondary: 'var(--text-secondary)',
  muted: 'var(--text-muted)',
  primary: 'var(--text-primary)',
};

/** Uppercase, letter-spaced eyebrow. The deck's only hierarchy device above a title. */
export function SectionLabel({ children, tone = 'accent', size = 'md', as: Tag = 'div', style, ...rest }) {
  return (
    <Tag
      style={{
        fontFamily: 'var(--font-sans)',
        fontSize: size === 'sm' ? 'var(--ui-xs)' : size === 'lg' ? 'var(--type-body-lg)' : 'var(--ui-sm)',
        letterSpacing: 'var(--tracking-label)',
        textTransform: 'uppercase',
        color: tones[tone],
        lineHeight: 'var(--leading-normal)',
        ...style,
      }}
      {...rest}
    >
      {children}
    </Tag>
  );
}
