FROM node:24-bookworm-slim

WORKDIR /app
ENV NODE_ENV=production \
    WRANGLER_SEND_METRICS=false

COPY package.json package-lock.json .npmrc ./
RUN npm ci --include=dev --include=optional --no-audit --no-fund

COPY . .
RUN npm run build && mkdir -p /app/.wrangler /app/.sites-runtime \
    && chown -R node:node /app/dist /app/.wrangler /app/.sites-runtime

USER node
EXPOSE 8787
CMD ["node", "--import", "./scripts/sites-env.mjs", "./node_modules/wrangler/bin/wrangler.js", "dev", "--config", "dist/server/wrangler.json", "--local", "--ip", "0.0.0.0", "--port", "8787", "--inspector-port", "0"]
