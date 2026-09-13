/** Monospace chip for machine-generated strings (agent ids, gates, shas). */
export interface TagProps {
  children?: React.ReactNode;
  tone?: 'accent' | 'pass' | 'warn' | 'fail' | 'neutral' | 'muted';
  style?: React.CSSProperties;
}
export declare function Tag(props: TagProps): JSX.Element;
