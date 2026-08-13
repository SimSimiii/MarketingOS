"""Watching a campaign run, without the pipeline knowing what is watching.

A campaign takes minutes and spends nearly all of them inside single model
calls, so a run has to narrate itself or it looks hung. The pipeline announces
what it is doing through this interface; persistence and the live stream
implement it. Every method is a no-op by default, so a caller that only wants
the result implements nothing.

The unit that matters here is the *role invocation*: one writer turn, one cold
read, one critique. That is the granularity a user can follow ("writing email
2, second draft"), and it is also the granularity that costs money, which
makes it the honest thing to show.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.knowledge.artifacts import KnowledgeArtifacts
    from app.marketing.briefs import CampaignBrief
    from app.marketing.craft import EmailVersion
    from app.marketing.critic import Critique
    from app.marketing.email_copy import Email
    from app.marketing.gates import GateReport
    from app.marketing.reader import PanelRead
    from app.marketing.report import CampaignReport
    from app.marketing.sequence import SequenceReport


class RunObserver:
    """Hook points for one campaign run. All methods are no-ops."""

    # ------------------------------------------------------------- progress

    def on_phase(self, phase: str, message: str, data: dict[str, Any] | None = None) -> None:
        """The run moved, or has something to say about where it is."""

    def on_role_started(
        self, role_id: str, label: str, data: dict[str, Any] | None = None
    ) -> None:
        """One reasoning role is about to work. `label` is what a person
        watching should read: "Email 2 · second draft"."""

    def on_role_finished(
        self, role_id: str, summary: str, output: dict[str, Any] | None = None
    ) -> None: ...

    def on_role_failed(self, role_id: str, error: str) -> None: ...

    # ------------------------------------------------------------ artifacts

    def on_knowledge(
        self, artifacts: "KnowledgeArtifacts", reused: bool, version: int
    ) -> None: ...

    def on_brief(self, brief: "CampaignBrief") -> None: ...

    def on_draft(self, position: int, attempt: int, email: "Email") -> None: ...

    def on_repair(self, position: int, repair: int, reason: str) -> None:
        """A draft came back unsendable and the writer was asked again.

        Worth a hook of its own because a repair is a full model call at the
        writer's tier and, before this existed, left no trace anywhere: the
        reason went back to the model and nowhere else. A run where a third of
        the writer's calls are repairs looks identical, from the outside, to a
        run with none - and the fix is usually one line of a prompt.
        """

    def on_gates(self, position: int, attempt: int, report: "GateReport") -> None: ...

    def on_read(self, position: int, attempt: int, read: "PanelRead") -> None: ...

    def on_critique(self, position: int, attempt: int, critique: "Critique") -> None: ...

    def on_email_accepted(self, position: int, version: "EmailVersion") -> None: ...

    def on_sequence(self, report: "SequenceReport") -> None: ...

    def on_report(self, report: "CampaignReport") -> None: ...
