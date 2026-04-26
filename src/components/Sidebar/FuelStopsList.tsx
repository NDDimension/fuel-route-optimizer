import { motion, useReducedMotion } from 'framer-motion';

import type { FuelStop } from '../../types/route';
import { FuelStopCard } from './FuelStopCard';

type StopTone = 'cheap' | 'mid' | 'expensive';

interface FuelStopsListProps {
  stops: FuelStop[];
  activeStopId: string | null;
  cheapestStopId: string | null;
  stopTones: Map<string, StopTone>;
  onStopSelect: (stop: FuelStop) => void;
  registerCard: (stationId: string, element: HTMLButtonElement | null) => void;
}

export function FuelStopsList({
  stops,
  activeStopId,
  cheapestStopId,
  stopTones,
  onStopSelect,
  registerCard,
}: FuelStopsListProps): JSX.Element {
  const reducedMotion = useReducedMotion();

  if (stops.length === 0) {
    return (
      <div className="rounded-2xl border border-surface-border bg-surface-card p-6">
        <p className="font-display text-lg font-semibold text-text-primary">No fuel stops needed</p>
        <p className="mt-2 text-sm text-text-secondary">
          This route is short enough that the optimizer did not need to schedule any fueling stops.
        </p>
      </div>
    );
  }

  return (
    <motion.div
      variants={
        reducedMotion
          ? undefined
          : {
              animate: {
                transition: {
                  staggerChildren: 0.06,
                },
              },
            }
      }
      initial={reducedMotion ? false : 'initial'}
      animate={reducedMotion ? undefined : 'animate'}
      className="space-y-3"
    >
      {stops.map((stop, index) => (
        <motion.div
          key={stop.station_id}
          variants={
            reducedMotion
              ? undefined
              : {
                  initial: { opacity: 0, y: 20 },
                  animate: { opacity: 1, y: 0 },
                }
          }
          transition={reducedMotion ? undefined : { duration: 0.3, ease: 'easeOut' }}
        >
          <FuelStopCard
            index={index}
            stop={stop}
            tone={stopTones.get(stop.station_id) ?? 'mid'}
            isActive={activeStopId === stop.station_id}
            isCheapest={cheapestStopId === stop.station_id}
            onSelect={onStopSelect}
            registerCard={registerCard}
          />
        </motion.div>
      ))}
    </motion.div>
  );
}
