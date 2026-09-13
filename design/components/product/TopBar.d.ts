/**
 * Product header bar: logo lockup, freshness status, right-aligned meta and actions.
 * @startingPoint section="Product" subtitle="Dashboard top bar" viewport="1200x92"
 */
export interface TopBarProps {
  /** Freshness sentence, e.g. "Data: 12h ago (pre-commit) — run purlin:status to refresh". */
  status?: React.ReactNode;
  statusTone?: 'pass' | 'warn' | 'fail' | 'neutral' | 'idle';
  /** Muted right-aligned strings, e.g. ["Design: 12h ago", "Integrity: 12h ago"]. */
  meta?: React.ReactNode[];
  actions?: React.ReactNode;
  /** 'light' swaps the mark to the navy-on-paper colourway. */
  logoTone?: 'dark' | 'light';
  logoSrc?: string;
  style?: React.CSSProperties;
}
export declare function TopBar(props: TopBarProps): JSX.Element;
