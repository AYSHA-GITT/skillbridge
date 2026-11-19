# Builds the React app and serves it with Caddy, which also proxies /api to Flask and
# obtains/renews the HTTPS certificate automatically.
FROM node:20-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM caddy:2-alpine
COPY --from=build /src/build /srv
