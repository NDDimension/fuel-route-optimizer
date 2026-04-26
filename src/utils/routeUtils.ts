import type { Coordinate, FuelStop } from '../types/route';

export function toGeoJSON(coords: Coordinate[]): GeoJSON.Feature<GeoJSON.LineString> {
  return {
    type: 'Feature',
    properties: {},
    geometry: {
      type: 'LineString',
      coordinates: coords.map(({ lon, lat }) => [lon, lat]),
    },
  };
}

export function classifyStops(stops: FuelStop[]): Map<string, 'cheap' | 'mid' | 'expensive'> {
  const sorted = [...stops].sort((a, b) => a.price_per_gallon - b.price_per_gallon);
  const classifications = new Map<string, 'cheap' | 'mid' | 'expensive'>();

  if (sorted.length === 0) {
    return classifications;
  }

  const cheapCutoff = Math.ceil(sorted.length / 3);
  const midCutoff = Math.ceil((sorted.length * 2) / 3);

  sorted.forEach((stop, index) => {
    const tier = index < cheapCutoff ? 'cheap' : index < midCutoff ? 'mid' : 'expensive';
    classifications.set(stop.station_id, tier);
  });

  return classifications;
}

export function routeBounds(coords: Coordinate[]): [[number, number], [number, number]] {
  if (coords.length === 0) {
    return [
      [-98.5795, 39.8283],
      [-98.5795, 39.8283],
    ];
  }

  const [first, ...rest] = coords;
  let minLon = first.lon;
  let maxLon = first.lon;
  let minLat = first.lat;
  let maxLat = first.lat;

  rest.forEach(({ lon, lat }) => {
    minLon = Math.min(minLon, lon);
    maxLon = Math.max(maxLon, lon);
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
  });

  return [
    [minLon, minLat],
    [maxLon, maxLat],
  ];
}

export function formatCost(usd: number): string {
  return usd.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatMiles(miles: number): string {
  return `${miles.toFixed(1)} mi`;
}

export function formatDuration(hours: number): string {
  const wholeHours = Math.floor(hours);
  const minutes = Math.round((hours - wholeHours) * 60);

  if (wholeHours === 0) {
    return `${minutes}m`;
  }

  if (minutes === 0) {
    return `${wholeHours}h`;
  }

  return `${wholeHours}h ${minutes}m`;
}
