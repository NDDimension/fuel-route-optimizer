import { useEffect, useState } from 'react';
import { MapPin } from 'lucide-react';

interface LocationInputProps {
  id: string;
  label: string;
  value: string;
  error?: string;
  flashToken: number;
  onChange: (value: string) => void;
}

export function LocationInput({
  id,
  label,
  value,
  error,
  flashToken,
  onChange,
}: LocationInputProps): JSX.Element {
  const [isFlashing, setIsFlashing] = useState(false);

  useEffect(() => {
    if (flashToken === 0) {
      return;
    }

    setIsFlashing(true);
    const timeoutId = window.setTimeout(() => setIsFlashing(false), 600);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [flashToken]);

  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block font-mono text-xs uppercase tracking-widest text-text-muted">
        {label}
      </label>
      <div
        className={[
          'flex items-center gap-3 rounded-xl border bg-surface-card px-3 py-3 transition-colors duration-150',
          isFlashing ? 'border-accent shadow-[0_0_0_1px_var(--accent)]' : 'border-surface-border',
          error ? 'border-red-700' : 'focus-within:border-accent',
        ].join(' ')}
      >
        <MapPin className="h-4 w-4 shrink-0 text-accent" />
        <input
          id={id}
          autoComplete="off"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="City, State or full address"
          className="w-full bg-transparent font-sans text-sm text-text-primary outline-none placeholder:text-text-muted"
        />
      </div>
      {error ? <p className="text-xs text-red-400">{error}</p> : null}
    </div>
  );
}
