/** Bare monospace command name, unboxed. The deck's top-right slide marker. */
export interface CommandChipProps {
  children?: React.ReactNode;
  tone?: 'secondary' | 'accent' | 'muted';
  size?: string;
  style?: React.CSSProperties;
}
export declare function CommandChip(props: CommandChipProps): JSX.Element;
