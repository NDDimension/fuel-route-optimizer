import { motion, useReducedMotion } from 'framer-motion';
import { AlertTriangle, X } from 'lucide-react';

interface ErrorBannerProps {
  message: string;
  onDismiss: () => void;
}

function normalizeError(message: string): string {
  if (message.startsWith('Could not geocode')) {
    return "We couldn't find that location. Try adding a state abbreviation.";
  }

  if (message.startsWith('No fuel stations reachable')) {
    return 'No fuel stations found along this route. Try a different path.';
  }

  if (message.includes('timed out')) {
    return 'Connection timed out. Check your network and try again.';
  }

  if (message.includes('Route optimizer services are not available')) {
    return 'The route optimizer is starting up. Please wait 30 seconds and try again.';
  }

  if (message.includes('Unable to connect')) {
    return 'Connection timed out. Check your network and try again.';
  }

  return message;
}

export function ErrorBanner({ message, onDismiss }: ErrorBannerProps): JSX.Element {
  const reducedMotion = useReducedMotion();

  return (
    <motion.div
      role="alert"
      initial={reducedMotion ? false : { height: 0, opacity: 0 }}
      animate={reducedMotion ? {} : { height: 'auto', opacity: 1 }}
      exit={reducedMotion ? {} : { height: 0, opacity: 0 }}
      transition={reducedMotion ? undefined : { duration: 0.2, ease: 'easeOut' }}
      className="overflow-hidden"
    >
      <div className="rounded-xl border border-red-800 bg-red-950 p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
          <div className="min-w-0 flex-1">
            <p className="text-sm text-red-300">{normalizeError(message)}</p>
          </div>
          <button
            type="button"
            onClick={onDismiss}
            className="inline-flex items-center gap-1 text-xs font-medium text-red-300 transition-colors hover:text-red-100 focus:outline-none focus:ring-2 focus:ring-red-500/50"
          >
            <X className="h-3.5 w-3.5" />
            Dismiss
          </button>
        </div>
      </div>
    </motion.div>
  );
}
