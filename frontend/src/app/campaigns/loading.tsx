import { SkeletonHeader, SkeletonPage, SkeletonTable } from "@/components/skeleton";

export default function Loading() {
  return (
    <SkeletonPage label="Loading your campaigns…">
      <SkeletonHeader />
      <SkeletonTable rows={6} />
    </SkeletonPage>
  );
}
