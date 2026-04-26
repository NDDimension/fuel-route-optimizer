import { Route } from 'lucide-react';

interface EmptyStateProps {
  onExampleSelect: (start: string, end: string) => void;
}

const EXAMPLES = [
  { label: 'New York → Los Angeles', start: 'New York, NY', end: 'Los Angeles, CA' },
  { label: 'Chicago → Dallas', start: 'Chicago, IL', end: 'Dallas, TX' },
];

export function EmptyState({ onExampleSelect }: EmptyStateProps): JSX.Element {
  return (
    <div className="rounded-2xl border border-dashed border-surface-border bg-surface-card/60 p-6">
      <div className="flex flex-col items-start gap-4">
        <div className="rounded-2xl border border-surface-border bg-surface-panel p-3">
          <Route className="h-8 w-8 text-text-muted" />
        </div>
        <div className="space-y-2">
          <h2 className="font-display text-xl font-semibold text-text-primary">Ready to optimize</h2>
          <p className="max-w-sm text-sm leading-6 text-text-secondary">
            Enter a start and destination to calculate the most fuel-efficient route.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((example) => (
            <button
              key={example.label}
              type="button"
              onClick={() => onExampleSelect(example.start, example.end)}
              className="rounded-full border border-surface-border bg-surface-panel px-3 py-1.5 font-mono text-xs text-text-secondary transition-colors hover:border-accent hover:text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/50"
            >
              {example.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
