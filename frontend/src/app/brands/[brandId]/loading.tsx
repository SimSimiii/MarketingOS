import { Skeleton, SkeletonPage } from "@/components/skeleton";

export default function Loading() {
  return (
    <SkeletonPage label="Loading this brand workspace…">
      {/* The hero, the six-tab nav and the section below it - the shape the
          brand layout always renders, whichever child route is loading. */}
      <Skeleton className="h-40 rounded-2xl" />
      <Skeleton className="h-20 rounded-2xl" />
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {[0, 1, 2, 3].map((item) => (
          <Skeleton key={item} className="h-[7.5rem] rounded-xl" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-64 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    </SkeletonPage>
  );
}
