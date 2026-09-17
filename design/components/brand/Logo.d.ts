/**
 * The Purlin truss mark, alone or locked up with the lowercase wordmark.
 * @startingPoint section="Brand" subtitle="Truss mark and wordmark lockup" viewport="700x150"
 */
export interface LogoProps {
  variant?: 'lockup' | 'mark';
  /** 'dark' is the cream mark for navy grounds; 'light' is the navy mark for paper and white. */
  tone?: 'dark' | 'light';
  /** Mark height in px. The wordmark scales from it. */
  size?: number;
  color?: string;
  /** Path to the supplied SVG, relative to the consuming page. */
  src?: string;
  style?: React.CSSProperties;
}
export declare function Logo(props: LogoProps): JSX.Element;
