# ReturnGuard frontend

Next.js (App Router, TypeScript, Tailwind). The browser only talks to this server;
`/api/*` is proxied to FastAPI (see `next.config.ts`), so the session cookie stays
same-origin.

```bash
npm ci
npm run dev        # http://localhost:3000, proxies /api to http://localhost:8000
npm run lint
npm run typecheck
npm run build
```

`API_INTERNAL_URL` sets the proxy target. `next.config.ts` is read at build time, so the
Docker image receives it as a build argument (see `../docker-compose.yml`).

This project uses Next.js 16: check `node_modules/next/dist/docs/` before relying on
older Next.js conventions.
