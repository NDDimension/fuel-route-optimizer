# Render + Vercel Deployment

## Backend on Render

1. Push this repository to GitHub.
2. In Render, create a new Blueprint from the repo root.
3. Render will detect [render.yaml](./render.yaml) and create the `routeopt-api` web service.
4. During setup, provide values for:
   - `MAPBOX_TOKEN`
   - `DJANGO_SECRET_KEY`
5. After the first deploy, open the Render service and set:
   - `ALLOWED_HOSTS` to your Render hostname or custom API domain
   - `CORS_ALLOWED_ORIGINS` to your Vercel production URL
   - `CORS_ALLOWED_ORIGIN_REGEXES` to your preview URL regex if you want preview deploys to talk to the API

Recommended preview regex:

```text
^https://.*\.vercel\.app$
```

Health check endpoint:

```text
/health/
```

## Frontend on Vercel

1. Import this repository into Vercel.
2. Keep the project root at the repository root.
3. Vercel will use [vercel.json](./vercel.json).
4. Add these environment variables in Vercel:
   - `VITE_API_BASE_URL=https://your-render-api-domain`
   - `VITE_MAPBOX_TOKEN=your_public_mapbox_token`
5. Redeploy after saving environment variables.

## Post-deploy wiring

Once both services are live:

1. Copy the Vercel production URL.
2. Add it to Render as `CORS_ALLOWED_ORIGINS`.
3. Copy the Render API hostname.
4. Add it to Vercel as `VITE_API_BASE_URL`.
5. Trigger a redeploy on both sides if needed.
