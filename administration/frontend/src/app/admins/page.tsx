"use client";

import { useCallback, useEffect, useState } from "react";

import { api, atLeast, type Admin, type AdminRole } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useSession } from "@/lib/session";
import { PageHeader, Shell } from "@/components/shell";
import { Badge, Button, Card, Empty, Field, Notice, Select } from "@/components/ui";

export default function AdminsPage() {
  return (
    <Shell>
      <AdminsBody />
    </Shell>
  );
}

function AdminsBody() {
  const { admin: me } = useSession();
  const [rows, setRows] = useState<Admin[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    try {
      setRows(await api.listAdmins());
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Could not load operators.");
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const canManage = atLeast(me?.role, "superadmin");

  async function run(action: () => Promise<unknown>, message: string) {
    setError("");
    setNote("");
    try {
      await action();
      setNote(message);
      await load();
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "That did not work.");
    }
  }

  return (
    <>
      <PageHeader
        title="Operators"
        description="Who can sign in to this console. There is no signup - accounts are created here."
      />

      {note && (
        <div className="mb-4">
          <Notice tone="ok">{note}</Notice>
        </div>
      )}
      {error && (
        <div className="mb-4">
          <Notice>{error}</Notice>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <div className="overflow-x-auto rounded-xl border border-line bg-surface">
          <table className="w-full min-w-[36rem] text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs uppercase tracking-wider text-muted">
                <th className="px-4 py-3 font-medium">Operator</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Last seen</th>
                {canManage && <th className="px-4 py-3 font-medium">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-line/60 last:border-0">
                  <td className="px-4 py-3">
                    <p className="font-medium">{row.full_name ?? row.email}</p>
                    <p className="text-xs text-muted">{row.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Badge tone={row.role === "superadmin" ? "violet" : "neutral"}>
                        {row.role}
                      </Badge>
                      {!row.is_active && <Badge tone="danger">disabled</Badge>}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-muted">{formatDateTime(row.last_login_at)}</td>
                  {canManage && (
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <select
                          value={row.role}
                          onChange={(event) =>
                            run(
                              () =>
                                api.updateAdmin(row.id, {
                                  role: event.target.value as AdminRole,
                                }),
                              `${row.email} is now ${event.target.value}.`,
                            )
                          }
                          className="rounded-lg border border-line bg-bg px-2 py-1 text-xs"
                          aria-label={`Role for ${row.email}`}
                        >
                          <option value="support">support</option>
                          <option value="admin">admin</option>
                          <option value="superadmin">superadmin</option>
                        </select>
                        <Button
                          className="px-2 py-1 text-xs"
                          // Deactivating yourself would leave the console
                          // reachable only through the bootstrap script; the
                          // API refuses it too.
                          disabled={row.id === me?.id}
                          onClick={() =>
                            run(
                              () => api.updateAdmin(row.id, { is_active: !row.is_active }),
                              row.is_active ? "Operator disabled." : "Operator re-enabled.",
                            )
                          }
                        >
                          {row.is_active ? "Disable" : "Enable"}
                        </Button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {loaded && rows.length === 0 && <Empty>No operators.</Empty>}
          {!loaded && <Empty>Loading…</Empty>}
        </div>

        <Card title="Add an operator">
          {canManage ? (
            <NewAdminForm onSubmit={run} />
          ) : (
            <p className="text-sm text-muted">
              Creating operators needs the <strong>superadmin</strong> role.
            </p>
          )}
        </Card>
      </div>
    </>
  );
}

function NewAdminForm({
  onSubmit,
}: {
  onSubmit: (action: () => Promise<unknown>, message: string) => Promise<void>;
}) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<string>("support");
  const [busy, setBusy] = useState(false);

  return (
    <form
      className="space-y-3"
      onSubmit={async (event) => {
        event.preventDefault();
        setBusy(true);
        await onSubmit(
          () =>
            api.createAdmin({
              email,
              password,
              full_name: name || undefined,
              role: role as AdminRole,
            }),
          `${email} can now sign in.`,
        );
        setEmail("");
        setName("");
        setPassword("");
        setBusy(false);
      }}
    >
      <Field
        label="Email"
        type="email"
        required
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />
      <Field label="Name" value={name} onChange={(event) => setName(event.target.value)} />
      <Field
        label="Password"
        type="password"
        required
        minLength={12}
        autoComplete="new-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        hint="At least 12 characters. Send it to them out of band and have them change it."
      />
      <Select label="Role" value={role} onChange={setRole}>
        <option value="support">support — read everything, change nothing</option>
        <option value="admin">admin — plans, quotas, suspensions</option>
        <option value="superadmin">superadmin — operators and deletions</option>
      </Select>
      <Button type="submit" variant="primary" disabled={busy} className="w-full">
        {busy ? "Creating…" : "Create operator"}
      </Button>
    </form>
  );
}
