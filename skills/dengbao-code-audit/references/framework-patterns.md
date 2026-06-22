# 框架识别与检查路径

## Java / Spring Boot

重点文件：
- `pom.xml`, `build.gradle`
- `src/main/java/**/controller/**`, `**/security/**`, `**/config/**`, `**/filter/**`, `**/interceptor/**`
- `application.yml`, `application-*.yml`, `bootstrap.yml`
- `mapper/**/*.xml`, `repository`, `dao`

检查点：
- Spring Security 配置：`permitAll`, `antMatchers`, `requestMatchers`, `csrf`, `cors`, `sessionManagement`。
- Controller 是否依赖统一认证上下文，不直接信任请求中的 userId/tenantId。
- MyBatis `${}` 拼接、`@Select` 拼接 SQL、JPA native query 拼接。
- Actuator 暴露：`management.endpoints.web.exposure.include=*`。
- 密码加密：`BCryptPasswordEncoder` 优先，避免 MD5/SHA1。
- 日志：是否有 AOP/Interceptor 审计关键操作。

## Node.js / Express / NestJS / Koa

重点文件：
- `package.json`, `src/**/*.controller.ts`, `routes`, `middleware`, `guards`, `auth`
- `.env*`, `config`, `ormconfig`, `prisma`, `sequelize`

检查点：
- 路由是否统一挂载 auth middleware/guard。
- `jwt.sign` secret、session secret、cookie 配置。
- `cors({ origin: "*" })` 或 `app.use(cors())`。
- `child_process.exec/spawn`, `eval`, `Function`。
- SQL/ORM raw query 拼接：`query("..."+)`, `$queryRawUnsafe`。
- 文件上传：`multer.any()`, 原始文件名、路径拼接、公开目录。
- SSRF：`axios/fetch/request` 使用用户传入 URL。

## Python / Django / Flask / FastAPI

重点文件：
- `requirements.txt`, `pyproject.toml`
- `settings.py`, `urls.py`, `views.py`, `routers`, `dependencies`, `middleware`

检查点：
- Django `DEBUG=True`, `ALLOWED_HOSTS=["*"]`, CSRF 中间件。
- Flask/FastAPI 路由是否使用认证依赖。
- `subprocess`, `os.system`, `eval`, `exec`。
- SQLAlchemy raw SQL、Django `.raw()` 拼接。
- `requests.get(user_url)` SSRF。
- 文件上传保存路径和后缀/MIME/大小校验。

## React / Vue / Next.js / Vite

重点文件：
- `package.json`, `src/router`, `src/routes`, `src/api`, `src/store`, `src/utils/request`
- `.env*`, `next.config.*`, `vite.config.*`

检查点：
- 前端权限只能作为体验控制，不能作为唯一控制。
- `dangerouslySetInnerHTML`, `v-html`, `innerHTML`。
- token 是否放入 `localStorage` 或 URL。
- API base URL 是否写死 HTTP 或生产内网地址。
- 错误页面和调试信息是否泄露接口、token、堆栈。

## Docker / Kubernetes / Nginx / CI

重点文件：
- `Dockerfile`, `docker-compose*.yml`
- `k8s/**/*.yml`, `helm`, `values.yaml`
- `nginx.conf`, `*.conf`
- `.github/workflows`, `.gitlab-ci.yml`, `Jenkinsfile`

检查点：
- 是否暴露 `22`, `3306`, `5432`, `6379`, `27017`, `9200`, `15672`, `9090`, `3000`, `8080` 等端口到公网。
- 是否使用 root 用户运行容器。
- 是否把 secrets 写入镜像、环境变量样例或 CI 日志。
- Nginx 是否强制 HTTPS、设置安全头、限制管理路径。
- CI/CD 是否存在生产发布审批、保护分支、回滚脚本。
