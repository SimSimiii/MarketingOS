import { ScrollText } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { ExpandableText } from "@/components/expandable-text";
import { PageHeader } from "@/components/page-header";
import { LogLevelBadge } from "@/components/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api-server";
import type { ExecutionLog } from "@/lib/types";

/** Optionally scoped to one run (`?execution=<id>`, how the live view links
 * here) and one specialist (`&agent=<agent_id>`), because "show me
 * everything that ever happened" stops being useful after the first
 * campaign. */
export default async function LogsPage({
  searchParams,
}: {
  searchParams: Promise<{ execution?: string; agent?: string }>;
}) {
  const { execution, agent } = await searchParams;

  const logs: ExecutionLog[] = execution
    ? await api
        .getExecutionLogs(execution, { agentId: agent, includeDebug: true })
        .catch(() => [])
    : await api.listLogs(200).catch(() => []);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={execution ? "One run" : "Across all runs"}
        title="Activity"
        description={
          execution
            ? `Every line logged during one run${agent ? ` by ${agent}` : ""}.`
            : "The most recent lines across all campaign runs."
        }
        // Scoped here from a run's live view, so the way out is the unscoped
        // list rather than whichever page happened to link in.
        backTo={execution ? { href: "/logs", label: "All activity" } : undefined}
      />

      <Card className="gap-0 py-0">
        <CardContent className="p-0">
          {logs.length === 0 ? (
            <EmptyState
              variant="inline"
              icon={ScrollText}
              title="Nothing logged yet"
              description="Every step a run takes is written here as it happens. Start a campaign and the lines will arrive."
            />
          ) : (
            <Table className="stacked-table">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-24">Level</TableHead>
                  <TableHead className="w-40">Agent</TableHead>
                  <TableHead className="w-16">Step</TableHead>
                  <TableHead>Message</TableHead>
                  <TableHead className="w-48">Timestamp</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>
                      <LogLevelBadge level={log.level} />
                    </TableCell>
                    <TableCell data-label="Agent" className="text-sm text-muted-foreground">
                      {log.agent_id ?? "—"}
                    </TableCell>
                    <TableCell
                      data-label="Step"
                      className="text-sm text-muted-foreground tabular-nums"
                    >
                      {log.step ?? "—"}
                    </TableCell>
                    {/* A run writes whole prompts into this column. Wrapping
                        them is right; letting one line own a screen and a half
                        is not - the excerpt is what makes the list scannable,
                        and the full text is one click away. */}
                    <TableCell data-label="Message" className="max-w-xl whitespace-normal">
                      <ExpandableText text={log.message} limit={180} />
                    </TableCell>
                    <TableCell data-label="Logged" className="text-xs text-muted-foreground">
                      {new Date(log.created_at).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
