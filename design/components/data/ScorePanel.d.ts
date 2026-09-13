/** Oversized percentage with a mono "n of m measured" line beneath. */
export interface ScorePanelProps {
  value: React.ReactNode;
  label: string;
  detail?: string;
  tone?: 'pass' | 'warn' | 'fail' | 'primary';
  style?: React.CSSProperties;
}
export declare function ScorePanel(props: ScorePanelProps): JSX.Element;
