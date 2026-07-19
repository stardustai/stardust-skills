# syntax=docker/dockerfile:1
ARG NODE_BUILD_IMAGE=__OPERATIONS_APPROVED_NODE_BUILD_IMAGE__
ARG RUNTIME_IMAGE=__OPERATIONS_APPROVED_NODE_RUNTIME_IMAGE__
FROM ${NODE_BUILD_IMAGE} AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
RUN npm run build && npm prune --omit=dev

FROM ${RUNTIME_IMAGE}
ENV NODE_ENV=production TZ=Asia/Shanghai
WORKDIR /app
COPY --from=build --chown=10000:10000 /src/package.json ./
COPY --from=build --chown=10000:10000 /src/node_modules ./node_modules
COPY --from=build --chown=10000:10000 /src/dist ./dist
USER 10000:10000
ENTRYPOINT ["node", "dist/main.js"]
