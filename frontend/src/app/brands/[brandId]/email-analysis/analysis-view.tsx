"use client";

import { useState } from "react";
import { toast } from "sonner";
import { BrandSectionHeader } from "../../brand-ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api-client";
import type { EmailAnalysis, EmailAnalysisCapabilities } from "@/lib/email-analysis-types";
import { PageData, refreshPage, usePageData, useRouteIds } from "@/lib/page-data";

function Workspace({ brandId, history, capabilities }: { brandId: string; history: EmailAnalysis[]; capabilities: EmailAnalysisCapabilities }) {
  const [subject, setSubject] = useState("");
  const [preview, setPreview] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState("");
  const [objective, setObjective] = useState("");
  const [mergeFields, setMergeFields] = useState("");
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<EmailAnalysis | null>(null);
  const [coldRead, setColdRead] = useState(false);
  const analysis = selected ?? history[0];
  const running = history.some((item) => item.state === "running") || analysis?.state === "running";

  async function analyse() {
    setBusy(true);
    try {
      setSelected(await api.analyseEmail(brandId, {
        subject, preview_text: preview, body, audience, objective, cold_read: coldRead,
        merge_fields: mergeFields.split(",").map((item) => item.trim()).filter(Boolean),
      }));
      refreshPage();
    } catch (error) { toast.error(error instanceof Error ? error.message : "Analysis could not start"); }
    finally { setBusy(false); }
  }

  async function refresh() {
    setBusy(true);
    try {
      api.invalidate();
      if (analysis) setSelected(await api.getEmailAnalysis(brandId, analysis.id));
      refreshPage();
    } catch (error) { toast.error(error instanceof Error ? error.message : "Could not refresh"); }
    finally { setBusy(false); }
  }

  function loadDraft(item: EmailAnalysis) {
    setSelected(item);
    setSubject(item.request.subject); setBody(item.request.body);
    setPreview(item.request.preview_text ?? ""); setAudience(item.request.audience ?? "");
    setObjective(item.request.objective ?? ""); setMergeFields(item.request.merge_fields?.join(", ") ?? "");
  }

  return <div className="space-y-5">
    <BrandSectionHeader title="Review your email" description="Paste a draft, check its support and get specific feedback from an optional simulated reader." />
    <div className="grid gap-5 xl:grid-cols-2">
      <form className="surface space-y-4 rounded-2xl p-5" onSubmit={(event) => { event.preventDefault(); void analyse(); }}>
        <div className="space-y-2"><Label htmlFor="analysis-subject">Subject</Label><Input id="analysis-subject" required maxLength={500} value={subject} onChange={(e) => setSubject(e.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="analysis-preview">Preview text (optional)</Label><Input id="analysis-preview" maxLength={1000} value={preview} onChange={(e) => setPreview(e.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="analysis-body">Complete email, including its next step and signature</Label><Textarea id="analysis-body" required maxLength={30000} rows={13} value={body} onChange={(e) => setBody(e.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="analysis-audience">Who receives this? Include their situation.</Label><Textarea id="analysis-audience" rows={2} maxLength={2000} value={audience} onChange={(e) => setAudience(e.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="analysis-objective">What should the reader do?</Label><Input id="analysis-objective" maxLength={2000} value={objective} onChange={(e) => setObjective(e.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="analysis-fields">Intended merge fields, separated by commas (optional)</Label><Input id="analysis-fields" value={mergeFields} onChange={(e) => setMergeFields(e.target.value)} placeholder="first_name, company" /></div>
        <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={coldRead} disabled={!capabilities.cold_read_available} onChange={(e) => setColdRead(e.target.checked)} className="mt-1" /><span>Add one cold reader · usually {capabilities.expected_calls} model call<br /><span className="text-xs text-muted-foreground">A malformed answer may need a second call; transport retries follow the existing limits. Checks alone use no model call. A cold read uses the account&apos;s job quota.</span></span></label>
        {!capabilities.cold_read_available && <p className="text-sm text-amber-200">{capabilities.reason}</p>}
        <Button type="submit" disabled={busy || Boolean(running && coldRead) || !subject.trim() || !body.trim()}>{busy ? "Working…" : coldRead ? "Check and request a cold read" : "Check this email"}</Button>
      </form>
      <div className="space-y-4">
        {analysis ? <section className="surface space-y-4 rounded-2xl p-5" aria-live="polite">
          <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold">Analysis · {analysis.state}</h2><Button size="sm" variant="outline" disabled={busy} onClick={refresh}>Refresh results</Button></div>
          <p className="text-sm text-muted-foreground">{analysis.request.subject} · {analysis.calls} model call(s){analysis.result.knowledge_version ? ` · Knowledge v${analysis.result.knowledge_version}` : " · Product facts not checked"}</p>
          {analysis.state === "running" && <p className="text-sm">The cold read is running. Refresh results to retrieve it; the checks below are already saved.</p>}
          {analysis.error && <p className="text-sm text-amber-200">{analysis.error}</p>}
          {(["verification", "context", "editorial"] as const).map((category) => <div key={category} className="space-y-2">
            <h3 className="text-sm font-semibold">{{ verification: "Passages to verify", context: "Missing context", editorial: "Editorial suggestions" }[category]}</h3>
            {analysis.result.findings.filter((item) => item.category === category).map((item, index) => <div key={`${item.check}-${index}`} className="rounded-lg border border-white/10 p-3 text-sm"><p>{item.detail}</p><p className="mt-2 text-muted-foreground">{item.action}</p></div>)}
            {!analysis.result.findings.some((item) => item.category === category) && <p className="text-sm text-muted-foreground">No issue detected by these checks.</p>}
          </div>)}
          {analysis.result.reader && <div className="space-y-2 border-t border-white/10 pt-4">
            <h3 className="font-semibold">Cold read {analysis.result.reader.assessment !== null ? `· ${analysis.result.reader.assessment}/10` : "· no score"}</h3>
            <p className="text-xs text-muted-foreground">One AI simulation, uncalibrated. This score does not predict clicks or conversion.</p>
            {analysis.result.reader.reported ? <>
              <p className="text-sm">Understanding: {analysis.result.reader.understood ? "clear" : "unclear"} · {analysis.result.reader.what_it_sells}</p>
              {analysis.result.reader.biggest_doubt && <p className="text-sm">Main doubt: {analysis.result.reader.biggest_doubt}</p>}
              {analysis.result.reader.stopped_at && <p className="text-sm">Stopped at: {analysis.result.reader.stopped_at}</p>}
              {analysis.result.reader.relevance_feedback && <p className="text-sm">Audience relevance: {analysis.result.reader.relevance_feedback}</p>}
              {analysis.result.reader.fixes.length > 0 && <ul className="list-disc space-y-1 pl-5 text-sm">{analysis.result.reader.fixes.map((fix, index) => <li key={index}>{fix}</li>)}</ul>}
            </> : <p className="text-sm">The reader did not return a verdict. Saved checks remain available.</p>}
          </div>}
          <details className="text-xs text-muted-foreground"><summary className="cursor-pointer">What this analysis covers</summary><ul className="mt-2 list-disc space-y-2 pl-4">{analysis.result.coverage.map((text) => <li key={text}>{text}</li>)}</ul></details>
        </section> : <div className="surface rounded-2xl p-6 text-sm text-muted-foreground">Your analysis will appear here. Missing evidence is flagged for verification; it is never labelled false merely because it is absent from the knowledge base.</div>}
        {history.length > 0 && <section className="surface space-y-2 rounded-2xl p-5"><h2 className="text-sm font-semibold">Saved analyses</h2>{history.map((item) => <button key={item.id} type="button" onClick={() => loadDraft(item)} className="block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-white/5">{item.request.subject}<span className="ml-2 text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString()} · {item.state}</span></button>)}</section>}
      </div>
    </div>
  </div>;
}

export function EmailAnalysisView() {
  const { brandId } = useRouteIds();
  const state = usePageData(async () => {
    const [history, capabilities] = await Promise.all([api.listEmailAnalyses(brandId), api.getEmailAnalysisCapabilities(brandId)]);
    return { history, capabilities };
  }, [brandId]);
  return <PageData state={state}>{({ history, capabilities }) => <Workspace key={brandId} brandId={brandId} history={history} capabilities={capabilities} />}</PageData>;
}
