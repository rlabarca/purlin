/** One-line collapsible notice strip above a list. */
export interface NoticeBarProps {
  count?: number;
  children?: React.ReactNode;
  tone?: 'pass' | 'warn' | 'fail' | 'neutral';
  open?: boolean;
  onToggle?: () => void;
  style?: React.CSSProperties;
}
export declare function NoticeBar(props: NoticeBarProps): JSX.Element;
