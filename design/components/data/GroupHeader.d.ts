export interface GroupSummary { label: string; tone?: 'pass' | 'warn' | 'fail' | 'neutral' | 'idle' }
/** Group band above spec rows: caps title, count, coverage, dotted state summary. */
export interface GroupHeaderProps {
  title: string;
  count?: number;
  covered?: number;
  total?: number;
  summary?: GroupSummary[];
  open?: boolean;
  onToggle?: () => void;
  style?: React.CSSProperties;
}
export declare function GroupHeader(props: GroupHeaderProps): JSX.Element;
