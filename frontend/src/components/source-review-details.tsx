import type { ApiSchemas } from "@/lib/api-schema";

export function SourceReviewDetails({ decision, sources }: {
  decision: ApiSchemas["GroundingDecision"];
  sources?: Record<string, string>;
}) {
  return (
    <div className="space-y-3 text-sm">
      <p>{decision.summary}</p>
      {decision.claims.map((claim, index) => (
        <div key={index} className="space-y-1 rounded-md border p-3">
          <p className="font-medium">{claim.text}</p>
          <p><span className="capitalize">{claim.status}</span> · {claim.explanation}</p>
          {claim.citations.map((citation, i) => (
            <blockquote key={i} className="border-l pl-3 text-muted-foreground">
              <p>{citation.quote}</p>
              {sources?.[citation.source_id] && (
                <cite className="break-all text-xs">{sources[citation.source_id]}</cite>
              )}
            </blockquote>
          ))}
        </div>
      ))}
      {decision.findings.map((finding, index) => (
        <p key={index}><strong>{finding.text}</strong> · {finding.explanation}</p>
      ))}
    </div>
  );
}
