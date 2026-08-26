class CancellationToken:
    """Cooperative cancellation flag shared between an API request (which can
    ask a running campaign to stop) and the pipeline.

    Checked only between calls - never mid-model-call - so a cancelled run
    always leaves the campaign in a consistent, fully persisted state instead
    of an aborted network call and a half-written email. See
    EmailCampaignPipeline._guard for the check between whole emails, and
    CraftLoop._cancelled for the finer-grained one inside a single email's
    own revision loop - without it, "Stop" could sit behind a whole bake-off
    and several rewrites before it took effect.
    """

    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled
