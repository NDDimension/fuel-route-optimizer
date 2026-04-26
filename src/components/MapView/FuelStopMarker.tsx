import { memo, useCallback } from 'react';
import { Fuel as FuelIcon } from 'lucide-react';
import { Marker, Popup } from 'react-map-gl';

import type { FuelStop } from '../../types/route';
import { formatCost } from '../../utils/routeUtils';

type StopTone = 'cheap' | 'mid' | 'expensive';

interface FuelStopMarkerProps {
  stop: FuelStop;
  tone: StopTone;
  isActive: boolean;
  isCheapest: boolean;
  onSelect: (stop: FuelStop) => void;
  onClose: (stationId: string) => void;
}

const toneClasses: Record<StopTone, string> = {
  cheap: 'bg-fuel-cheap',
  mid: 'bg-fuel-mid',
  expensive: 'bg-fuel-expensive',
};

function FuelStopMarkerComponent({
  stop,
  tone,
  isActive,
  isCheapest,
  onSelect,
  onClose,
}: FuelStopMarkerProps): JSX.Element {
  const stationId = stop.station_id;

  const handleSelect = useCallback(() => {
    onSelect(stop);
  }, [onSelect, stationId]);

  const handleClose = useCallback(() => {
    onClose(stationId);
  }, [onClose, stationId]);

  return (
    <Marker longitude={stop.lon} latitude={stop.lat} anchor="bottom">
      <>
        <button
          type="button"
          onClick={handleSelect}
          aria-label={`Fuel stop: ${stop.name}, $${stop.price_per_gallon.toFixed(3)} per gallon`}
          className="group flex flex-col items-center focus:outline-none"
        >
          <span
            className={[
              'flex h-6 w-6 items-center justify-center rounded-full lg:h-8 lg:w-8',
              toneClasses[tone],
              'shadow-lg transition-transform duration-150 [transition-timing-function:cubic-bezier(0.34,1.56,0.64,1)] group-hover:scale-[1.2] motion-reduce:transition-none motion-reduce:group-hover:scale-100',
            ].join(' ')}
          >
            <FuelIcon className="h-3.5 w-3.5 text-white lg:h-[14px] lg:w-[14px]" />
          </span>
          <span className="mt-1 rounded-full bg-surface-panel/90 px-2 py-0.5 font-mono text-[10px] text-text-primary lg:text-[11px]">
            ${stop.price_per_gallon.toFixed(2)}
          </span>
        </button>
        {isActive ? (
          <Popup
            longitude={stop.lon}
            latitude={stop.lat}
            anchor="top"
            closeButton={false}
            offset={20}
            onClose={handleClose}
          >
            <div className="min-w-[220px] rounded-2xl border border-surface-border bg-surface-card p-4 shadow-panel">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-display text-lg font-semibold text-text-primary">{stop.name}</p>
                  <p className="mt-1 text-sm text-text-secondary">
                    {stop.city}, {stop.state}
                  </p>
                </div>
                {isCheapest ? (
                  <span className="rounded-full bg-fuel-cheap/15 px-2 py-0.5 font-mono text-[10px] text-fuel-cheap">
                    CHEAPEST
                  </span>
                ) : null}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 font-mono text-xs text-text-secondary">
                <div>
                  <p>Gallons</p>
                  <p className="mt-1 text-sm text-text-primary">{stop.gallons_added.toFixed(1)} gal</p>
                </div>
                <div>
                  <p>Total Cost</p>
                  <p className="mt-1 text-sm text-text-primary">{formatCost(stop.stop_cost)}</p>
                </div>
                <div>
                  <p>Price / gal</p>
                  <p className="mt-1 text-sm text-text-primary">${stop.price_per_gallon.toFixed(3)}</p>
                </div>
                <div>
                  <p>Off Route</p>
                  <p className="mt-1 text-sm text-text-primary">{stop.off_route_miles.toFixed(1)} mi</p>
                </div>
              </div>
            </div>
          </Popup>
        ) : null}
      </>
    </Marker>
  );
}

export const FuelStopMarker = memo(FuelStopMarkerComponent);
