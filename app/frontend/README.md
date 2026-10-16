# ReturnGuard frontend

Next.js (App Router, TypeScript, Tailwind). The browser only talks to this server;
`/api/*` is proxied to FastAPI by `src/app/api/[...path]/route.ts`, so the session
cookie stays same-origin and the API sees the browser's address.

```bash
npm ci
npm run dev        # http://localhost:3000, proxies /api to http://localhost:8000
npm run lint
npm run typecheck
npm run build
```

`API_INTERNAL_URL` sets the proxy target (default `http://localhost:8000`); it is read at
runtime. API types in `src/lib/api-schema.d.ts` are generated: run `make api-types` from
`app/` after changing the API.

This project uses Next.js 16: check `node_modules/next/dist/docs/` before relying on
older Next.js conventions.
