# demo-node — 图书受注管理（SAP CAP 培训课程示范项目 · Node.js 运行时）

一个**在本机真实跑通、并被 26 条 OData 断言验证过**的最小完整 CAP 项目：
CDS 领域模型 + OData V4 服务 + 业务规则（编号生成 / 派生金额 / 汇总回写 / 状态迁移 / 聚合函数）
+ Fiori Elements 界面 + 集成测试脚本 + MTA 部署描述。

同一套 `db/` 与 `srv/*.cds` 模型在 `../demo-java/` 里换成 **Java 运行时**实现 —— 这正是 CAP 要演示的
「模型与运行时解耦」。

---

## 1. 目录结构

```
demo-node/
├── db/
│   ├── schema.cds                     领域模型：Books / Customers / BookOrders / BookOrderItems / OrderItemView
│   └── data/*.csv                     种子数据（表头 = 物理列名）
├── srv/
│   ├── book-order-service.cds         服务定义（投影 / 草稿 / 动作 / 函数 / 授权）
│   └── book-order-service.js          业务逻辑（before / on / after 事件处理器）
├── app/book-orders/
│   ├── annotations.cds                Fiori Elements 的 UI.* 注解（界面长什么样在这里决定）
│   └── webapp/{index.html,manifest.json,Component.js}
├── test/
│   ├── odata-verify.sh                26 条 OData 验收断言（curl 版集成测试）
│   ├── odata.test.js                  mocha + cds.test 的 16 个用例（第 1 层测试）
│   └── dev-proxy.js                   本地给浏览器注入 mock 认证的小代理（看 Fiori 用）
├── approuter/{package.json,xs-app.json}   部署时的对外入口（认证 + 转发）
├── mta.yaml                           部署描述符（srv + approuter + hana + xsuaa）
├── xs-security.json                   授权定义（scopes / role-templates）
└── package.json                       npm scripts + cds 配置（sqlite / mocked 认证）
```

## 2. 环境要求

| 组件 | 版本 | 说明 |
|---|---|---|
| Node.js | **20 或 22 LTS** | 必须 LTS：`better-sqlite3` 的原生模块要匹配 ABI（本机实测 `v22.23.2`） |
| @sap/cds | 9.x | 与 cds-dk 同大版本 |
| @sap/cds-dk | 9.x | 提供 `cds` CLI（`@sap/cds` 本身不带 CLI） |
| @cap-js/sqlite | 2.x | 本地数据库（SQLite 3.53.2） |

没有 BTP 账号也能完整跑起来；只有 `mta.yaml` / `cf deploy` 那一步需要真实环境。

## 3. 跑起来（本机实测命令）

```bash
cd project-code/demo-node

# 0) 如果系统的 Node 不是 LTS，用 npx 取一个 22：
export PATH="$(dirname "$(npx -y node@22 -p process.execPath)"):$PATH"
node -v                       # → v22.23.2

# 1) 安装依赖
npm install                   # → added 328 packages

# 2) 建库 + 灌种子数据
npm run deploy                # → successfully deployed to db.sqlite

# 3) 启动服务
npm start                     # → server listening on { url: 'http://localhost:4004' }
                              #    serving BookOrderService { at: ['/odata/v4/book-order'] }

# 4) 验收（另开一个终端）
bash test/odata-verify.sh     # → PASS 26 / FAIL 0
```

### 3.1 实测输出（本机真实结果）

`npm run deploy`：

```
  > init from db/data/sap.training.bookorder-Customers.csv
  > init from db/data/sap.training.bookorder-Books.csv
  > init from db/data/sap.training.bookorder-BookOrders.csv
  > init from db/data/sap.training.bookorder-BookOrderItems.csv
/> successfully deployed to db.sqlite
```

`work/sqlite_tables.py db.sqlite`（用 python3 直接查 sqlite_master，确认没有「静默回滚」）：

```
TABLES: ['BookOrderService_BookOrders_drafts', 'DRAFT_DraftAdministrativeData',
         'cds_outbox_Messages', 'sap_training_bookorder_BookOrderItems',
         'sap_training_bookorder_BookOrders', 'sap_training_bookorder_Books',
         'sap_training_bookorder_Customers']
  sap_training_bookorder_BookOrderItems 9 rows
  sap_training_bookorder_BookOrders  4 rows
  sap_training_bookorder_Books       5 rows
  sap_training_bookorder_Customers   3 rows
```

`bash test/odata-verify.sh`（节选，完整输出见课程站「测试体系」页）：

