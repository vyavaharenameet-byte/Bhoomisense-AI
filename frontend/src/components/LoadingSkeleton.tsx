/** Shimmer skeleton displayed while the backend computes a prediction. */
export default function LoadingSkeleton() {
  return (
    <div className="space-y-5 animate-pulse">
      <div className="grid sm:grid-cols-3 gap-5">
        {[0, 1, 2].map((i) => (
          <div key={i} className="glass rounded-2xl p-6 h-56">
            <div className="skeleton animate-shimmer h-4 w-24 rounded mb-6" />
            <div className="skeleton animate-shimmer h-28 w-28 rounded-full mx-auto" />
          </div>
        ))}
      </div>
      <div className="glass rounded-2xl p-6 h-72">
        <div className="skeleton animate-shimmer h-4 w-40 rounded mb-4" />
        <div className="skeleton animate-shimmer h-52 w-full rounded-xl" />
      </div>
    </div>
  );
}
