/** Uppercase letter-spaced eyebrow above a title or panel. */
export interface SectionLabelProps {
  children?: React.ReactNode;
  /** Colour role. Copper ('accent') is the deck default. */
  tone?: 'accent' | 'secondary' | 'muted' | 'primary';
  size?: 'sm' | 'md' | 'lg';
  as?: keyof JSX.IntrinsicElements;
  style?: React.CSSProperties;
}
export declare function SectionLabel(props: SectionLabelProps): JSX.Element;
