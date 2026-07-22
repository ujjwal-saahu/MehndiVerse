import { Skeleton } from "@/components/feedback/skeleton";

/** Next.js route-segment loading boundary — shown automatically while a
 * page in this route group is fetching data server-side. */
export default function Loading() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6" aria-busy="true">
      <Skeleton className="h-8 w-1/2" aria-label="Loading page" />
      <div className="mt-6 flex flex-col gap-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  );
}
