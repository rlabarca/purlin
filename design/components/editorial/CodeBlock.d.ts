export interface CodeLine { text: string; kind?: 'plain' | 'add' | 'del' | 'muted' | 'accent' }
/**
 * Terminal / diff well in Courier New on a sunken ground.
 * @startingPoint section="Editorial" subtitle="Terminal and diff well" viewport="700x260"
 */
export interface CodeBlockProps {
  children?: React.ReactNode;
  /** Pass lines to get per-line colouring; +/- prefixes auto-colour as add/del. */
  lines?: (string | CodeLine)[];
  tone?: 'sunken' | 'plain' | 'accent';
  size?: string;
  style?: React.CSSProperties;
}
export declare function CodeBlock(props: CodeBlockProps): JSX.Element;
