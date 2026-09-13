/** Rule/spec state badge. Outline = measured by machine, solid = signed by a person. */
export interface StatusPillProps {
  status?: 'passing' | 'verified' | 'failing' | 'incomplete' | 'stale' | 'excluded' | 'drafted';
  /** Override the label text; the status still sets the colour. */
  children?: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function StatusPill(props: StatusPillProps): JSX.Element;
