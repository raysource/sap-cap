# SAP CAP 培训课程站（`sap-cap/`）

从 **BTP 试用账号注册 → BAS 开发环境 → HANA Cloud → CDS 建模 → Node.js / Java 双运行时服务 →
测试 → 权限 → Fiori UI → 构建部署** 的全流程中文课程，静态 HTML、离线可开、无外部依赖，
并交付一个**在本机真实跑通**的端到端示范项目（含 Fiori Elements 界面与 26 条 OData 验收断言）。

---

## 1. 打开方式

```bash
open ~/Desktop/work/training/sap-cap/index.html      # 直接双击也行，不需要服务器
```

站点是纯静态的：`assets/style.css` + `assets/main.js` + `assets/quiz.js` + `assets/cap.css`，
代码高亮与「复制」按钮由 `main.js` 提供，自测题判分由 `quiz.js` 提供。

## 2. 页面清单（20 页 + 3 个生成页）

| 页面 | 主题 |
|---|---|
| `index.html` | 课程地图、学习路线、环境清单、交付物、实测证据 |
| `concept.html` | CAP 概念总览：三层架构、请求生命周期、Node/Java 分工、常见误解 |
| `btp.html` | ① 从 BTP 注册到环境就绪（子账户 / 权限 / CF / CLI / 服务实例） |
| `bas.html` | ② Business Application Studio 开发环境 |
| `hana.html` | ③ SAP HANA Cloud 与 HDI 容器 |
| `cds.html` | ④ CDS 建模（类型、关联、视图、注解、种子数据陷阱、排错手册） |
| `node.html` | ⑤ CAP Node.js 服务实现（事件处理器、CQN、草稿） |
| `java.html` | ⑥ CAP Java 服务实现（Maven、cds-maven-plugin、@Before/@After/@On） |
| `testing.html` | ⑦ 测试体系（模型检查 → 单元 → OData 集成 → CI） |
| `security.html` | ⑧ 认证与授权（mocked/dummy、XSUAA、@requires/@restrict） |
| `fiori.html` | ⑨ Fiori Elements 应用与注解 |
| `deploy.html` | ⑩ MTA 构建、cf 部署、CI/CD |
| `project.html` | **示范项目端到端**（需求 → 模型 → 服务 → 测试 → 界面 → 部署） |
| `code.html` | 示范项目全部源码（由 `tools/build_code.py` 生成） |
| `cli.html` / `issues.html` / `glossary.html` | 命令速查 / 故障排除手册 / 术语对照 |
| `instructor.html` / `worksheet.html` / `quiz.html` | 讲师版 / 学员版工作纸 / 自测（由 `tools/build_quiz.py` 生成） |
| `tasks.html` | 任务索引 119 条（由 `tools/build_tasks.py` 生成） |

## 3. 示范项目（真实可运行）

| 目录 | 内容 | 本机状态 |
|---|---|---|
| `project-code/demo-node/` | CAP Node.js：模型 + 服务 + 业务规则 + Fiori Elements + 验收脚本 + MTA | **实测通过**：`npm install` → `npm run deploy`（6 张表 / 21 行）→ `npm start` → `bash test/odata-verify.sh` **PASS 26 / FAIL 0**；Fiori List Report 在浏览器里渲染成功（`assets/fig/real/fiori_list_report.png`） |
| `project-code/demo-java/` | 同一套 `db/` 与 `srv/*.cds` 的 Java 实现（Maven + Spring Boot + cds-maven-plugin） | **部分通过**：`mvn compile` BUILD SUCCESS、服务启动、CSV 灌入 H2、`$metadata` 200；**带认证的实体读取仍 401**（本地 mock 用户配置未找到正确写法，记录在 `java.html` §10） |

一键起停本地演示环境：

```bash
bash tools/serve_demo.sh start|status|stop      # 4004 = CAP 服务，4005 = 注入 mock 认证的代理
```

## 4. 目录结构

