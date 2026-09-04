"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api-client";

/**
 * The other half of a run that stopped to ask.
 *
 * The pipeline already refuses to spend a campaign's budget on material that
 * cannot carry one, and hands back the questions that would unblock it - no
 * customer is named, nothing is priced, there is no action to ask for. Those
 * questions were rendered onto the receipt and there was nowhere to answer
 * them: the user's only route back in was to write a document, find the
 * knowledge page, and upload it, at which point they have already been told
 * no twice.
 *
 * Answers become a knowledge document like any other, so they are read by the
 * compiler on the next run, they change the material's fingerprint (which is
 * what forces the recompile), and they are visible and deletable beside
 * everything else the business has handed over. Scoped to the brand where
 * there is one: what a company charges is true of the company, not of one
 * campaign, and the next campaign should not have to ask again.
 */
export function AnswerQuestionsCard({
  questions,
  campaignId,
  brandId,
}: {
  questions: string[];
  campaignId: string;
  brandId: string | null;
}) {
  const router = useRouter();
  const [answers, setAnswers] = useState<string[]>(() => questions.map(() => ""));
  const [saving, setSaving] = useState(false);

  const answered = answers.filter((answer) => answer.trim().length > 0).length;

  async function save(thenRun: boolean) {
    // Each answer is kept with the question above it. An answer on its own
    // ("about forty a week") is a fact with no subject, and the compiler
    // would have to guess what it is a fact about.
    const content = questions
      .map((question, index) => [question, answers[index]?.trim()] as const)
      .filter(([, answer]) => answer)
      .map(([question, answer]) => `## ${question}\n\n${answer}`)
      .join("\n\n");
    if (!content) {
      toast.error("Answer at least one of them first");
      return;
    }

    setSaving(true);
    try {
      await api.addKnowledgeSource({
        content: `# What the business told us directly\n\n${content}`,
        title: "Answers from you",
        ...(brandId ? { brand_id: brandId } : { campaign_id: campaignId }),
      });
      if (!thenRun) {
        toast.success("Saved - the next run reads this before it writes anything");
        router.refresh();
        return;
      }
      const advice = await api.getCampaignGenerationAdvice(campaignId);
      if (
        advice.override_required &&
        !window.confirm(
          [
            `${advice.recommendation?.state.replaceAll("_", " ") ?? advice.readiness}: ${advice.user_message}`,
            ...advice.reasons.map((reason) => `• ${reason}`),
            "",
            "Generate anyway? This override will be recorded with the new run.",
          ].join("\n"),
        )
      ) {
        toast.success("Answers saved. The campaign was not restarted.");
        return;
      }
      const execution = await api.restartCampaign(campaignId, advice.override_required);
      router.push(`/campaigns/${campaignId}/executions/${execution.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save your answers");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="ring-amber-500/40">
      <CardHeader>
        <CardTitle className="text-base">Answer these and this campaign becomes writable</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Nothing was spent on this run. The material we have contains nothing a stranger has any
          reason to believe, and no rewrite has ever added a proof that was not there - so it
          stopped before the first model call rather than writing five emails nobody would act on.
        </p>
        {questions.map((question, index) => (
          <div key={question} className="space-y-1.5">
            <label
              htmlFor={`answer-${index}`}
              className="block text-sm font-medium leading-snug"
            >
              {question}
            </label>
            <Textarea
              id={`answer-${index}`}
              rows={2}
              placeholder="A sentence is enough. A real number, a real name."
              value={answers[index] ?? ""}
              onChange={(event) => {
                const next = [...answers];
                next[index] = event.target.value;
                setAnswers(next);
              }}
            />
          </div>
        ))}
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" disabled={saving || answered === 0} onClick={() => save(true)}>
            {saving ? "Saving..." : "Save and run again"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={saving || answered === 0}
            onClick={() => save(false)}
          >
            Save for later
          </Button>
          <span className="text-xs text-muted-foreground">
            {answered} of {questions.length} answered
            {brandId ? " - kept with the brand, so the next campaign starts from it" : ""}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
