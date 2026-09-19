# figkit 画面 spec 格式（写画面的人必读）

一个画面 = 一个 JSON 文件，放在 `tools/figkit/spec.d/<key>.json`，文件名就是 key。
渲染：`python3 tools/figkit/figkit.py --all tools/figkit/spec.d --outdir assets/fig`
产物：`assets/fig/<key>.svg`（离线、无外部依赖、1440×900 或自定义）。

**硬规则**

1. `callouts[].on` 必须**逐字**出现在画面上的某个文本里（可以是子串）。找不到 → 渲染失败并报错。
   代码块（`code` 块 / BAS 编辑器的 `editor.lines`）按**整行**匹配，例如 `on: "items : Association to many"`。
2. 内容不得超出画布：渲染器会报 `content overflows canvas`，处理办法是删掉几行/缩短文案（不要改画布尺寸，除非整站统一）。
3. 不要自己写 HTML 实体（`&lt;`）。文字直接写 `<` 即可，渲染器会转义。
4. 换行符 `\n` 不会被解释：要换行就用 `p` 块的多行，或者用 `wrap`（自动折行）。

## 顶层字段

| 字段 | 说明 |
|---|---|
| `key` | 画面 id，= 文件名（如 `btp_s01`）。页面里用 `<!--FIG:btp_s01-->` 引用 |
| `kind` | `cockpit` \| `bas` \| `terminal` \| `fiori` \| `hana` \| `dialog` |
| `w`, `h` | 画布尺寸，默认 1440×900。整站统一用默认值 |
| `caption` | **页面上的图注**（会写进 figcaption），中文，一句话说清这张画面在看什么 |
| `alt` | 图片 alt 文本（无障碍）。省略则用 caption |
| `label` | 图注右侧的小标签，默认「高保真重绘」；本地实际运行截图写「本地实机运行」 |
| `src` | 图注来源行，默认「本站自绘（figkit 高保真画面）」。写实测输出时写实际命令，例如 `本地实测：npx cds watch` |
| `callouts` | 红色编号标注数组，见下 |

## callouts

```json
{"on": "Create Instance", "text": "1. 点这里创建实例"}
{"on": "hdi-shared", "on_index": 2, "text": "2. CAP 必须用 hdi-shared 计划"}
{"at": [820, 240], "text": "3. 空白区域标注（on 找不到时用）"}
```

- `on_index`：同一文本出现多次时取第 n 个（从 1 开始，按从上到下、从左到右排序）。
- 标注气泡由渲染器自动避让文字；若硬放不下会打印 `forced=`，此时**缩短标注文字**（12 字以内最佳）。

## 各 kind 的字段

### `cockpit`（SAP BTP Cockpit / 子账户界面）
```json
{"kind":"cockpit","product":"SAP Business Technology Platform",
 "crumbs":["Global Account: trial (trial-eu10)", "Subaccount: trial"],
 "nav":{"title":"Subaccount: trial","items":[{"label":"Overview","active":true},
        {"label":"Connectivity","sub":["Destinations"]},{"label":"Users","group":true}]},
 "title":"Instances and Subscriptions","subtitle":"…","tabs":["Instances","Marketplace"],"activeTab":0,
 "blocks":[ … ],"status":"底部状态栏文字",
 "callouts":[…]}
```
`nav.items[]` 里：`active:true` = 当前项（可带 `sub` 子项数组）；`group:true` = 分组标题行。

### `bas`（Business Application Studio，VS Code 风格）
```json
{"kind":"bas","window":"schema.cds - demo-node - SAP Business Application Studio",
 "sideTitle":"EXPLORER","sideW":272,
 "side":[{"label":"DEMO-NODE (WORKSPACE)","items":[{"d":0,"k":"folder","open":true,"label":"db","b":true},
        {"d":1,"k":"file","label":"schema.cds","tag":"M"}]}],
 "tabs":["schema.cds","order-service.js"],"activeTab":0,
 "breadcrumb":"demo-node › db › schema.cds",
 "editor":{"lang":"cds","fs":13,"lh":22,"hl":[12,13],"lines":["namespace sap.training.bookorder;",""]},
 "panel":{"title":"TERMINAL","h":218,"extraTabs":["PROBLEMS","OUTPUT"],"lines":["$ npm run deploy","@> cds deploy"]},
 "activity":[{"glyph":"⧉","active":true},{"glyph":"⌕"}],
 "status":["⑂ main","0 ▲ 0 ●","Node 22.20.0","CAP 9.4.2","UTF-8"],
 "callouts":[…]}
```
- `editor` 与 `blocks` 二者选一：有 `editor` 就在编辑器区画代码，否则画 `blocks`。
- 终端行前缀：`$` 绿、`@` 蓝、`#` 黄、其他灰白。
- `hl` 是行号数组（从 1 开始），高亮那几行。

