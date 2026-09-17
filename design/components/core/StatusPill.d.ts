/** Rule-cell badge. Outline = computed by a machine, solid = signed by a person. */
export interface StatusPillProps {
  status?: 'passed' | 'signed' | 'failed' | 'weak' | 'stale' | 'not required' | 'drafted';
  /** Override the label text; the status still sets the colour. */
  children?: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function StatusPill(props: StatusPillProps): JSX.Element;
