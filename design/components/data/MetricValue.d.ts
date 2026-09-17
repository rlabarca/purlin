/** Table-cell metric. Percentages colour themselves: >=80 pass, >=50 warn, below fail. */
export interface MetricValueProps {
  value: React.ReactNode;
  /** Force a hue instead of deriving it. */
  tone?: 'pass' | 'warn' | 'fail' | 'neutral' | 'idle';
  mono?: boolean;
  style?: React.CSSProperties;
}
export declare function MetricValue(props: MetricValueProps): JSX.Element;
