ARG JAVA_BUILD_IMAGE=__OPERATIONS_APPROVED_JAVA_BUILD_IMAGE__
ARG RUNTIME_IMAGE=__OPERATIONS_APPROVED_JAVA_RUNTIME_IMAGE__
FROM ${JAVA_BUILD_IMAGE} AS build
WORKDIR /src
COPY . .
RUN ./mvnw -B -DskipTests package

FROM ${RUNTIME_IMAGE}
ENV TZ=Asia/Shanghai JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=70 -XX:+ExitOnOutOfMemoryError"
WORKDIR /app
COPY --from=build --chown=10000:10000 /src/target/*.jar /app/app.jar
USER 10000:10000
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
