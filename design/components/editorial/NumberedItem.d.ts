/**
 * Numbered definition row: slate numeral, cream term, cream definition, hairline above.
 * @startingPoint section="Editorial" subtitle="Numbered definition row" viewport="700x150"
 */
export interface NumberedItemProps {
  /** Usually a zero-padded string: "01". */
  index: React.ReactNode;
  term: React.ReactNode;
  children?: React.ReactNode;
  /** Draw the hairline above the row. Off for the last item in a stack. */
  rule?: boolean;
  style?: React.CSSProperties;
}
export declare function NumberedItem(props: NumberedItemProps): JSX.Element;
