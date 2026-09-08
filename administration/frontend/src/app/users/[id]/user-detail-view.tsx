"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { api, atLeast, type UserDetail, type Workspace } from "@/lib/api";
import { compact, formatDate, formatDateTime, money } from "@/lib/format";
import { useSession } from "@/lib/session";
import { PageHeader, Shell } from "@/components/shell";
import { Badge, Button, Card, Empty, Field, Notice, Select, Stat } from "@/components/ui";

const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

/**
 * The id comes from `window.location`, not from route params.
 *
 * At the edge this page's URL was rewritten onto the `_` placeholder before it
 * reached S3, so `useParams()` would hand back "_". The address bar still has
 * the real one.
 */
function useAccountId(): string | null {
  const [id, setId] = useState<string | null>(null);
  useEffect(() => {
    setId(window.location.pathname.match(UUID)?.[0] ?? null);
  }, []);
  return id;
}

export function UserDetailView() {
  return (
    <Shell>
      <Body />
    </Shell>
  );
}

function Body() {
  const id = useAccountId();
  const { admin } = useSession();
  const [user, setUser] = useState<UserDetail | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [detail, space] = await Promise.all([api.getUser(id), api.getWorkspace(id)]);
      setUser(detail);
      setWorkspace(space);
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Could not load this account.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

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

  if (id === null && user === null && !error) return <Empty>Reading the address…</Empty>;
  if (error && user === null) return <Notice>{error}</Notice>;
  if (user === null) return <Empty>Loading…</Empty>;

  const canWrite = atLeast(admin?.role, "admin");
  const canDelete = atLeast(admin?.role, "superadmin");
  const suspended = user.status === "suspended";

  return (
    <>
      <Link
        href="/users/"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-fg"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        All accounts
      </Link>

      <PageHeader
        title={user.full_name ?? user.email}
        description={[user.email, user.company_name].filter(Boolean).join(" · ")}
        action={
          <div className="flex items-center gap-2">
            <Badge tone={user.plan === "free" ? "neutral" : "violet"}>{user.plan}</Badge>
            <Badge tone={suspended ? "danger" : "ok"}>{user.status}</Badge>
          </div>
        }
      />

      {suspended && user.suspended_reason && (
        <div className="mb-4">
          <Notice>Suspended: {user.suspended_reason}</Notice>
        </div>
      )}
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

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Runs"
          value={user.runs}
          hint={
            user.monthly_run_quota > 0
              ? `${user.runs_used} used of ${user.monthly_run_quota} this period`
              : "no quota set (unlimited)"
          }
        />
        <Stat
          label="Model spend"
          value={money(user.estimated_cost_usd)}
          hint={`${compact(user.total_input_tokens + user.total_output_tokens)} tokens`}
        />
        <Stat label="Workspace" value={`${user.brands} / ${user.campaigns}`} hint="brands / campaigns" />
        <Stat
          label="Signed in"
          value={user.active_sessions}
          hint={`last seen ${formatDateTime(user.last_login_at)}`}
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card title="Plan and quota">
          {canWrite ? (
            <PlanForm user={user} onSubmit={run} />
          ) : (
            <p className="text-sm text-muted">
              Changing a plan needs the <strong>admin</strong> role.
            </p>
          )}
        </Card>

        <Card title="Access">
          {canWrite ? (
            <AccessActions user={user} onSubmit={run} canDelete={canDelete} />
          ) : (
            <p className="text-sm text-muted">
              Suspending an account needs the <strong>admin</strong> role.
            </p>
          )}
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="What they have built">
          {workspace === null || (workspace.brands.length === 0 && workspace.campaigns.length === 0) ? (
            <Empty>Nothing yet.</Empty>
          ) : (
            <div className="space-y-4 text-sm">
              <div>
                <p className="mb-1.5 text-xs uppercase tracking-wider text-muted">Brands</p>
                <ul className="space-y-1">
                  {workspace.brands.map((brand) => (
                    <li key={brand.id} className="flex justify-between gap-4">
                      <span className="truncate">{brand.name}</span>
                      <span className="shrink-0 text-muted">{formatDate(brand.created_at)}</span>
                    </li>
                  ))}
                  {workspace.brands.length === 0 && <li className="text-muted">None.</li>}
                </ul>
              </div>
              <div>
                <p className="mb-1.5 text-xs uppercase tracking-wider text-muted">Campaigns</p>
                <ul className="space-y-1">
                  {workspace.campaigns.map((campaign) => (
                    <li key={campaign.id} className="flex justify-between gap-4">
                      <span className="truncate">{campaign.name}</span>
                      <span className="shrink-0 text-muted">{campaign.status}</span>
                    </li>
                  ))}
                  {workspace.campaigns.length === 0 && <li className="text-muted">None.</li>}
                </ul>
              </div>
            </div>
          )}
          <p className="mt-4 border-t border-line pt-3 text-xs text-muted">
            Names and dates only. The console does not open a customer&apos;s copy.
          </p>
        </Card>

        <Card title="History">
          <AuditForTarget targetId={user.id} />
        </Card>
      </div>
    </>
  );
}

