import { Skeleton, SkeletonHeader, SkeletonPage } from "@/components/skeleton";

export default function Loading() {
  return (
    <SkeletonPage label="Loading your settings…">
      <SkeletonHeader />
      <Skeleton className="h-96 rounded-xl" />
      <Skeleton className="h-48 rounded-xl" />
    </SkeletonPage>
  );
}
