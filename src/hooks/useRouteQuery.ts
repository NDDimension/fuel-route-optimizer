import { useCallback, useEffect, useReducer, useRef } from 'react';

import { fetchRoute } from '../api/routeApi';
import type { RouteRequest, RouteResponse, RouteStatus } from '../types/route';

type RouteAction =
  | { type: 'loading' }
  | { type: 'success'; data: RouteResponse }
  | { type: 'error'; message: string }
  | { type: 'reset' };

interface UseRouteQueryReturn {
  status: RouteStatus;
  submit: (req: RouteRequest) => Promise<void>;
  reset: () => void;
}

function reducer(_state: RouteStatus, action: RouteAction): RouteStatus {
  switch (action.type) {
    case 'loading':
      return { phase: 'loading' };
    case 'success':
      return { phase: 'success', data: action.data };
    case 'error':
      return { phase: 'error', message: action.message };
    case 'reset':
      return { phase: 'idle' };
    default:
      return { phase: 'idle' };
  }
}

export function useRouteQuery(): UseRouteQueryReturn {
  const [status, dispatch] = useReducer(reducer, { phase: 'idle' } satisfies RouteStatus);
  const abortControllerRef = useRef<AbortController | null>(null);

  const submit = useCallback(async (req: RouteRequest) => {
    abortControllerRef.current?.abort();

    const controller = new AbortController();
    abortControllerRef.current = controller;
    dispatch({ type: 'loading' });

    try {
      const data = await fetchRoute(req, controller.signal);

      if (abortControllerRef.current === controller) {
        dispatch({ type: 'success', data });
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }

      const message = error instanceof Error ? error.message : 'Unable to optimize this route.';

      if (abortControllerRef.current === controller) {
        dispatch({ type: 'error', message });
      }
    }
  }, []);

  const reset = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    dispatch({ type: 'reset' });
  }, []);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  return { status, submit, reset };
}
