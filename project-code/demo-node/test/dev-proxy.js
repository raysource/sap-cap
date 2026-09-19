#!/usr/bin/env node
/**
 * 本地开发用的小代理：给浏览器请求注入 Basic 认证，然后再转发给 CAP 服务。
 *
 * 为什么需要它：CAP 服务上写了 `@(requires: 'authenticated-user')`，
 * 而 Fiori 应用在浏览器里发起 OData 请求时不会带凭据（本地没有 approuter / XSUAA
 * 做登录跳转），于是页面会因为 401 显示 "No data" 或直接报错。
 * 这个代理把 `Authorization: Basic alice:alice` 加到每个请求上，模拟「已登录用户」。
 *
 *   node test/dev-proxy.js            # 默认 4005 -> 4004，用户 alice
 *   PORT=4005 TARGET=http://localhost:4004 AUTH_USER=alice:alice node test/dev-proxy.js
 *
 * 然后打开： http://localhost:4005/book-orders/webapp/index.html
 * （仅用于本地教学；真实部署由 approuter + XSUAA 负责认证，不要把它带上生产。）
 */
const http = require('http');

const PORT = Number(process.env.PORT || 4005);
const TARGET = process.env.TARGET || 'http://localhost:4004';
/* 注意：不要用 process.env.USER —— 那是操作系统的登录名，会覆盖这里的设置 */
const USER = process.env.AUTH_USER || 'alice:alice';
const AUTH = 'Basic ' + Buffer.from(USER).toString('base64');
const target = new URL(TARGET);

const server = http.createServer((req, res) => {
  const headers = { ...req.headers, authorization: AUTH, host: target.host };
  const proxied = http.request(
    { hostname: target.hostname, port: target.port || 80, path: req.url, method: req.method, headers },
    (upstream) => {
      res.writeHead(upstream.statusCode, upstream.headers);
      upstream.pipe(res);
    }
  );
  proxied.on('error', (e) => {
    res.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('proxy error: ' + e.message + '\n');
  });
  req.pipe(proxied);
});

server.listen(PORT, () => {
  console.log(`dev-proxy: http://localhost:${PORT}  ->  ${TARGET}   (as ${USER})`);
  console.log(`open: http://localhost:${PORT}/book-orders/webapp/index.html`);
});