```
sap-cap/
├── *.html                        课程页面（20 页 + 生成页）
├── assets/
│   ├── style.css main.js quiz.js  从生态共享（未改动）
│   ├── cap.css                    本站扩展：两行导航、figure 版式、本节测试等
│   └── fig/                       92 张高保真重绘画面（SVG）+ real/ 下 1 张真实截图
├── project-code/{demo-node,demo-java}/
├── tools/
│   ├── figkit/                    画面引擎：figkit.py · SPEC.md · spec.d/*.json · insert.py · insert_missing.py · check_render.py
│   ├── make_nav.py                统一顶栏/页脚（21 个入口，两行）
│   ├── build_quiz.py              汇总 work/quiz/*.json → quiz.html（196 题）
│   ├── build_tasks.py             汇总 work/tasks/*.json → tasks.html（119 条）
│   ├── build_code.py              从 project-code/ 生成 code.html（源码全文）
│   ├── check_page.py              单页静态检查（标签平衡 / 链接 / quiz / FIG / 图片 alt）
│   ├── check_anchors.py           锚点级链接检查（page.html#id 是否真的存在）
│   ├── serve_demo.sh              起停本地演示环境
│   └── shot.js                    CDP 真实截图（等页面出现指定文本再截）
├── work/
│   ├── evidence/                  真实运行证据：01_deploy · 02_tables · 03_server · 04_odata · 05_metadata · 06_proxy · 07_java_server · 08_java_odata
│   ├── quiz/ tasks/               子代理写的题目与任务片段（quiz.html / tasks.html 的数据源）
│   └── sqlite_tables.py           建库后核对表与行数的小脚本
└── CAP培训_手顺书_学习WBS.xlsx      手顺书 + 学习 WBS（若已生成）
```

## 5. 改动后请重新生成的步骤

```bash
cd ~/Desktop/work/training/sap-cap
python3 tools/figkit/figkit.py --all tools/figkit/spec.d --outdir assets/fig   # 1. 画面
python3 tools/figkit/insert.py                                                # 2. 插入页面（按 <!--FIG:key--> 标记）
python3 tools/make_nav.py                                                     # 3. 顶栏/页脚（新增页面后必跑）
python3 tools/build_quiz.py && python3 tools/build_tasks.py && python3 tools/build_code.py
python3 tools/check_page.py --all                                             # 4. 检查
```

## 6. 关于画面与数据的声明（与页面口径一致）

- BTP Cockpit / BAS / HANA / Fiori 的画面是本站用 SVG **重绘的高保真画面**（图注标「高保真重绘」），
  不是实机截图；标签文字可能随版本/区域变化。
- 标「本地实机运行」的内容（终端输出、表格数据、Fiori 截图）是真实命令的输出，图注里写了产生它的命令。
- 服务 plan、配额、角色集合名、API 端点等**标准值**随版本与区域不同，页面里给了「自系统确认方法」。
- BTP 云端部分（`mbt build` / `cf deploy`）**未在本机执行**（无试用账号），命令与验证清单来自官方文档。

## 7. 仓库与发布

- 本站是独立仓库：**https://github.com/raysource/sap-cap** （public，`main`）。
  历史是父仓库 `raysource/sap-consult` 用 `git subtree split -P sap-cap` 切出来的，5 条本站提交一条不少。
- 发布/同步：`bash tools/publish_to_github.sh ["提交信息"]` —— init（若无）+ 建/改 remote +
  `git add -A` + commit + push，末尾调用
  `scripts/reconcile_published_repo.sh`（来自 sap-training-sites skill）做**逐路径对账**：
  `local HEAD == git ls-remote == gh api …/commits/main`，且远端 blob 列表 == 本地 `git ls-files`。
  只信这个输出，不信 push 的回显。
- 本仓库的 `.gitignore` 已经挡掉 `node_modules/`、`db.sqlite*`、`target/`、`gen/`、`work/render/`、
  `mta_archives/`、`*.mtar`；**`assets/` 与 `work/evidence`、`work/quiz` 是内容，必须提交**。
- 注意：有了自己的 `.git` 之后，本站就是父仓库里的**嵌套仓库**——在父仓库里
  `git add sap-cap/...` **会静默无效**（git 2.39 实测返回 0 但索引为空）。
  要同步进父仓库请用：
  `bash ../tools/include_nested_repo_files.sh "$PWD/.." sap-cap`
  （读嵌套索引的 mode + blob sha → hash-object 落库 → update-index，脚本会 assert SHA 一致），
  然后核对 `git ls-files sap-cap | wc -l` == `git -C sap-cap ls-files | wc -l`。
