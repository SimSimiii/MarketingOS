"""The job requested by the user, independent of the argument chosen for it."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CampaignObjective = Literal["announcement", "acquisition", "activation", "recovery", "nurture", "custom"]
ReaderRelationship = Literal["unknown", "cold", "subscriber", "prospect", "customer"]


class CampaignIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: CampaignObjective = "custom"
    objective_source: Literal["user", "inferred"] = "user"
    reader_relationship: ReaderRelationship = "unknown"
    relationship_source: Literal["user", "inferred"] = "user"
    announcement: str = Field(default="", max_length=6000)
    reason_now: str = Field(default="", max_length=4000)
    desired_action: str = Field(default="", max_length=2000)

    def render(self) -> str:
        lines = [
            f"Campaign objective: {self.objective} ({self.objective_source}).",
            f"Reader relationship: {self.reader_relationship} ({self.relationship_source}).",
            "Non-buyers are not necessarily cold readers. Preserve the requested objective, audience and fixed destination.",
        ]
        if self.announcement:
            lines.append(f"User-provided announcement facts: {self.announcement}")
        if self.reason_now:
            lines.append(f"User-provided reason for timing: {self.reason_now}")
        if self.desired_action:
            lines.append(f"User-requested next action: {self.desired_action}")
        lines.append({
            "announcement": "Present the offering or stated change and its concrete relevance. A launch template alone establishes no release date or novelty. Do not turn this into a documentation tutorial by default.",
            "acquisition": "Earn a relevant first conversation or evaluation. Do not invent the recipient's pain, installed tools or past failures.",
            "activation": "Help the reader complete a useful first action; no replacement story or competitive difference is required.",
            "recovery": "Help the reader resume the established action. Do not invent a discount, deadline or reason they stopped.",
            "nurture": "Develop a useful supported idea and a proportionate next step for this relationship.",
            "custom": "Follow the user's request; a pain-to-solution argument is optional, not a universal format.",
        }[self.objective])
        return "\n".join(lines)


def infer_intent(request: str) -> CampaignIntent:
    """Legacy text gets a labelled interpretation, never invented launch facts."""
    objective: CampaignObjective = "custom"
    for pattern, candidate in (
        (r"abandoned.cart|cart recovery|panier abandonn", "recovery"),
        (r"\blaunch\b|\bannounc|\blancement\b|\bannonce", "announcement"),
        (r"\bonboarding\b|\bactivation\b", "activation"),
        (r"\bcold\b|\bacquisition\b|\bprospect", "acquisition"),
        (r"\bnurture\b|\bnewsletter\b", "nurture"),
    ):
        if re.search(pattern, request, re.IGNORECASE):
            objective = candidate
            break
    return CampaignIntent(
        objective=objective, objective_source="inferred", relationship_source="inferred",
        reader_relationship="cold" if re.search(r"\bcold\b|\bà froid\b", request, re.IGNORECASE) else "unknown",
    )
