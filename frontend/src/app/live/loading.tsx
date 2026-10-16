import { Skeleton, SkeletonHeader, SkeletonPage } from "@/components/skeleton";

export default function Loading() {
  return (
    <SkeletonPage label="Loading what is running…">
      <SkeletonHeader />
      <Skeleton className="h-14 rounded-2xl" />
      <div className="space-y-4">
        {[0, 1, 2].map((item) => (
          <Skeleton key={item} className="h-24 rounded-2xl" />
        ))}
      </div>
    </SkeletonPage>
  );
}
