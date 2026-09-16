Use `DataTable` + `TableHead` + `TableRow` for the spec list. Pass the same `columns` array to head and rows so the grid tracks line up.

```jsx
const cols = [{label:'Spec',width:'2fr'},{label:'Coverage',width:'1.4fr'},{label:'Status',width:'1.2fr'}];
<DataTable>
  <TableHead columns={cols} />
  <TableRow columns={cols} cells={[<DisclosureRow label="skill_audit" />, <CoverageBar covered={19} total={19} />, <StatusPill status="passed" />]} />
</DataTable>
```

Rows are separated by 1px hairlines only — no zebra striping, no vertical rules.
