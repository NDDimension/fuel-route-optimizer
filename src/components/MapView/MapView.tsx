import { forwardRef } from 'react';
import Map, { NavigationControl, type MapProps, type MapRef } from 'react-map-gl';

const initialViewState: NonNullable<MapProps['initialViewState']> = {
  longitude: -98.5795,
  latitude: 39.8283,
  zoom: 3.5,
};

interface MapViewProps {
  onMapLoad: () => void;
  children?: React.ReactNode;
}

export const MapView = forwardRef<MapRef, MapViewProps>(function MapView(
  { onMapLoad, children },
  ref,
): JSX.Element {
  return (
    <div className="relative h-screen w-full bg-surface" role="img" aria-label="Route map showing fuel stops">
      <Map
        ref={ref}
        initialViewState={initialViewState}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
        reuseMaps
        onLoad={onMapLoad}
        style={{ width: '100%', height: '100%' }}
      >
        <NavigationControl position="top-right" showCompass={false} />
        {children}
      </Map>
    </div>
  );
});
