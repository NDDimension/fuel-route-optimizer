export interface RouteRequest {
  start: string;
  end: string;
}

export interface Coordinate {
  lat: number;
  lon: number;
}

export interface FuelStop {
  station_id: string;
  name: string;
  city: string;
  state: string;
  lat: number;
  lon: number;
  route_mile: number;
  off_route_miles: number;
  gallons_added: number;
  price_per_gallon: number;
  stop_cost: number;
}

export interface RouteResponse {
  start: string;
  end: string;
  total_miles: number;
  duration_hours: number;
  route: Coordinate[];
  fuel_stops: FuelStop[];
  total_fuel_cost: number;
  total_gallons: number;
}

export type RouteStatus =
  | { phase: 'idle' }
  | { phase: 'loading' }
  | { phase: 'success'; data: RouteResponse }
  | { phase: 'error'; message: string };