```
== 1. 服务可达性与认证 ==
  PASS  GET $metadata (alice)                                      200
  PASS  GET /BookOrders 匿名 → 401                                401
  PASS  GET /BookOrders (bob)                                      200
  PASS  GET /BookOrders 任意用户(mocked 放行)                       200
== 2. 读：过滤 / 展开 / 只读视图 ==
  PASS  GET BookOrders?$filter=status eq OPEN → 2 张                2
  PASS  GET BookOrders 带 $expand=items 行数                        3
  PASS  GET OrderItemView (带主键视图，可暴露)                      9
== 3. 函数（无绑定）：聚合走函数而不是实体 ==
  PASS  getOrderTotal(BO-1003) = 17400                          17400
  PASS  getOrderTotal(不存在) → 404                                404
  PASS  getOrderSummary() 4 行                                       4
== 4. 写：派生字段与汇总回写 ==
  PASS  POST 明细：金额自动计算 = 2800×3                          8400
  PASS  POST 明细后父订单合计被回写 = 12000                       12000
== 5. 负向：业务校验必须返回 4xx ==
  PASS  POST 数量 0 → 400                                          400
  PASS  POST 图书不存在 → 400                                      400
  PASS  只读实体 POST → 405                                        405
== 6. 草稿（@odata.draft.enabled）创建与激活 ==
  PASS  POST 新建订单 → 草稿未激活                               False
  PASS  重复订单号激活 → 409                                       409
  PASS  顾客不存在激活 → 400                                        400
  PASS  正常激活 → 201 并自动编号                                  201
  PASS  自动编号 = BO-1005                                      BO-1005
== 7. 绑定动作 submitOrder（状态迁移） ==
  PASS  空订单提交 → 400                                           400
  PASS  BO-1001 提交 → 200                                         200
  PASS  状态已变为 SUBMITTED                                 SUBMITTED
  PASS  重复提交 → 409                                             409

  PASS 26 / FAIL 0
```

> 注意：验收脚本会**修改数据**（新增明细、提交订单、自动新建 BO-1005）。
> 想重复运行就先 `rm -f db.sqlite && npm run deploy` 再重启服务，否则断言会失败。

### 3.2 第 1 层测试：mocha + cds.test（16 用例）

`test/odata.test.js` 用官方 `cds.test` 起一个真实服务，直接打 OData 接口做断言（含 400/401/405/409 负向用例与草稿流程）。
`@sap/cds` 9 的 `cds.test` 需要单独安装测试包，而它的 peer 依赖要求 `chai@^6`（本项目是 `^5`），所以：

```bash
npm i -D @cap-js/cds-test --legacy-peer-deps   # 或把 chai 升到 ^6 后 npm i -D @cap-js/cds-test
npm test                                       # → 16 passing (~0.4s)
```

`odata.test.js` 的 `before()` 里调用了 `data.reset()`：**本站 `cds.test` 连的就是 `db.sqlite`**，
不重置的话第二次运行会被上一次写的数据影响（课程站「⑦ 测试体系」第 5 节给了连跑两次的 FAIL 对照）。

### 3.3 手工验证（一条 curl 就够）

```bash
# 匿名 → 401（服务上有 @(requires: 'authenticated-user')）
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:4004/odata/v4/book-order/BookOrders

# 取数据（mocked 认证：用户名任意，口令随便）
curl -s -u alice:alice \
  "http://localhost:4004/odata/v4/book-order/BookOrders?\$expand=items&\$select=orderNo,status,totalAmount"
```

返回（节选，真实输出）：

```json
{"@odata.context":"$metadata#BookOrders","value":[
 {"orderNo":"BO-1001","status":"OPEN","totalAmount":16000,
  "items":[{"quantity":2,"amount":8400},{"quantity":1,"amount":2800},{"quantity":1,"amount":4800}]}, ... ]}
```

## 4. 界面（Fiori Elements）

```bash
# 服务已在 4004 运行的前提下，再起一个注入 mock 认证的小代理
node test/dev-proxy.js          # → http://localhost:4005 -> http://localhost:4004 (as alice:alice)
```

浏览器打开 <http://localhost:4005/book-orders/webapp/index.html>：

- **List Report**：订单号 / 顾客 / 日期 / 状态（按 Criticality 着色）/ 合计，行内动作「提交订单」
- **Object Page**：订单信息 + 金额 + 明细表，编辑走 draft（POST draft → PATCH → draftActivate）

界面里出现的每一列、每个按钮，都由 `app/book-orders/annotations.cds` 的 `UI.LineItem` /
`UI.FieldGroup` / `UI.Facets` / `UI.DataFieldForAction` 决定；`manifest.json` 只决定「用哪个模板、路由怎么走」。
验证注解真的进了服务元数据：

