/**
 * Headline count: big number, tracked caps label, mono footnote.
 * @startingPoint section="Data" subtitle="Dashboard summary tile" viewport="700x200"
 */
export interface StatTileProps {
  value: React.ReactNode;
  label: string;
  /** Small mono line under the label, e.g. "39 on host, 0 on claude-cli". */
  note?: string;
  tone?: 'primary' | 'pass' | 'warn' | 'fail' | 'neutral' | 'idle' | 'accent';
  align?: 'left' | 'center';
  style?: React.CSSProperties;
}
export declare function StatTile(props: StatTileProps): JSX.Element;
