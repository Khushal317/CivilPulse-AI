export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div aria-live="polite" className="loading-indicator" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function Skeleton({ height = "1rem", width = "100%" }: { height?: string; width?: string }) {
  return (
    <span
      aria-hidden="true"
      className="skeleton"
      style={{ height, width }}
    />
  );
}
