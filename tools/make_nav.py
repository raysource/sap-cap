#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate the shared header (brand + nav) and footer on every page.

Every page carries the same nav link list with exactly one .active entry, so the
chrome has to be written by one program instead of hand-copied 21 times.  Run this
AFTER any page is added/renamed:

    python3 tools/make_nav.py            # rewrite all pages
    python3 tools/make_nav.py --check    # report drift only (used by the verifier)

The block is replaced between <header class="site">…</header> and
<footer class="site">…</footer>, so it works even on pages that were written by
hand from the template.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (file, label, tooltip)  — order = learning order
NAV = [
    ("index.html", "首页", "课程总览 · 学习路线 · 环境清单"),
    ("concept.html", "概念", "CAP 是什么：模型 · 服务 · UI 三层与两种运行时"),
    ("btp.html", "① BTP 注册", "从试用账号到环境就绪：全局账户 · 子账户 · 权限 · CF 空间"),
    ("bas.html", "② BAS 环境", "Business Application Studio 开发环境与终端"),
    ("hana.html", "③ HANA 云", "SAP HANA Cloud 实例 · HDI 容器 · 数据库浏览器"),
    ("cds.html", "④ CDS 建模", "CDS 语言 · 实体 · 关联 · 注解 · 数据初始化"),
    ("node.html", "⑤ Node 服务", "CAP Node.js：服务定义与事件处理器"),
    ("java.html", "⑥ Java 服务", "CAP Java：Maven 工程 · 事件处理器 · Spring 集成"),
    ("testing.html", "⑦ 测试", "单元测试 · 集成测试 · OData 验证 · CI"),
    ("security.html", "⑧ 权限", "XSUAA · 角色集合 · @requires / @restrict"),
    ("fiori.html", "⑨ Fiori UI", "Fiori Elements 应用 · 注解 · 本地运行"),
    ("deploy.html", "⑩ 部署", "MTA 构建 · cf deploy · 部署后验证 · CI/CD"),
    (None, None, None),
    ("project.html", "示范项目", "端到端可运行示范：模型 → 服务 → 测试 → Fiori → 部署"),
    ("code.html", "源码", "示范项目全部源文件全文（可复制）"),
    ("cli.html", "速查", "cds / cf / btp / mvn / curl 命令与注解速查"),
    ("issues.html", "排错", "常见错误信息 → 原因 → 对策"),
    ("tasks.html", "任务索引", "全部实训任务一览（可筛选）"),
    (None, None, None),
    ("instructor.html", "讲师版", "采分点 · 必问问题 · 参考答案"),
    ("worksheet.html", "学员版", "记入式工作纸（可打印）"),
    ("quiz.html", "自测", "按章节分组的能力测试（合格 75%）"),
    ("glossary.html", "术语表", "中英对照 + 对象速查"),
]


def nav_html(current: str) -> str:
    out = ['<header class="site">', '  <div class="nav-wrap">',
           '    <a class="brand" href="index.html"><span class="logo">CAP</span>'
           '<span class="txt">SAP CAP 培训</span></a>',
           '    <nav class="main">']
    for f, label, tip in NAV:
        if f is None:
            out.append('      <span class="navsep"></span>')
            continue
        cls = ' class="active"' if f == current else ""
        out.append(f'      <a{cls} href="{f}" title="{tip}">{label}</a>')
    out += ['    </nav>', '  </div>', '</header>']
    return "\n".join(out)


FOOTER = """<footer class="site">
  <div class="inner">
    <div class="cols">
      <div>
        <h5>SAP CAP 培训课程</h5>
        <p>从 BTP 注册到部署上线 · Node.js 与 Java 双运行时 · 每节带测试</p>
      </div>
      <div>
        <h5>课程板块</h5>
        <p><a href="concept.html">概念</a> · <a href="btp.html">① BTP 注册</a> ·
        <a href="bas.html">② BAS 环境</a> · <a href="hana.html">③ HANA 云</a> ·
        <a href="cds.html">④ CDS 建模</a> · <a href="node.html">⑤ Node 服务</a> ·
        <a href="java.html">⑥ Java 服务</a></p>
      </div>
      <div>
        <h5>实训与资料</h5>
        <p><a href="project.html">示范项目</a> · <a href="code.html">源码</a> ·
        <a href="cli.html">速查</a> · <a href="issues.html">排错</a> ·
        <a href="tasks.html">任务索引</a> · <a href="glossary.html">术语表</a></p>
      </div>
      <div>
        <h5>课堂配套</h5>
        <p><a href="instructor.html">讲师版</a> · <a href="worksheet.html">学员版</a> ·
        <a href="quiz.html">自测</a></p>
      </div>
      <div>
        <h5>一句话免责</h5>
        <p>页面中的 BTP / BAS / HANA / Fiori 画面为本站<b>高保真重绘图</b>（非实机截图），
        终端输出为本地实际运行结果。标准值与配额随版本/区域而异，请在自己环境中核对。</p>
      </div>
    </div>
    <p class="copy">© <span data-year>2026</span> SAP CAP 培训课程 · 静态站点，可离线使用</p>
  </div>
</footer>"""

HEADER_RE = re.compile(r'<header class="site">.*?</header>', re.S)
FOOTER_RE = re.compile(r'<footer class="site">.*?</footer>', re.S)


def pages(root=ROOT):
    return sorted(f for f in os.listdir(root)
                  if f.endswith(".html") and os.path.isfile(os.path.join(root, f)))


def apply(root=ROOT, check=False) -> int:
    drift = 0
    known = {f for f, _, _ in NAV if f}
    for f in pages(root):
        path = os.path.join(root, f)
        src = open(path, encoding="utf-8").read()
        want_h, want_f = nav_html(f), FOOTER
        new = src
        if HEADER_RE.search(new):
            new = HEADER_RE.sub(lambda _m: want_h, new, count=1)
        else:
            new = new.replace("<body>", "<body>\n" + want_h, 1)
        if FOOTER_RE.search(new):
            new = FOOTER_RE.sub(lambda _m: want_f, new, count=1)
        else:
            marker = '<script src="assets/main.js">'
            if marker in new:
                new = new.replace(marker, want_f + "\n" + marker, 1)
        if new == src:
            continue
        if check:
            print(f"DRIFT {f}")
            drift += 1
        else:
            open(path, "w", encoding="utf-8").write(new)
            print(f"nav  {f}")
    if check:
        print(f"\n{drift} page(s) differ from the generated chrome")
    missing = [f for f in known if f not in pages(root)]
    if missing:
        print(f"WARN nav links to missing pages: {', '.join(missing)}")
    return 1 if (drift or missing) else 0


if __name__ == "__main__":
    sys.exit(apply(check="--check" in sys.argv[1:]))
