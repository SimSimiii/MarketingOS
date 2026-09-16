import { Skeleton, SkeletonHeader, SkeletonPage, SkeletonStats } from "@/components/skeleton";

export default function Loading() {
  return (
    <SkeletonPage label="Loading your brand workspaces…">
      <SkeletonHeader />
      <SkeletonStats />
      <Skeleton className="h-14 rounded-xl" />
      <div className="grid gap-4 lg:grid-cols-2">
        {[0, 1, 2, 3].map((item) => (
          <Skeleton key={item} className="h-64 rounded-xl" />
        ))}
      </div>
    </SkeletonPage>
  );
}
