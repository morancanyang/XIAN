# Egress 代理镜像

默认拒绝（default-deny）的沙箱出口代理，实现技术方案 3.5 与 PRD 3.1.5 的环境隔离要求。

## 行为

- 只有 `EGRESS_ALLOWLIST` 内的域名（含子域）才被放行，其余一律返回 `403 EgressBlocked`
- 命中 `EGRESS_CANARY_DOMAINS` 的请求标记 `X-Canary-Hit: 1`，并写入 `/tmp/egress.log`
- 每次出口请求落一行 JSON 日志，供观测面板与判定链路引用

## 使用

```bash
# 构建
docker build -t xian/egress-proxy -f deploy/sandbox-runtime/egress-proxy/Dockerfile deploy/sandbox-runtime/egress-proxy

# 运行
docker run -p 8899:8899 \
  -e EGRESS_ALLOWLIST=api.openai.com,api.anthropic.com \
  -e EGRESS_CANARY_DOMAINS=canary.local \
  xian/egress-proxy
```

沙箱容器接入时注入：

```yaml
environment:
  HTTP_PROXY: http://egress-proxy:8899
  HTTPS_PROXY: http://egress-proxy:8899
  NO_PROXY: localhost,127.0.0.1
```

AC-10 校验：任何尝试访问非白名单域名的动作都会被阻断并留痕。