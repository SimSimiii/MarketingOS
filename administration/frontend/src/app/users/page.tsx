"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { api, atLeast, type UserPlan, type UserSummary } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { useSession } from "@/lib/session";
import { PageHeader, Shell } from "@/components/shell";
import { Badge, Button, Card, Empty, Field, Notice, Select } from "@/components/ui";

const PAGE_SIZE = 25;

export default function UsersPage() {
  return (
    <Shell>
      <UsersBody />
    </Shell>
  );
}

function UsersBody() {
  const { admin: me } = useSession();
  const [search, setSearch] = useState("");
  const [plan, setPlan] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);

  const [rows, setRows] = useState<UserSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api.listUsers({ search, plan, status, limit: PAGE_SIZE, offset });
      setRows(result.items);
      setTotal(result.total);
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Could not load accounts.");
    } finally {
      setLoading(false);
    }
  }, [search, plan, status, offset]);

  // Debounced, because this fires on every keystroke in the search box and
  // each one is a query with three counts behind it.
  useEffect(() => {
    const timer = setTimeout(load, 250);
    return () => clearTimeout(timer);
  }, [load]);

  return (
    <>
      <PageHeader
        title="Accounts"
        description="Everyone with a login. Search matches email, name and company."
      />

      {atLeast(me?.role, "admin") && <NewTesterForm onCreated={load} />}

      <div className="mb-4 grid gap-3 sm:grid-cols-[2fr_1fr_1fr]">
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-muted">Search</span>
          <input
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setOffset(0);
            }}
            placeholder="email, name or company"
            className="w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm placeholder:text-muted/60"
          />
        </label>
        <Select
          label="Plan"
          value={plan}
          onChange={(value) => {
            setPlan(value);
            setOffset(0);
          }}
        >
          <option value="">Any plan</option>
          <option value="free">Free</option>
          <option value="pro">Pro</option>
          <option value="business">Business</option>
        </Select>
        <Select
          label="Status"
          value={status}
          onChange={(value) => {
            setStatus(value);
            setOffset(0);
          }}
        >
          <option value="">Any status</option>
          <option value="active">Active</option>
          <option value="pending">Pending</option>
          <option value="suspended">Suspended</option>
        </Select>
      </div>

      <Notice>{error}</Notice>

      <div className="overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[54rem] text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs uppercase tracking-wider text-muted">
              <th className="px-4 py-3 font-medium">Account</th>
              <th className="px-4 py-3 font-medium">Plan</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 text-right font-medium">Brands</th>
              <th className="px-4 py-3 text-right font-medium">Campaigns</th>
              <th className="px-4 py-3 text-right font-medium">Runs</th>
              <th className="px-4 py-3 font-medium">Joined</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((user) => (
              <tr key={user.id} className="border-b border-line/60 last:border-0 hover:bg-white/3">
                <td className="px-4 py-3">
                  <Link href={`/users/${user.id}/`} className="font-medium text-violet-soft hover:underline">
                    {user.full_name ?? user.email}
                  </Link>
                  <p className="text-xs text-muted">
                    {user.email}
                    {user.company_name && ` · ${user.company_name}`}
                  </p>
                </td>
                <td className="px-4 py-3">
                  <Badge tone={user.plan === "free" ? "neutral" : "violet"}>{user.plan}</Badge>
                </td>
                <td className="px-4 py-3">
                  <Badge tone={user.status === "suspended" ? "danger" : "ok"}>{user.status}</Badge>
                </td>
                <td className="px-4 py-3 text-right tabular-nums">{user.brands}</td>
                <td className="px-4 py-3 text-right tabular-nums">{user.campaigns}</td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {user.runs}
                  {user.monthly_run_quota > 0 && (
                    <span className="text-muted"> / {user.monthly_run_quota}</span>
                  )}
                </td>
                <td className="px-4 py-3 text-muted">{formatDate(user.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && !loading && <Empty>No account matches that.</Empty>}
        {loading && rows.length === 0 && <Empty>Loading…</Empty>}
      </div>

      <div className="mt-4 flex items-center justify-between text-sm text-muted">
        <span>
          {total === 0
            ? "No accounts"
            : `${offset + 1}–${Math.min(offset + PAGE_SIZE, total)} of ${total}`}
        </span>
        <div className="flex gap-2">
          <Button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
            Previous
          </Button>
          <Button
            disabled={offset + PAGE_SIZE >= total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Next
          </Button>
        </div>
      </div>
    </>
  );
}

/** Public signup is off, so this is how a tester gets in. Leave the password
 *  blank and one is generated and shown here once - it is not stored anywhere
 *  this console can read it back from. */
function NewTesterForm({ onCreated }: { onCreated: () => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [plan, setPlan] = useState<UserPlan>("free");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<{ email: string; password: string | null } | null>(null);

  return (
    <div className="mb-6">
      <Card title="Create a test account">
        <form
          className="grid gap-3 sm:grid-cols-[2fr_1.5fr_1fr_1.5fr_auto] sm:items-end"
          onSubmit={async (event) => {
            event.preventDefault();
            setBusy(true);
            setError("");
            setCreated(null);
            try {
              const result = await api.createUser({
                email,
                plan,
                full_name: name || undefined,
                password: password || undefined,
              });
              setCreated({ email: result.user.email, password: result.generated_password });
              setEmail("");
              setName("");
              setPassword("");
              await onCreated();
            } catch (exception) {
              setError(exception instanceof Error ? exception.message : "Could not create it.");
            } finally {
              setBusy(false);
            }
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
          <Select label="Plan" value={plan} onChange={(value) => setPlan(value as UserPlan)}>
            <option value="free">Free</option>
            <option value="pro">Pro</option>
            <option value="business">Business</option>
          </Select>
          <Field
            label="Password"
            type="text"
            minLength={10}
            autoComplete="off"
            placeholder="blank = generate one"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Creating…" : "Create"}
          </Button>
        </form>
        <div className="mt-3 space-y-2">
          <Notice>{error}</Notice>
          {created && (
            <Notice tone="ok">
              {created.password
                ? `${created.email} can sign in with ${created.password} - copy it now, it is not shown again.`
                : `${created.email} can sign in with the password you chose.`}
            </Notice>
          )}
        </div>
      </Card>
    </div>
  );
}
