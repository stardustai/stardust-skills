ARG NGINX_IMAGE=__OPERATIONS_APPROVED_NGINX_IMAGE__
FROM ${NGINX_IMAGE}
ENV TZ=Asia/Shanghai
COPY --chown=10000:10000 dist/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
USER 10000:10000
ENTRYPOINT ["nginx", "-g", "daemon off;"]
