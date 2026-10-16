import {
  SkeletonHeader,
  SkeletonPage,
  SkeletonStats,
  SkeletonTable,
} from "@/components/skeleton";

export default function Loading() {
  return (
    <SkeletonPage label="Loading your workspace…">
      <SkeletonHeader />
      <SkeletonStats count={4} />
      <div className="grid gap-6 xl:grid-cols-2">
        <SkeletonTable rows={4} />
        <SkeletonTable rows={4} />
      </div>
    </SkeletonPage>
  );
}