function PlanForm({
  user,
  onSubmit,
}: {
  user: UserDetail;
  onSubmit: (action: () => Promise<unknown>, message: string) => Promise<void>;
}) {
  const [plan, setPlan] = useState(user.plan as string);
  const [quota, setQuota] = useState(String(user.monthly_run_quota));
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  return (
    <form
      className="space-y-3"
      onSubmit={async (event) => {
        event.preventDefault();
        setBusy(true);
        await onSubmit(
          () =>
            api.changePlan(user.id, {
              plan,
              monthly_run_quota: Number(quota),
              reason: reason || undefined,
            }),
          `Moved to ${plan}.`,
        );
        setReason("");
        setBusy(false);
      }}
    >
      <Select label="Plan" value={plan} onChange={setPlan}>
        <option value="free">Free</option>
        <option value="pro">Pro</option>
        <option value="business">Business</option>
      </Select>
      <Field
        label="Runs per period"
        type="number"
        min={0}
        value={quota}
        onChange={(event) => setQuota(event.target.value)}
        hint="0 means unlimited."
      />
      <Field
        label="Reason"
        placeholder="invoice 12, trial extension…"
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        hint="Goes into the audit trail. Worth filling in."
      />
      <div className="flex gap-2">
        <Button type="submit" variant="primary" disabled={busy}>
          {busy ? "Saving…" : "Save plan"}
        </Button>
        <Button
          type="button"
          disabled={busy || user.runs_used === 0}
          onClick={async () => {
            setBusy(true);
            await onSubmit(
              () => api.setQuota(user.id, { runs_used: 0, reason: reason || "period reset" }),
              "Period reset.",
            );
            setBusy(false);
          }}
        >
          Reset the period
        </Button>
      </div>
    </form>
  );
}

function AccessActions({
  user,
  canDelete,
  onSubmit,
}: {
  user: UserDetail;
  canDelete: boolean;
  onSubmit: (action: () => Promise<unknown>, message: string) => Promise<void>;
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const suspended = user.status === "suspended";

  async function guard(action: () => Promise<unknown>, message: string) {
    setBusy(true);
    await onSubmit(action, message);
    setBusy(false);
  }

  return (
    <div className="space-y-3">
      {!suspended && (
        <Field
          label="Reason for suspending"
          placeholder="chargeback, abuse report…"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          hint="Shown to the customer when they try to sign in."
        />
      )}

      <div className="flex flex-wrap gap-2">
        {suspended ? (
          <Button
            variant="primary"
            disabled={busy}
            onClick={() => guard(() => api.unsuspend(user.id), "Account restored.")}
          >
            Lift the suspension
          </Button>
        ) : (
          <Button
            variant="danger"
            disabled={busy}
            onClick={() => guard(() => api.suspend(user.id, reason), "Account suspended.")}
          >
            Suspend
          </Button>
        )}

        <Button
          disabled={busy || user.active_sessions === 0}
          onClick={() =>
            guard(() => api.signOutUser(user.id), "Every session for this account was ended.")
          }
        >
          Sign out everywhere
        </Button>
      </div>

      <p className="text-xs text-muted">
        Suspending ends every live session immediately, rather than at the next sign-in.
      </p>

      {canDelete && (
        <div className="border-t border-line pt-3">
          <Button
            variant="danger"
            disabled={busy}
            onClick={() => {
              // A browser confirm rather than a modal: this is the one action
              // in the console that cannot be undone, and a native dialog is
              // harder to click through by muscle memory than a styled button.
              if (
                !window.confirm(
                  `Delete ${user.email}? Their brands and campaigns are kept but left unowned. This cannot be undone.`,
                )
              ) {
                return;
              }
              void guard(async () => {
                await api.deleteUser(user.id);
                window.location.href = "/users/";
              }, "Account deleted.");
            }}
          >
            Delete this account
          </Button>
          <p className="mt-2 text-xs text-muted">
            The work is not destroyed - brands and campaigns are unowned, and stay
            invisible until someone claims them.
          </p>
        </div>
      )}
    </div>
  );
}

function AuditForTarget({ targetId }: { targetId: string }) {
  const [rows, setRows] = useState<{ id: string; action: string; admin_email: string | null; created_at: string }[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api
      .audit({ target_id: targetId, limit: 20 })
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoaded(true));
  }, [targetId]);

  if (!loaded) return <Empty>Loading…</Empty>;
  if (rows.length === 0) return <Empty>Nothing has been changed on this account.</Empty>;

  return (
    <ul className="space-y-2 text-sm">
      {rows.map((row) => (
        <li key={row.id} className="flex justify-between gap-4 border-b border-line/50 pb-2 last:border-0">
          <span>
            <span className="font-medium">{row.action}</span>
            <span className="block text-xs text-muted">{row.admin_email ?? "system"}</span>
          </span>
          <span className="shrink-0 text-xs text-muted">{formatDateTime(row.created_at)}</span>
        </li>
      ))}
    </ul>
  );
}
