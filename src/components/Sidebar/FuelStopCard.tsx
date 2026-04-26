import { memo, useCallback } from 'react';

import type { FuelStop } from '../../types/route';
import { formatCost } from '../../utils/routeUtils';

type StopTone = 'cheap' | 'mid' | 'expensive';

interface FuelStopCardProps {
  index: number;
  stop: FuelStop;
  tone: StopTone;
  isActive: boolean;
  isCheapest: boolean;
  onSelect: (stop: FuelStop) => void;
  registerCard: (stationId: string, element: HTMLButtonElement | null) => void;
}

const dotToneClasses: Record<StopTone, string> = {
  cheap: 'bg-fuel-cheap',
  mid: 'bg-fuel-mid',
  expensive: 'bg-fuel-expensive',
};

function FuelStopCardComponent({
  index,
  stop,
  tone,
  isActive,
  isCheapest,
  onSelect,
  registerCard,
}: FuelStopCardProps): JSX.Element {
  const handleClick = useCallback(() => {
    onSelect(stop);
  }, [onSelect, stop]);

  const handleRef = useCallback(
    (element: HTMLButtonElement | null) => {
      registerCard(stop.station_id, element);
    },
    [registerCard, stop.station_id],
  );

  return (
    <button
      ref={handleRef}
      type="button"
      onClick={handleClick}
      className={[
        'w-full rounded-xl border border-surface-border bg-surface-card p-4 text-left transition-colors duration-150 hover:bg-surface-hover focus:outline-none focus:ring-2 focus:ring-accent/50',
        isActive ? 'border-l-2 border-l-accent' : '',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <span className={['h-2.5 w-2.5 rounded-full', dotToneClasses[tone]].join(' ')} />
            <p className="truncate font-sans text-sm font-medium text-text-primary">{stop.name}</p>
          </div>
          <p className="mt-2 text-sm text-text-secondary">
            {stop.city}, {stop.state}
          </p>
          <p className="mt-1 font-mono text-xs text-text-muted">
            Mile {stop.route_mile.toFixed(1)} · {stop.off_route_miles.toFixed(1)} mi off route
          </p>
        </div>
        <span className="rounded-full bg-surface-hover px-2.5 py-1 font-mono text-xs text-text-muted">
          #{index + 1}
        </span>
      </div>
      <div className="my-4 border-t border-surface-border" />
      <div className="grid grid-cols-3 gap-3">
        <div>
          <p className="font-sans text-[11px] uppercase tracking-wide text-text-muted">Price</p>
          <p className="mt-1 font-mono text-sm text-text-primary">${stop.price_per_gallon.toFixed(3)} / gal</p>
        </div>
        <div>
          <p className="font-sans text-[11px] uppercase tracking-wide text-text-muted">Gallons</p>
          <p className="mt-1 font-mono text-sm text-text-primary">{stop.gallons_added.toFixed(1)} gal</p>
        </div>
        <div>
          <p className="font-sans text-[11px] uppercase tracking-wide text-text-muted">Cost</p>
          <p className="mt-1 font-mono text-sm text-text-primary">{formatCost(stop.stop_cost)}</p>
        </div>
      </div>
      {isCheapest ? (
        <span className="mt-4 inline-flex rounded-full bg-fuel-cheap/15 px-2 py-0.5 font-mono text-xs text-fuel-cheap">
          CHEAPEST STOP
        </span>
      ) : null}
    </button>
  );
}

export const FuelStopCard = memo(FuelStopCardComponent);
