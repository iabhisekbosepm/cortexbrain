"use client";

import { cn } from "@/lib/utils";

interface Column<T> {
  header: string;
  accessor: keyof T | ((row: T) => React.ReactNode);
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  emptyMessage?: string;
  className?: string;
}

export function DataTable<T>({ columns, data, emptyMessage = "No data", className }: DataTableProps<T>) {
  if (data.length === 0) {
    return <p className="text-sm text-gray-500 py-8 text-center">{emptyMessage}</p>;
  }

  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            {columns.map((col, i) => (
              <th key={i} className={cn("text-left py-3 px-3 font-medium text-gray-600", col.className)}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
              {columns.map((col, j) => (
                <td key={j} className={cn("py-3 px-3 text-gray-800", col.className)}>
                  {typeof col.accessor === "function"
                    ? col.accessor(row)
                    : (row[col.accessor] as React.ReactNode)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
