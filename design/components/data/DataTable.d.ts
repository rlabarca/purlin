export interface TableColumn { label?: string; width?: string; align?: 'left' | 'right' | 'center'; sorted?: boolean }
/**
 * Grid-based spec table: shell, header row, body row. No borders except 1px row rules.
 * @startingPoint section="Data" subtitle="Spec table with header and rows" viewport="700x260"
 */
export interface DataTableProps { children?: React.ReactNode; style?: React.CSSProperties }
export interface TableHeadProps { columns?: TableColumn[]; style?: React.CSSProperties }
export interface TableRowProps { columns?: TableColumn[]; cells?: React.ReactNode[]; selected?: boolean; onClick?: () => void; style?: React.CSSProperties }
export declare function DataTable(props: DataTableProps): JSX.Element;
export declare function TableHead(props: TableHeadProps): JSX.Element;
export declare function TableRow(props: TableRowProps): JSX.Element;
