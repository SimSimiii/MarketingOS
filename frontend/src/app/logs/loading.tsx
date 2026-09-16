import { SkeletonHeader, SkeletonPage, SkeletonTable } from "@/components/skeleton";

export default function Loading() {
  return (
    <SkeletonPage label="Loading recent activity…">
      <SkeletonHeader />
      <SkeletonTable rows={8} />
    </SkeletonPage>
  );
}
