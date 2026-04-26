import { useCallback, useRef, type MutableRefObject, type RefObject } from 'react';
import type { MapRef } from 'react-map-gl';

import type { FuelStop, RouteResponse } from '../types/route';
import { routeBounds, toGeoJSON } from '../utils/routeUtils';

const EMPTY_ROUTE = toGeoJSON([]);

function getMapPadding(): { top: number; bottom: number; left: number; right: number } {
  if (window.innerWidth < 1024) {
    return {
      top: 60,
      bottom: Math.round(window.innerHeight * 0.4),
      left: 40,
      right: 40,
    };
  }

  return {
    top: 80,
    bottom: 80,
    left: 80,
    right: 500,
  };
}

interface UseMapControllerReturn {
  mapRef: RefObject<MapRef>;
  routeFeatureRef: MutableRefObject<GeoJSON.Feature<GeoJSON.LineString> | null>;
  updateRoute: (data: RouteResponse) => void;
  clearRoute: () => void;
  flyToStop: (stop: FuelStop) => void;
}

export function useMapController(): UseMapControllerReturn {
  const mapRef = useRef<MapRef>(null);
  const routeFeatureRef = useRef<GeoJSON.Feature<GeoJSON.LineString> | null>(null);

  const updateRoute = useCallback((data: RouteResponse) => {
    const feature = toGeoJSON(data.route);
    routeFeatureRef.current = feature;

    const map = mapRef.current?.getMap();

    if (!map) {
      return;
    }

    const source = map.getSource('route-source');

    if (source && 'setData' in source) {
      source.setData(feature);
    }

    const bounds = routeBounds(data.route);
    map.fitBounds(bounds, {
      padding: getMapPadding(),
      duration: 900,
    });
  }, []);

  const clearRoute = useCallback(() => {
    routeFeatureRef.current = null;

    const map = mapRef.current?.getMap();
    const source = map?.getSource('route-source');

    if (source && 'setData' in source) {
      source.setData(EMPTY_ROUTE);
    }
  }, []);

  const flyToStop = useCallback((stop: FuelStop) => {
    mapRef.current?.flyTo({
      center: [stop.lon, stop.lat],
      zoom: 12,
      duration: 800,
      essential: true,
    });
  }, []);

  return {
    mapRef,
    routeFeatureRef,
    updateRoute,
    clearRoute,
    flyToStop,
  };
}