### `terminal`（独立终端窗口，用于命令与输出）
```json
{"kind":"terminal","title":"jason@MacBook-Pro: ~/projects/demo-node",
 "lines":["$ npm run deploy","@> cds deploy --to sqlite:db.sqlite",""],"callouts":[…]}
```
行数 ≤ 40（lh 20）以保证不溢出；超了就拆成两张画面。

### `fiori`（Fiori Elements / Launchpad）
```json
{"kind":"fiori","mode":"app","product":"SAP Fiori","user":"JASON",
 "title":"图书受注管理","subtitle":"Table","crumbs":"Home › 图书受注管理 › 受注一覧",
 "toolbar":{"items":[{"label":"创建","primary":true},{"label":"删除"}],"search":"搜索"},
 "filter":[["订单号",""],["状态",""]],
 "blocks":[…],"callouts":[…]}
```
`mode:"launchpad"` 时改画 Fiori 启动台：
```json
{"kind":"fiori","mode":"launchpad","title":"My Home","subtitle":"…",
 "sections":[{"label":"图书受注管理","cols":4,"items":[{"title":"管理订单","sub":"…","chip":"已发布"}]}]}
```

### `hana`（SAP HANA Cloud / Database Explorer）
```json
{"kind":"hana","product":"SAP HANA Cloud","nav":{"title":"Database Explorer","items":[…]},
 "title":"SQL Console — BOOKORDER.BOOK_ORDERS","tabs":["SQL Console 1"],"blocks":[…],
 "status":"Connected · demo-hana-db (HDI container) · 0.08 s · 4 rows"}
```

### `dialog`（向导 / 弹窗，压在半透明背景上）
```json
{"kind":"dialog","dw":760,"dh":520,"title":"Create Instance","subtitle":"…",
 "under":{"kind":"cockpit","nav":{…},"title":"Instances and Subscriptions","blocks":[…]},
 "steps":{"items":["Basic Information","Parameters","Review"],"active":1},
 "blocks":[…],"buttons":[{"label":"Cancel"},{"label":"Create","primary":true}],"callouts":[…]}
```

## blocks（cockpit / bas / fiori / hana / dialog 通用）

| `t` | 参数 | 用途 |
|---|---|---|
| `h1` `h2` `h3` `h4` | `text`, `mt` | 小标题 |
| `p` | `text`, `size`, `fill` | 段落（自动折行，CJK 按全角计算） |
| `kv` | `rows`:[[label,value]], `lw` | 键值对列表 |
| `table` | `cols`, `rows`, `widths`(相对权重), `selected`(行号), `hh`, `rh`, `fs` | 表格 |
| `tiles` | `items`:[{title,sub,glyph,chip,chipBg,chipInk,accent}], `cols`, `h` | 卡片磁贴 |
| `cards` | `items`:[{title,value,text,status}], `cols`, `h` | 信息卡 |
| `form` | `fields`:[[label,value,hint]], `cols`, `rowh` | 表单（输入框只读展示） |
| `code` | `lang`, `lines`, `title`, `numbers`, `hl`(行号或行号数组), `fs`, `lh` | 代码块（带行号与高亮） |
| `term` | `lines`, `fs`, `lh` | 终端块（`$` 绿 / `@` 蓝 / `#` 黄） |
| `note` | `kind`:info\|warn\|error\|success, `text` | 提示条 |
| `banner` | 同 `note` | 同 `note` |
| `list` | `items`, `ordered` | 列表 |
| `tree` | `items`:[{d:dépth,label,k,open,tag,b}], `rowh` | 树（`k`:folder/file） |
| `toolbar` | `items`:[{label,primary}], `search` | 工具条按钮 |
| `steps` | `items`, `active`, `sub` | 水平步骤条 |
| `metrics` | `items`:[{label,value,color}] | 大数字卡片行 |
| `progress` | `value`, `text` | 进度条 |
| `tabs` | `items`, `active` | 标签页头 |
| `hr` | — | 分隔线 |
| `space` | `h` | 垂直留白 |

## 写作要求（内容质量）

- 画面里的**字段名、按钮名、命令、输出行**必须是真实存在的（查 SAP Help / CAP 文档 / 本地实跑）。
  不确定的名字用 `~` 前缀标记，并在页面正文里说明「名称随版本/区域可能不同」。
- 每个画面 2–4 个 callout：说 **为什么**（「1. 子账户是授权与部署的作用域」），不要说「点这里」。
- 表里的数据用本站示范项目的场景值（图书受注：客户 1000/2000/3000，图书 1001–1005，订单 BO-1001…），
  保证同一张画面之间的数字能对上（数量 × 单价 = 金额；明细之和 = 合计）。
- 画面是**重绘图**：不要在画面里写「截图」「真实画面」，也不要伪造浏览器地址栏的真实域名。
