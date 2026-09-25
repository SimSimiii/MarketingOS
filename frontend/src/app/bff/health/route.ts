/**
 * Liveness for whatever is fronting this app.
 *
 * Deliberately shallow: it answers "is the Next server up", not "is the API
 * reachable". A health check that fails because a dependency is down turns one
 * outage into two - the container gets replaced, cold-starts, and fails the
 * same check again while the actual problem is somewhere else entirely.
 *
 * The Lambda Web Adapter polls this before it forwards the first request; see
 * AWS_LWA_READINESS_CHECK_PATH in the Dockerfile.
 */
export const dynamic = "force-dynamic";

export function GET() {
  return Response.json({ status: "ok" });
}
