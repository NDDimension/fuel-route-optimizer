"""
            if BootstrapState.error:
                return Response(
                    {
                        "error": BootstrapState.error,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {
                    "error": (
                        "Route optimizer services are still starting. "
                        "Please retry in 30-60 seconds."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        routing_svc = RouteConfig.routing_service
        fuel_index = RouteConfig.fuel_station_index
        optimizer = RouteConfig.fuel_optimizer

        try:
            # ------------------------------------------------------------------
            # 3. Fetch route
            # ------------------------------------------------------------------
            route_result = routing_svc.get_route(start, end)

            # ------------------------------------------------------------------
            # 4. Find nearby stations
            # ------------------------------------------------------------------
            nearby = fuel_index.find_near_route(
                route_coords=route_result.coords,
                route_cum_miles=route_result.cum_miles,
                max_off_route_miles=settings.MAX_OFF_ROUTE_MILES,
            )

            logger.info(
                "Found %d candidate stations near route",
                len(nearby),
            )

            # ------------------------------------------------------------------
            # 5. Optimize route
            # ------------------------------------------------------------------
            opt_result = optimizer.optimize(
                candidate_stations=nearby,
                total_route_miles=route_result.total_miles,
            )

        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except RouteOptimizationError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        except http_requests.HTTPError as exc:
            logger.error("Mapbox API error: %s", exc)

            return Response(
                {"error": f"Upstream routing API error: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except Exception:
            logger.exception("Unexpected route processing failure")

            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ------------------------------------------------------------------
        # 6. Response payload
        # ------------------------------------------------------------------
        response_data = {
            "start": start,
            "end": end,
            "total_miles": round(route_result.total_miles, 1),
            "duration_hours": round(route_result.duration_sec / 3600, 2),
            "route": [
                {"lat": lat, "lon": lon}
                for lat, lon in route_result.coords[::5]
            ],
            "fuel_stops": [
                {
                    "station_id": stop.station_id,
                    "name": stop.name,
                    "city": stop.city,
                    "state": stop.state,
                    "lat": stop.lat,
                    "lon": stop.lon,
                    "route_mile": stop.route_mile,
