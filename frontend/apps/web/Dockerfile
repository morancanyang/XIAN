# syntax=docker/dockerfile:1
# XIAN Web 控制台镜像：多阶段构建 + nginx 静态托管
FROM node:22-alpine AS builder

RUN corepack enable && corepack prepare pnpm@9.12.0 --activate

WORKDIR /app
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml frontend/.npmrc ./
COPY frontend/packages ./packages
COPY frontend/apps/web ./apps/web

RUN pnpm install --frozen-lockfile \
    && pnpm --filter @xian/types build:skip || true \
    && pnpm --filter @xian/web build


FROM nginx:1.27-alpine

COPY deploy/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]