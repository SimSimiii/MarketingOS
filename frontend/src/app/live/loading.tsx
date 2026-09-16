import { Skeleton, SkeletonHeader, SkeletonPage } from "@/components/skeleton";

export default function Loading() {
  return (
    <SkeletonPage label="Loading what is running…">
      <SkeletonHeader />
      <Skeleton className="h-8 w-32 rounded-lg" />
      <div className="space-y-4">
        {[0, 1, 2].map((item) => (
          <Skeleton key={item} className="h-24 rounded-xl" />
        ))}
      </div>
    </SkeletonPage>
  );
}
