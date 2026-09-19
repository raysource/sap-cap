#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate code.html — every source file of the demo projects, verbatim.

    python3 tools/build_code.py

Sources come from project-code/{demo-node,demo-java}/ on disk, so the page can never
drift from the shipped code. Files are grouped by project, ordered for reading, and
each one is emitted as a copy-able <pre class="hl"> block with its own anchor
(#f-<n>) so other pages can deep-link.
"""
import html
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECTS = [
    ("demo-node", "① Node.js 运行时（本机实测通过）",
     "整套规则在本机跑通：建库 → 启动 → 26 条 OData 断言全绿 → Fiori 界面可见。"),
    ("demo-java", "② Java 运行时（同一套 .cds 模型）",
     "把 db/ 与 srv/*.cds 原样搬过来，业务逻辑换成 Java 事件处理器 —— CAP「模型与运行时解耦」的直接证据。"),
]

SKIP_DIRS = {"node_modules", "target", "gen", ".git", "db.sqlite", "dist", ".mta"}
SKIP_FILES = {"package-lock.json", "db.sqlite", ".DS_Store", "localService"}

READ_ORDER = [
    "README.md", "package.json", "pom.xml", "mta.yaml", "xs-security.json", ".cdsrc.json",
    "schema.cds", "book-order-service.cds", "book-order-service.js", "annotations.cds",
    "manifest.json", "index.html", "Component.js", "application.yaml",
    "odata-verify.sh", "dev-proxy.js", "xs-app.json",
]

LANG = {
    ".cds": "cds", ".js": "js", ".java": "java", ".json": "json", ".yaml": "yaml",
    ".yml": "yaml", ".xml": "xml", ".html": "xml", ".sh": "bash", ".md": "text",
    ".properties": "text", ".sql": "sql", ".csv": "text", ".gitignore": "text",
}


def collect(project):
    base = os.path.join(ROOT, "project-code", project)
    files = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f in SKIP_FILES or f.startswith("."):
                if f != ".cdsrc.json":
                    continue
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, base)
            files.append((rel, full))

    def sort_key(item):
        rel = item[0]
        name = os.path.basename(rel)
        try:
            return (READ_ORDER.index(name), rel)
        except ValueError:
            return (len(READ_ORDER), rel)

    return sorted(files, key=sort_key)


def main():
    total_files = 0
    total_lines = 0
    blocks, sections = [], []
    anchor = 0
    for project, title, blurb in PROJECTS:
        files = collect(project)
        tree_lines = [rel for rel, _ in sorted(files, key=lambda i: i[0])]
        sections.append(f'<h2 id="p-{project}">{title}</h2>\n<p>{blurb}</p>\n'
                        f'<div class="file-tree">project-code/{project}/\n' +
                        "\n".join(f"├── {ln.strip()}" for ln in tree_lines) + '</div>')
        for rel, full in files:
            anchor += 1
            lang = LANG.get(os.path.splitext(rel)[1], "text")
            src = open(full, encoding="utf-8", errors="replace").read()
            lines = src.count("\n") + 1
            total_files += 1
            total_lines += lines
            sections.append(
                f'<h3 id="f-{anchor}">'
                f'<a href="code.html#f-{anchor}">#f-{anchor}</a> '
                f'<code>project-code/{project}/{rel}</code> '
                f'<span class="tag gray">{lines} 行</span></h3>\n'
                f'<pre class="hl"><div class="code-head"><span class="lang">{lang}</span>'
                f'<button class="copy-btn" type="button">复制</button></div>'
                f'<code class="lang-{lang}">{html.escape(src)}</code></pre>')

    out = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>示范项目源码 · SAP CAP 培训课程</title>
<meta name="description" content="SAP CAP 培训示范项目的全部源码：Node.js 版与 Java 版（同一套 CDS 模型）、Fiori Elements 应用、验收脚本、MTA 部署描述，逐文件全文可复制。">
<link rel="stylesheet" href="assets/style.css">
<link rel="stylesheet" href="assets/cap.css">
</head>
<body>
<!--NAV-->
<header class="site"><div class="nav-wrap"><a class="brand" href="index.html"><span class="logo">CAP</span><span class="txt">SAP CAP 培训</span></a><nav class="main"><a class="active" href="code.html">源码</a></nav></div></header>
<!--/NAV-->

<div class="wrap">
<main class="page">
<article>
<p class="breadcrumb"><a href="index.html">首页</a> / <span>示范项目源码</span></p>
<h1>示范项目源码：{total_files} 个文件 / {total_lines} 行</h1>
<p class="kicker">全部内容按磁盘上的实际文件生成（本页由 tools/build_code.py 生成，不会与代码脱节）</p>

<div class="box info"><b class="t">怎么用这些代码</b>
<ul>
  <li>本页是<b>阅读用</b>的全文视图；要真跑起来，请把 <code>project-code/</code> 目录整体复制到工作区，
      按 <a href="project.html">示范项目</a> 的手顺执行 <code>npm install</code> → <code>npm run deploy</code> → <code>npm start</code>。</li>
  <li>每个文件右上角有「复制」按钮；代码块下方的 <code>#f-N</code> 是稳定锚点，可以在教材里直接引用。</li>
  <li>Node 版与 Java 版共享同一份 <code>db/schema.cds</code> 与 <code>srv/book-order-service.cds</code> ——
      对照读两份 <code>book-order-service.js</code> / <code>BookOrderServiceHandler.java</code> 是理解两种运行时最快的方式。</li>
</ul></div>

<div class="toc">
  <a href="#p-demo-node">① Node.js 版</a><a href="#p-demo-java">② Java 版</a>
  <a href="project.html">示范项目手顺</a><a href="cli.html">命令速查</a>
</div>

{chr(10).join(sections)}

<div class="sectest">
  <b class="t">读源码的三个练习</b>
  <ol>
    <li>在 <code>book-order-service.js</code> 里找出「金额 = 单价 × 数量」的实现，说明为什么放在 before 而不是 after。</li>
    <li>对照 Java 版的 <code>beforeBookOrderItems</code>，写出两者在类型安全上的差别各带来什么好处与成本。</li>
    <li>找出「删除明细后重算订单合计」的代码：Node 与 Java 各自怎么拿到被删行的父订单号？为什么不能直接用结果集？</li>
  </ol>
  <p class="go">参考答案见 <a href="instructor.html">讲师版</a>。</p>
</div>
</article>
</main>
</div>

<!--FOOTER-->
<footer class="site"><div class="inner"><p class="copy">© <span data-year>2026</span> SAP CAP 培训课程</p></div></footer>
<!--/FOOTER-->
<script src="assets/main.js"></script>
<script src="assets/quiz.js"></script>
</body>
</html>
"""
    open(os.path.join(ROOT, "code.html"), "w", encoding="utf-8").write(out)
    print(f"code.html written: {total_files} files / {total_lines} lines / "
          f"{os.path.getsize(os.path.join(ROOT, 'code.html')) // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
