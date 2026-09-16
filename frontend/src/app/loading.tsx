import {
  Skeleton,
  SkeletonHeader,
  SkeletonPage,
  SkeletonStats,
  SkeletonTable,
} from "@/components/skeleton";

export default function Loading() {
  return (
    <SkeletonPage label="Loading your workspace…">
      <SkeletonHeader />
      <Skeleton className="h-48 rounded-2xl" />
      <SkeletonStats />
      <SkeletonTable rows={4} />
    </SkeletonPage>
  );
}
