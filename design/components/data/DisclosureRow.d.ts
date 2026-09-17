/** Disclosure triangle plus a spec name; the first cell of every spec row. */
export interface DisclosureRowProps {
  label: React.ReactNode;
  open?: boolean;
  onToggle?: () => void;
  mono?: boolean;
  style?: React.CSSProperties;
}
export declare function DisclosureRow(props: DisclosureRowProps): JSX.Element;
