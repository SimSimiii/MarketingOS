"use client";

import { useCallback, useEffect, useState } from "react";

import { api, type AuditEntry } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { PageHeader, Shell } from "@/components/shell";
import { Empty, Notice, Select } from "@/components/ui";

const ACTIONS = [
  "auth.login",
  "auth.logout",
  "user.plan_change",
  "user.quota_change",
  "user.suspend",
  "user.unsuspend",
  "user.force_logout",
  "user.delete",
  "admin.create",
  "admin.update",
  "admin.password_reset",
];

export default function AuditPage() {
  return (
    <Shell>
      <AuditBody />
    </Shell>
  );
}

function AuditBody() {
  const [action, setAction] = useState("");
  const [rows, setRows] = useState<AuditEntry[]>([]);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    setLoaded(false);
    try {
      setRows(await api.audit({ action, limit: 200 }));
      setError("");
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Could not load the trail.");
    } finally {
      setLoaded(true);
    }
  }, [action]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <>
      <PageHeader
        title="Audit trail"
        description="Every state-changing action an operator took, newest first. Append-only."
      />

      <div className="mb-4 max-w-xs">
        <Select label="Action" value={action} onChange={setAction}>
          <option value="">Everything</option>
          {ACTIONS.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
      </div>

      <Notice>{error}</Notice>

      <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
        {rows.map((row) => (
          <li key={row.id} className="px-5 py-4">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <p className="text-sm">
                <span className="font-medium">{row.action}</span>
                <span className="text-muted"> by {row.admin_email ?? "system"}</span>
                {row.target_type && (
                  <span className="text-muted">
                    {" "}
                    on {row.target_type} {row.target_id?.slice(0, 8)}
                  </span>
                )}
              </p>
              <p className="text-xs text-muted">
                {formatDateTime(row.created_at)}
                {row.ip_address && ` · ${row.ip_address}`}
              </p>
            </div>
            {row.detail && Object.keys(row.detail).length > 0 && (
              <pre className="mt-2 overflow-x-auto rounded-lg border border-line bg-bg px-3 py-2 text-xs text-muted">
                {JSON.stringify(row.detail, null, 2)}
              </pre>
            )}
          </li>
        ))}
      </ul>

      {loaded && rows.length === 0 && <Empty>Nothing recorded for that filter.</Empty>}
      {!loaded && <Empty>Loading…</Empty>}
    </>
  );
}
