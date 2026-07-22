# Multi-stage build for the customer web app — see docs/deployment.md
# #api-web-admin. Built from the *repository root* (npm workspaces need the
# root lockfile/package.json): `docker build -f apps/web/Dockerfile .`
#
# `next.config.ts`'s `output: "standalone"` traces only the dependencies
# each page actually needs into `.next/standalone`, so the final image
# doesn't carry the whole monorepo's node_modules.

FROM node:24-slim AS builder
WORKDIR /repo

COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY apps/admin/package.json apps/admin/package.json
# Whole packages/ tree (source, not just package.json) copied before
# `npm ci` — these workspace packages have no build step of their own
# (consumed as TS/CSS source directly by apps/web), and copying only their
# package.json files left npm unable to complete the workspace symlink for
# @mehndiverse/design-tokens (found the hard way: a Docker build of this
# Dockerfile failed with `Can't resolve '@mehndiverse/design-tokens/src/
# tokens.css'`, and `node_modules/@mehndiverse/design-tokens` was missing
# entirely after `npm ci`). See docs/deployment.md#api-web-admin.
COPY packages ./packages
RUN npm ci

COPY . .
RUN npm run build --workspace=apps/web

# --- Runtime image ---------------------------------------------------------
FROM node:24-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

# Standalone output preserves the monorepo-relative path
# (apps/web/server.js) — see docs/deployment.md for why.
COPY --from=builder /repo/apps/web/.next/standalone ./
COPY --from=builder /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /repo/apps/web/public ./apps/web/public

EXPOSE 3000
CMD ["node", "apps/web/server.js"]
