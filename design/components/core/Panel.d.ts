/**
 * Hairline container. Purlin has no drop shadows — depth is tint plus a 1px rule.
 * @startingPoint section="Core" subtitle="Hairline container, four tones" viewport="700x200"
 */
export interface PanelProps {
  children?: React.ReactNode;
  /** 'veil' reproduces the deck's 30%-cream box; 'accent' the copper-ruled one. */
  tone?: 'default' | 'sunken' | 'accent' | 'veil';
  padding?: string;
  style?: React.CSSProperties;
}
export declare function Panel(props: PanelProps): JSX.Element;