```bash
curl -s -u alice:alice "http://localhost:4004/odata/v4/book-order/\$metadata" | grep -c Annotation   # → 166
```

### 为什么需要 `dev-proxy.js`？

CAP 服务要求认证，但浏览器里的 Fiori 应用不会带 Basic 凭据（本地没有 approuter / XSUAA 做登录跳转），
于是页面会 401 → 显示 No data。这个 20 行的代理给每个请求补上 `Authorization: Basic alice:alice`，
模拟「已登录用户」。**真实部署时由 approuter + XSUAA 负责认证，不要把它带到生产。**

## 5. 业务规则清单（都在 `srv/book-order-service.js`）

| # | 位置 | 规则 | 失败时的响应 |
|---|---|---|---|
| ① | `before CREATE BookOrders` | 没给订单号就自动编号（`max(orderNo)+1`）；给了就查重 | 409 `订单号 … 已存在` |
| ① | `before CREATE BookOrders` | 顾客必须存在 | 400 `顾客 … 不存在` |
| ① | `before CREATE BookOrders` | 初始化 `status='OPEN'` 与 `statusCriticality`（派生字段） | — |
| ② | `before CREATE/UPDATE BookOrderItems` | `amount = 图书单价 × 数量`；数量必须 > 0 | 400 `数量必须大于 0` / `图书 … 不存在` |
| ③ | `after CREATE/UPDATE/DELETE BookOrderItems` | 汇总回写父订单的 `totalAmount` | — |
| ④ | `on submitOrder`（绑定动作） | 空订单不能提交、合计必须 > 0、不能重复提交；提交后状态 + Criticality 同步 | 400 / 404 / 409 |
| ⑤ | `on getOrderTotal` / `getOrderSummary`（无绑定函数） | 聚合结果**没有主键**，不能作为实体暴露 → 用函数返回 | 404（订单号不存在） |

设计取舍（课程里会展开讲，也都是真实踩过的坑）：

1. **不用 `Composition`，用显式 `Association to many … on`。**
   managed composition 会在**父表**加 FK 列，用 CSV 播种时父侧 FK 是空的 → `$expand=items` 返回 `[]`。
   子表用普通列 + 显式反向关联，CSV 与 `$expand` 都正常。
2. **聚合视图不暴露为实体。** group by 的结果没有主键，`cds2edm` 会报
   `Expected entity to have a primary key`；能用实体暴露的是**带主键的视图**（本项目 `OrderItemView`）。
3. **两张实体都源自 `db.BookOrderItems` 时必须显式指定重定向目标**，否则报
   `can't auto-redirect BookOrders:items` → 在 `BookOrderItems` 投影上加 `@cds.redirection.target`。
4. **`statusCriticality` 是派生字段**，由服务端维护（`0 Neutral / 1 Negative / 2 Critical / 3 Positive`），
   界面用它给状态列着色，客户端改不了。
5. **`mocked` 认证会放行任意用户名** —— 它不是真认证，只是开发期模拟。
   因此「未知用户 → 401」这条断言在本地**不成立**（真实验收脚本里就是按 200 断言的）。

## 6. 部署（需要 BTP 试用账号）

```bash
npm ci
npx cds build --production          # → gen/srv, gen/db
npm i -g mbt && mbt build -t mta_archives
cf login -a https://api.cf.ap10.hana.ondemand.com --sso
cf deploy mta_archives/demo-node_1.0.0.mtar -f
cf apps                             # 确认 demo-node-srv / demo-node-approuter 都是 started
```

部署后：`demo-node-uaa` 提供 scopes，`OrderAdmin` 角色模板控制「提交订单」，
`demo-node-db` 提供 HDI 容器（表由 hdi-deployer 在部署时创建）。
完整手顺见课程站「⑩ 构建与部署」。

## 7. 已知限制

- 本机没有开通 BTP 试用账号，`mbt build` / `cf deploy` 未在本机执行（命令来自官方文档，未实测）；
  本地可执行的部分（建库、启动、OData 验证、Fiori 预览）全部实测通过。
- Fiori 应用从 `ui5.sap.com` CDN 加载 SAPUI5（`sap.fe.*` 不在 OpenUI5 里）。
  离线教学环境需要把 UI5 下载到本地并由 approuter/srv 提供。
- 使用 SQLite 只适合本地教学；上云请用 HANA Cloud（`cds bind` 或 MTA resource）。
