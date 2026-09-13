/**
 * Pill button. Outline is the product default; solid is reserved for one primary action per view.
 * @startingPoint section="Core" subtitle="Outline, solid and ghost pills" viewport="700x150"
 */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'outline' | 'solid' | 'ghost';
  /** Hue role. 'accent' is copper; 'pass'/'fail' borrow the state hues. */
  tone?: 'accent' | 'pass' | 'fail' | 'neutral';
  size?: 'sm' | 'md' | 'lg';
}
export declare function Button(props: ButtonProps): JSX.Element;
