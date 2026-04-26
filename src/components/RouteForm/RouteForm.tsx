import { useCallback, useState, type FormEvent } from 'react';
import { Navigation } from 'lucide-react';

import { LoadingSpinner } from '../UI/LoadingSpinner';
import { LocationInput } from './LocationInput';

interface RouteFormProps {
  start: string;
  end: string;
  isLoading: boolean;
  flashTokens: {
    start: number;
    end: number;
  };
  onStartChange: (value: string) => void;
  onEndChange: (value: string) => void;
  onSubmit: () => void;
}

export function RouteForm({
  start,
  end,
  isLoading,
  flashTokens,
  onStartChange,
  onEndChange,
  onSubmit,
}: RouteFormProps): JSX.Element {
  const [errors, setErrors] = useState<{ start?: string; end?: string }>({});

  const handleSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      const nextErrors = {
        start: start.trim() ? undefined : 'Start location is required.',
        end: end.trim() ? undefined : 'Destination is required.',
      };

      setErrors(nextErrors);

      if (nextErrors.start || nextErrors.end) {
        return;
      }

      onSubmit();
    },
    [end, onSubmit, start],
  );

  const isDisabled = start.trim().length === 0 || end.trim().length === 0;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <LocationInput
        id="route-start"
        label="Start"
        value={start}
        error={errors.start}
        flashToken={flashTokens.start}
        onChange={(value) => {
          if (errors.start) {
            setErrors((current) => ({ ...current, start: undefined }));
          }
          onStartChange(value);
        }}
      />
      <LocationInput
        id="route-end"
        label="Destination"
        value={end}
        error={errors.end}
        flashToken={flashTokens.end}
        onChange={(value) => {
          if (errors.end) {
            setErrors((current) => ({ ...current, end: undefined }));
          }
          onEndChange(value);
        }}
      />
      <button
        type="submit"
        aria-busy={isLoading}
        disabled={isDisabled}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-accent px-4 py-3 font-sans text-sm font-semibold tracking-wide text-surface transition-transform duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:bg-surface-hover disabled:text-text-muted"
      >
        {isLoading ? <LoadingSpinner /> : <Navigation className="h-4 w-4" />}
        <span>{isLoading ? 'Calculating…' : 'Optimize Route'}</span>
      </button>
    </form>
  );
}
