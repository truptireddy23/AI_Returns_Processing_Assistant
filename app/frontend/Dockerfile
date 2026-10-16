# syntax=docker/dockerfile:1

FROM node:24-alpine AS deps
WORKDIR /srv
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

FROM node:24-alpine AS build
WORKDIR /srv
# next.config.ts is read at build time, so the API address is baked in here.
ARG API_INTERNAL_URL=http://api:8000
ENV API_INTERNAL_URL=$API_INTERNAL_URL \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /srv/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24-alpine AS runtime
WORKDIR /srv
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY --from=build --chown=node:node /srv/.next/standalone ./
COPY --from=build --chown=node:node /srv/.next/static ./.next/static
COPY --from=build --chown=node:node /srv/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
