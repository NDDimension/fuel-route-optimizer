import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { useEffect, useState } from 'react';

import type { RouteResponse } from '../../types/route';
import { formatCost, formatMiles } from '../../utils/routeUtils';

interface SummaryPanelProps {
  data: RouteResponse | null;
}

interface StatValueProps {
  value: number;
  formatter: (value: number) => string;
}

function StatValue({ value, formatter }: StatValueProps): JSX.Element {
  const reducedMotion = useReducedMotion();
  const [displayValue, setDisplayValue] = useState(reducedMotion ? value : 0);

  useEffect(() => {
    if (reducedMotion) {
      setDisplayValue(value);
      return;
    }

    let frame = 0;
    let startTime = 0;
    const duration = 800;

    const tick = (timestamp: number) => {
      if (startTime === 0) {
        startTime = timestamp;
      }

      const progress = Math.min((timestamp - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(value * eased);

      if (progress < 1) {
        frame = window.requestAnimationFrame(tick);
      }
    };

    frame = window.requestAnimationFrame(tick);

    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, [reducedMotion, value]);

  return <span>{formatter(displayValue)}</span>;
}

export function SummaryPanel({ data }: SummaryPanelProps): JSX.Element {
  const reducedMotion = useReducedMotion();

  return (
    <AnimatePresence initial={false}>
      {data ? (
        <motion.div
          initial={reducedMotion ? false : { height: 0, opacity: 0 }}
          animate={reducedMotion ? {} : { height: 'auto', opacity: 1 }}
          exit={reducedMotion ? {} : { height: 0, opacity: 0 }}
          transition={reducedMotion ? undefined : { duration: 0.35, ease: 'easeOut' }}
          className="overflow-hidden"
        >
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Total Cost', node: <StatValue value={data.total_fuel_cost} formatter={formatCost} /> },
              { label: 'Total Miles', node: <StatValue value={data.total_miles} formatter={formatMiles} /> },
              {
                label: 'Total Gallons',
                node: <StatValue value={data.total_gallons} formatter={(value) => `${value.toFixed(1)} gal`} />,
              },
              {
                label: 'Fuel Stops',
                node: <StatValue value={data.fuel_stops.length} formatter={(value) => `${Math.round(value)} stops`} />,
              },
            ].map((stat) => (
              <div key={stat.label} className="rounded-xl bg-surface-card p-4">
                <p className="font-mono text-xs uppercase tracking-widest text-text-muted">{stat.label}</p>
                <p className="mt-3 font-display text-2xl font-bold text-text-primary">{stat.node}</p>
              </div>
            ))}
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
