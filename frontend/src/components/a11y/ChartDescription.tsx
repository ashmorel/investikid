import { VisuallyHidden } from './VisuallyHidden';

type Props = {
  summary: string;
  columns: string[];
  rows: (string | number)[][];
};

export function ChartDescription({ summary, columns, rows }: Props) {
  return (
    <VisuallyHidden>
      <p>{summary}</p>
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c} scope="col">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((cell, j) => (
                <td key={j}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </VisuallyHidden>
  );
}
