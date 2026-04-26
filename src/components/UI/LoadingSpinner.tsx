export function LoadingSpinner(): JSX.Element {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-surface border-t-transparent"
    />
  );
}
