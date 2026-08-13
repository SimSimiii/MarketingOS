import Link from "next/link";

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
import { api } from "@/lib/api-client";
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
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Activity</h1>
          <p className="text-sm text-muted-foreground">
            {execution
              ? `Every line logged during one run${agent ? ` by ${agent}` : ""}.`
              : "The most recent lines across all campaign runs."}
          </p>
        </div>
        {execution && (
          <Link href="/logs" className="text-sm text-primary hover:underline">
            Show all runs
          </Link>
        )}
      </div>

      <Card>
        <CardContent className="p-0">
          {logs.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">No logs yet.</p>
          ) : (
            <Table>
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
                    <TableCell className="text-sm text-muted-foreground">
                      {log.agent_id ?? "—"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground tabular-nums">
                      {log.step ?? "—"}
                    </TableCell>
                    <TableCell>{log.message}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
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
