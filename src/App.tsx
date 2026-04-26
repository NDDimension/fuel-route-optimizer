import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { FuelStopMarker } from './components/MapView/FuelStopMarker';
import { MapView } from './components/MapView/MapView';
import { RouteLayer } from './components/MapView/RouteLayer';
import { Sidebar } from './components/Sidebar/Sidebar';
import { useMapController } from './hooks/useMapController';
import { useRouteQuery } from './hooks/useRouteQuery';
import type { FuelStop, RouteResponse } from './types/route';
import { classifyStops } from './utils/routeUtils';

export default function App(): JSX.Element {
  const { status, submit, reset } = useRouteQuery();
  const { mapRef, routeFeatureRef, updateRoute, clearRoute, flyToStop } = useMapController();
  const [formState, setFormState] = useState({ start: '', end: '' });
  const [flashTokens, setFlashTokens] = useState({ start: 0, end: 0 });
  const [activeStopId, setActiveStopId] = useState<string | null>(null);
  const lastSuccessfulRef = useRef<RouteResponse | null>(null);
  const cardRefs = useRef(new Map<string, HTMLButtonElement>());

  const displayedData = status.phase === 'success' ? status.data : lastSuccessfulRef.current;

  const stopTones = useMemo(
    () => classifyStops(displayedData?.fuel_stops ?? []),
    [displayedData?.fuel_stops],
  );

  const cheapestStopId = useMemo(() => {
    const stops = displayedData?.fuel_stops ?? [];
    if (stops.length === 0) {
      return null;
    }

    return [...stops].sort((a, b) => a.price_per_gallon - b.price_per_gallon)[0]?.station_id ?? null;
  }, [displayedData?.fuel_stops]);

  useEffect(() => {
    if (status.phase === 'success') {
      lastSuccessfulRef.current = status.data;
      updateRoute(status.data);
      setActiveStopId(null);
    }
  }, [status, updateRoute]);

  const handleMapLoad = useCallback(() => {
    if (lastSuccessfulRef.current) {
      updateRoute(lastSuccessfulRef.current);
    }
  }, [updateRoute]);

  const handleSubmit = useCallback(() => {
    void submit({
      start: formState.start.trim(),
      end: formState.end.trim(),
    });
  }, [formState.end, formState.start, submit]);

  const handleReset = useCallback(() => {
    setActiveStopId(null);
    reset();
  }, [reset]);

  const handleExampleSelect = useCallback((start: string, end: string) => {
    setFormState({ start, end });
    setFlashTokens((current) => ({ start: current.start + 1, end: current.end + 1 }));
  }, []);

  const registerCard = useCallback((stationId: string, element: HTMLButtonElement | null) => {
    if (element) {
      cardRefs.current.set(stationId, element);
      return;
    }

    cardRefs.current.delete(stationId);
  }, []);

  const focusStop = useCallback(
    (stop: FuelStop, shouldScroll: boolean) => {
      setActiveStopId(stop.station_id);
      flyToStop(stop);

      if (shouldScroll) {
        cardRefs.current.get(stop.station_id)?.scrollIntoView({
          block: 'nearest',
          behavior: 'smooth',
        });
      }
    },
    [flyToStop],
  );

  const handleCardSelect = useCallback((stop: FuelStop) => {
    focusStop(stop, false);
  }, [focusStop]);

  const handleMarkerSelect = useCallback((stop: FuelStop) => {
    focusStop(stop, true);
  }, [focusStop]);

  const handleMarkerClose = useCallback((stationId: string) => {
    setActiveStopId((current) => (current === stationId ? null : current));
  }, []);

  const handleStartChange = useCallback((value: string) => {
    setFormState((current) => ({ ...current, start: value }));
  }, []);

  const handleEndChange = useCallback((value: string) => {
    setFormState((current) => ({ ...current, end: value }));
  }, []);

  const displayedStops = displayedData?.fuel_stops ?? [];
  const isRouteDimmed = status.phase === 'loading' && lastSuccessfulRef.current !== null;

  return (
    <div className="relative h-screen overflow-hidden bg-surface text-text-primary">
      <MapView ref={mapRef} onMapLoad={handleMapLoad}>
        <RouteLayer data={routeFeatureRef.current} dimmed={isRouteDimmed} />
        {displayedStops.map((stop) => (
          <FuelStopMarker
            key={stop.station_id}
            stop={stop}
            tone={stopTones.get(stop.station_id) ?? 'mid'}
            isActive={activeStopId === stop.station_id}
            isCheapest={cheapestStopId === stop.station_id}
            onSelect={handleMarkerSelect}
            onClose={handleMarkerClose}
          />
        ))}
      </MapView>

      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_55%,rgba(10,10,15,0.72)_100%)]" />

      <Sidebar
        status={status}
        start={formState.start}
        end={formState.end}
        flashTokens={flashTokens}
        activeStopId={activeStopId}
        displayedData={displayedData}
        cheapestStopId={cheapestStopId}
        stopTones={stopTones}
        onStartChange={handleStartChange}
        onEndChange={handleEndChange}
        onSubmit={handleSubmit}
        onReset={handleReset}
        onExampleSelect={handleExampleSelect}
        onStopSelect={handleCardSelect}
        registerCard={registerCard}
      />
    </div>
  );
}
