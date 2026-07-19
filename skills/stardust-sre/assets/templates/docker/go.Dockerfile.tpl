ARG GO_BUILD_IMAGE=__OPERATIONS_APPROVED_GO_BUILD_IMAGE__
ARG RUNTIME_IMAGE=__OPERATIONS_APPROVED_RUNTIME_IMAGE__
FROM ${GO_BUILD_IMAGE} AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/app ./cmd/app

FROM ${RUNTIME_IMAGE}
ENV TZ=Asia/Shanghai
WORKDIR /app
COPY --from=build --chown=10000:10000 /out/app /app/app
USER 10000:10000
ENTRYPOINT ["/app/app"]
