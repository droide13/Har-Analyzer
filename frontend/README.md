# HAR Analyzer frontend

React + TypeScript + Vite. Talks to the FastAPI backend in `../backend` (dev
server proxies `/api/*` to `http://127.0.0.1:8000`, see `vite.config.ts`).

```bash
npm install
npm run dev      # http://localhost:5173, backend must be running separately
npm run build    # type-checks (tsc -b) then builds
npm run lint      # oxlint
```
