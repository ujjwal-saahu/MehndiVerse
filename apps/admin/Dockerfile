# Multi-stage build for the admin dashboard — see docs/deployment.md
# #api-web-admin. Built from the *repository root*:
# `docker build -f apps/admin/Dockerfile .`

FROM node:24-slim AS builder
WORKDIR /repo

COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY apps/admin/package.json apps/admin/package.json
# See apps/web/Dockerfile for why this is the whole packages/ tree, not
# just each package's package.json.
COPY packages ./packages
RUN npm ci

COPY . .
RUN npm run build --workspace=apps/admin

# --- Runtime image ---------------------------------------------------------
FROM node:24-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /repo/apps/admin/.next/standalone ./
COPY --from=builder /repo/apps/admin/.next/static ./apps/admin/.next/static
COPY --from=builder /repo/apps/admin/public ./apps/admin/public

EXPOSE 3000
CMD ["node", "apps/admin/server.js"]
