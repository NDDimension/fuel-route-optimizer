import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';

import type { FuelStop, RouteResponse, RouteStatus } from '../../types/route';
import { RouteForm } from '../RouteForm/RouteForm';
import { EmptyState } from '../UI/EmptyState';
import { ErrorBanner } from '../UI/ErrorBanner';
import { FuelStopsList } from './FuelStopsList';
import { SummaryPanel } from './SummaryPanel';

type StopTone = 'cheap' | 'mid' | 'expensive';

interface SidebarProps {
  status: RouteStatus;
  start: string;
  end: string;
  flashTokens: {
    start: number;
    end: number;
  };
  activeStopId: string | null;
  displayedData: RouteResponse | null;
  cheapestStopId: string | null;
  stopTones: Map<string, StopTone>;
  onStartChange: (value: string) => void;
  onEndChange: (value: string) => void;
  onSubmit: () => void;
  onReset: () => void;
  onExampleSelect: (start: string, end: string) => void;
  onStopSelect: (stop: FuelStop) => void;
  registerCard: (stationId: string, element: HTMLButtonElement | null) => void;
}

function LoadingSkeleton(): JSX.Element {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="grid grid-cols-2 gap-3">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="h-28 rounded-xl bg-surface-card" />
        ))}
      </div>
      {Array.from({ length: 3 }).map((_, index) => (
        <div key={index} className="h-40 rounded-xl bg-surface-card" />
      ))}
    </div>
  );
}

export function Sidebar({
  status,
  start,
  end,
  flashTokens,
  activeStopId,
  displayedData,
  cheapestStopId,
  stopTones,
  onStartChange,
  onEndChange,
  onSubmit,
  onReset,
  onExampleSelect,
  onStopSelect,
  registerCard,
}: SidebarProps): JSX.Element {
  const reducedMotion = useReducedMotion();
  const isLoading = status.phase === 'loading';

  return (
    <motion.aside
      initial={reducedMotion ? false : { opacity: 0, y: 16 }}
      animate={reducedMotion ? {} : { opacity: 1, y: 0 }}
      transition={reducedMotion ? undefined : { duration: 0.35, ease: 'easeOut' }}
      className="pointer-events-auto fixed inset-x-0 bottom-0 z-20 flex h-[65vh] flex-col rounded-t-3xl border border-surface-border bg-surface-panel/95 shadow-panel backdrop-blur-xl lg:inset-y-0 lg:left-0 lg:right-auto lg:h-screen lg:w-[420px] lg:rounded-none lg:rounded-r-2xl lg:border-r lg:border-t-0 lg:border-l-0 lg:border-b-0"
    >
      <div className="flex justify-center pt-3 lg:hidden">
        <span className="h-1 w-8 rounded-full bg-surface-border" />
      </div>
      <div className="shrink-0 border-b border-surface-border px-5 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-accent/30 bg-accent/10 font-display text-lg font-bold text-accent">
            R
          </div>
          <div>
            <p className="font-display text-xl font-semibold text-text-primary">RouteOpt</p>
            <p className="font-mono text-xs uppercase tracking-widest text-text-muted">Fuel Command Center</p>
          </div>
        </div>
      </div>
      <div className="shrink-0 space-y-4 border-b border-surface-border px-5 py-5">
        <RouteForm
          start={start}
          end={end}
          isLoading={isLoading}
          flashTokens={flashTokens}
          onStartChange={onStartChange}
          onEndChange={onEndChange}
          onSubmit={onSubmit}
        />
        <AnimatePresence initial={false}>
          {status.phase === 'error' ? <ErrorBanner message={status.message} onDismiss={onReset} /> : null}
        </AnimatePresence>
      </div>
      <div className="relative min-h-0 flex-1">
        <motion.div
          initial={reducedMotion ? false : { opacity: 0, y: 16 }}
          animate={reducedMotion ? {} : { opacity: 1, y: 0 }}
          transition={reducedMotion ? undefined : { duration: 0.35, ease: 'easeOut' }}
          className="sidebar-scroll h-full overflow-y-auto px-5 py-5"
        >
          <div className="space-y-4 pb-16">
            {status.phase === 'idle' && !displayedData ? <EmptyState onExampleSelect={onExampleSelect} /> : null}
            {status.phase === 'loading' ? <LoadingSkeleton /> : null}
            {displayedData && status.phase !== 'loading' ? <SummaryPanel data={displayedData} /> : null}
            {displayedData && status.phase !== 'loading' ? (
              <FuelStopsList
                stops={displayedData.fuel_stops}
                activeStopId={activeStopId}
                cheapestStopId={cheapestStopId}
                stopTones={stopTones}
                onStopSelect={onStopSelect}
                registerCard={registerCard}
              />
            ) : null}
          </div>
        </motion.div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-gradient-to-b from-transparent to-surface-panel" />
      </div>
    </motion.aside>
  );
}
