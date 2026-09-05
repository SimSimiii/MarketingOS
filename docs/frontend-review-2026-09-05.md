# Frontend review — 2026-09-05

## Scope and findings

Reviewed the app shell, design tokens, dashboard, campaign and brand lists, shared UI primitives, API client and creation dialog structure. The existing server-component architecture and concurrent dashboard requests were appropriate; no additional client state or dependencies were needed for the redesign.

- The fixed 240px sidebar and unconditional 32px content padding squeezed small viewports. The shell now stacks on mobile, keeps navigation locally scrollable, and constrains desktop reading width.
- The font token referenced itself. It now resolves to the Geist font already loaded by Next.
- The dashboard gave onboarding and workspace activity similar visual weight. It now separates an introductory panel, linked counts, review alerts and campaign rows with actual run status.
- Dashboard requests silently converted failures into empty lists. Partial failures now retain successful data and explicitly mark unavailable counts. The brand list uses the shared error boundary instead of showing a first-use state on failure.
- Page headings duplicated layout rules. Overview, campaigns and brands now share PageHeader.
- Campaign tables hid status and actions beyond the mobile viewport. The same rows and action components now stack on phones, preserving desktop tables and avoiding duplicate interactive controls.
- Navigation lacked current-page semantics and a skip link. Both are now present, alongside visible link focus and decorative icon labels.
- Route transitions had no shared loading or recovery UI. Added reduced-motion-aware loading placeholders and a retry boundary.

## Visual direction

Dark graphite surfaces, restrained violet accents, clearer spacing and typography, thin borders and a quiet radial highlight. Existing English product language and dark-only theme are preserved. No animation library or new assets are required.

## Validation

- ESLint: passed.
- TypeScript (`npx tsc --noEmit`): passed.
- Backend scripted suite: 1007 passed, two dependency deprecation warnings.
- `git diff --check`: passed.
- Browser: dashboard inspected at desktop and 390px width; campaigns and brands inspected at 390px; campaign rows verified after responsive correction. Loading UI was also observed during navigation.
- No real campaign or billed model call was run.

## Limits

This is a targeted refactor of the shared shell and entry pages, not an exhaustive redesign of every nested editor. No production build or measured performance benchmark was run. The partial-failure and retry states were reviewed in code but not exercised by interrupting the running backend. Gains concern layout, maintainability and perceived loading, rather than a claimed reduction in backend latency.

## Second pass — live updates and deliverables

- Live polling now waits four seconds after the previous request batch completes, eliminating overlap on slow responses. Hidden tabs stop scheduling requests and refresh immediately on return; disposal prevents late results from updating an unmounted board.
- The elapsed-time clock runs only while there is active work and pauses in hidden tabs.
- Failed live requests preserve the last known cards and display a retry notice. Initial failures no longer look like an empty board.
- The campaign dialog defers model catalog loading until it opens. Switching from an existing brand to no brand or a new brand now invalidates outstanding knowledge/audience responses; resetting the form does too.
- Deliverable headers wrap on narrow screens, preview selectors expose their pressed state as ordinary keyboard-accessible buttons, copy feedback is announced, and repeated copies restart the feedback timer. Text line length is constrained for reading.

Validation: ESLint and TypeScript passed; all 1007 backend tests passed. Three deterministic polling tests passed (slow request overlap, visibility pause/resume and cleanup, completion while hidden). Run them with Node 24 from the repository root: `node --test frontend/tests/visible-polling.test.mjs`. Live studio rendering was inspected in the browser against existing work; no new campaign or model call was started. Dialog race handling and deliverable controls were code-reviewed, not end-to-end tested under simulated network latency.
