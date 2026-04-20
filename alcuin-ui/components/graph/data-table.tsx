"use client"

import type { GraphSchema } from "@/lib/types"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export function DataTable({ schema }: { schema: GraphSchema }) {
  return (
    <Tabs defaultValue={schema.tables[0]?.name}>
      <TabsList className="mb-2">
        {schema.tables.map((t) => (
          <TabsTrigger key={t.name} value={t.name} className="text-xs">
            {t.name}
          </TabsTrigger>
        ))}
      </TabsList>
      {schema.tables.map((table) => (
        <TabsContent key={table.name} value={table.name}>
          <ScrollArea className="rounded-md border max-h-64">
            <table className="w-full text-xs">
              <thead className="border-b bg-muted/50 sticky top-0">
                <tr>
                  {table.columns.map((col) => (
                    <th key={col} className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.slice(0, 5).map((row, i) => (
                  <tr key={i} className="border-b last:border-0 hover:bg-muted/30">
                    {row.map((cell, j) => (
                      <td key={j} className="px-3 py-1.5 whitespace-nowrap text-foreground">
                        {String(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <ScrollBar orientation="horizontal" />
          </ScrollArea>
          {table.rows.length > 5 && (
            <p className="text-xs text-muted-foreground px-1">
              Showing 5 of {table.rows.length} rows
            </p>
          )}
        </TabsContent>
      ))}
    </Tabs>
  )
}
