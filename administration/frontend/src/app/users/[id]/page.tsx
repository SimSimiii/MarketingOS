import { UserDetailView } from "./user-detail-view";

/**
 * One exported page for every account.
 *
 * A static export has to know its routes at build time, and account ids are
 * not knowable then. So exactly one placeholder page is emitted and the
 * CloudFront function in the SAM template rewrites `/users/<uuid>/` onto it at
 * the edge. The browser's URL still carries the real id, which is where the
 * client component below reads it from.
 */
export function generateStaticParams() {
  return [{ id: "_" }];
}

export default function UserPage() {
  return <UserDetailView />;
}
