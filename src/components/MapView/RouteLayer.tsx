import { useMemo, useRef } from 'react';
import { Layer, Source } from 'react-map-gl';

function getAccentColor(): string {
  if (typeof document === 'undefined') return '#22D3EE';
  const value = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim();
  return value || '#22D3EE';
}

interface RouteLayerProps {
  data: GeoJSON.Feature<GeoJSON.LineString> | null;
  dimmed: boolean;
}

export function RouteLayer({ data, dimmed }: RouteLayerProps): JSX.Element | null {
  const colorRef = useRef<string | null>(null);
  if (colorRef.current === null) {
    colorRef.current = getAccentColor();
  }
  const glowColor = colorRef.current;

  const glowPaint = useMemo(
    () => ({
      'line-color': glowColor,
      'line-width': 8,
      'line-opacity': dimmed ? 0.06 : 0.15,
      'line-blur': 0.8,
    }),
    [dimmed, glowColor],
  );

  const linePaint = useMemo(
    () => ({
      'line-color': glowColor,
      'line-width': 2.5,
      'line-opacity': dimmed ? 0.4 : 1,
    }),
    [dimmed, glowColor],
  );

  if (!data) {
    return null;
  }

  return (
    <Source id="route-source" type="geojson" data={data}>
      <Layer id="route-glow" type="line" paint={glowPaint} />
      <Layer id="route-line" type="line" paint={linePaint} />
    </Source>
  );
}
