/** Ratio plus a thin progress bar. Colour is derived from the ratio unless overridden. */
export interface CoverageBarProps {
  covered?: number;
  total?: number;
  width?: number;
  showRatio?: boolean;
  tone?: 'pass' | 'warn' | 'fail' | 'neutral';
  style?: React.CSSProperties;
}
export declare function CoverageBar(props: CoverageBarProps): JSX.Element;
