import type { RouteRequest, RouteResponse } from '../types/route';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

interface ErrorResponse {
  error?: string;
}

export async function fetchRoute(
  req: RouteRequest,
  signal?: AbortSignal,
): Promise<RouteResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/route/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req),
      signal,
    });

    if (!response.ok) {
      const errorBody = (await response.json().catch(() => ({}))) as ErrorResponse;
      throw new Error(errorBody.error ?? 'Unable to optimize this route right now.');
    }

    return (await response.json()) as RouteResponse;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error;
    }

    if (error instanceof Error) {
      if (error.message === 'Failed to fetch') {
        throw new Error('Unable to connect to the route optimizer. Check your network and try again.');
      }

      throw error;
    }

    throw new Error('Unable to connect to the route optimizer. Check your network and try again.');
  }
}
