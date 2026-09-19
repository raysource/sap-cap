#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble tasks.html (可筛选的任务索引) from work/tasks/*.json.

    python3 tools/build_tasks.py

Each page author writes work/tasks/<page>.json: a JSON array of
  {"no": "BTP-01", "title": "...", "basis": "完成基准（可观察）", "time": "10 分", "rel": "btp.html#s2"}
The page ships a client-side filter (板块 / 关键字) over the merged table.
"""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TDIR = os.path.join(ROOT, "work", "tasks")

ORDER = [
    ("btp", "① BTP 注册", "btp.html"),
    ("bas", "② BAS 环境", "bas.html"),
    ("hana", "③ HANA 云", "hana.html"),
    ("cds", "④ CDS 建模", "cds.html"),
    ("node", "⑤ Node 服务", "node.html"),
    ("java", "⑥ Java 服务", "java.html"),
    ("testing", "⑦ 测试", "testing.html"),
    ("security", "⑧ 权限", "security.html"),
    ("fiori", "⑨ Fiori UI", "fiori.html"),
    ("deploy", "⑩ 部署", "deploy.html"),
    ("concept", "概念（理解型）", "concept.html"),
    ("project", "示范项目", "project.html"),
]


def cell(x):
    """HTML-escape a table cell and neutralise pipes (they break the <td> check)."""
    return html.escape(str(x)).replace("|", "／")


def main():
    rows, missing = [], []
    for key, label, page in ORDER:
        path = os.path.join(TDIR, key + ".json")
        if not os.path.exists(path):
            missing.append(key)
            continue
        for t in json.load(open(path, encoding="utf-8")):
            rows.append(dict(t, chapter=label, page=page))

    total_min = 0
    body = []
    for r in rows:
        try:
            total_min += int("".join(ch for ch in str(r.get("time", "0")) if ch.isdigit()) or 0)
        except ValueError:
            pass
        rel = r.get("rel") or ("%s" % r["page"])
        body.append(
            '    <tr data-c="%s">\n'
            '      <td><code>%s</code></td>\n'
            '      <td>%s</td>\n'
            '      <td>%s</td>\n'
            '      <td>%s</td>\n'
            '      <td>%s</td>\n'
            '      <td><a href="%s">%s</a></td>\n'
            '    </tr>' % (
                cell(r["chapter"]),
                cell(r["chapter"]),
                cell(r.get("no", "")),
                cell(r.get("title", "")),
                cell(r.get("basis", "")),
                cell(r.get("time", "")),
                html.escape(rel), html.escape(r["chapter"])))

    chapters = sorted({r["chapter"] for r in rows})
    chips = "".join(f'<button class="copy-btn" data-f="{html.escape(c)}" style="margin:2px">{html.escape(c)}</button>'
                    for c in chapters)
    out = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>任务索引 · SAP CAP 培训课程</title>
<meta name="description" content="SAP CAP 培训课程的全部实训任务索引：{len(rows)} 个任务，含完成基准、预计时间与所在页面，可按板块筛选。">
<link rel="stylesheet" href="assets/style.css">
<link rel="stylesheet" href="assets/cap.css">
</head>
<body>
<!--NAV-->
<header class="site"><div class="nav-wrap"><a class="brand" href="index.html"><span class="logo">CAP</span><span class="txt">SAP CAP 培训</span></a><nav class="main"><a class="active" href="tasks.html">任务索引</a></nav></div></header>
<!--/NAV-->

<div class="wrap">
<main class="page">
<article>
<p class="breadcrumb"><a href="index.html">首页</a> / <span>任务索引</span></p>
<h1>任务索引：{len(rows)} 个实训任务</h1>
<p class="kicker">每条任务都有可观察的「完成基准」 · 合计约 {total_min // 60} 小时 {total_min % 60} 分 · 可按板块筛选或搜索</p>

<div class="box info"><b class="t">怎么用</b>
<ul>
  <li>讲师可以按板块把任务分配给学员；学员用「完成基准」自检，做不出来就回到对应页面重做手顺。</li>
  <li>预计时间是<b>自己动手做</b>的估算（含排查），只看不做的复习约为 1/3。</li>
  <li>顺序建议：① BTP → ② BAS → ③ HANA → ④ CDS → ⑤ Node → ⑦ 测试 → ⑧ 权限 → ⑨ Fiori → ⑩ 部署（⑥ Java 与 ⑤ 可互换）。</li>
</ul></div>

<p><input id="q" type="search" placeholder="搜索任务号 / 关键字（例如：草稿、HANA、409）"
   style="width:100%;max-width:420px;padding:8px 12px;border:1px solid var(--line);border-radius:8px">
   <span id="cnt" style="font-size:13px;color:var(--muted);margin-left:8px"></span></p>
<p>{chips}<button class="copy-btn" data-f="" style="margin:2px;background:#0f2438">全部</button></p>

<div class="tblwrap"><table class="tbl small" id="tasks">
<thead><tr><th>板块</th><th>任务号</th><th>任务</th><th>完成基准（可观察）</th><th>预计</th><th>页面</th></tr></thead>
<tbody>
{chr(10).join(body)}
</tbody></table></div>

<div class="sectest">
  <b class="t">验收建议</b>
  <ol>
    <li>挑 3 个任务让学员现场做给讲师看，以「完成基准」逐条判定。</li>
    <li>课程结束前必须完成：CDS 建模、Node 服务、测试、Fiori、部署 五个板块的全部任务。</li>
    <li>Java 板块至少完成「跑通同一个模型」与「写一个事件处理器」两项。</li>
  </ol>
  <p class="go">配套自测见 <a href="quiz.html">自测页</a>；任务对应的手顺在各板块页面内。</p>
</div>
</article>
</main>
</div>

<!--FOOTER-->
<footer class="site"><div class="inner"><p class="copy">© <span data-year>2026</span> SAP CAP 培训课程</p></div></footer>
<!--/FOOTER-->
<script src="assets/main.js"></script>
<script src="assets/quiz.js"></script>
<script>
(function () {{
  var rows = [].slice.call(document.querySelectorAll('#tasks tbody tr'));
  var q = document.getElementById('q'), cnt = document.getElementById('cnt');
  var chapter = '';
  function apply() {{
    var kw = (q.value || '').trim().toLowerCase(), n = 0;
    rows.forEach(function (tr) {{
      var okC = !chapter || tr.getAttribute('data-c') === chapter;
      var okK = !kw || tr.innerText.toLowerCase().indexOf(kw) >= 0;
      var show = okC && okK;
      tr.style.display = show ? '' : 'none';
      if (show) n++;
    }});
    cnt.textContent = '显示 ' + n + ' / ' + rows.length + ' 条';
  }}
  document.addEventListener('click', function (e) {{
    var b = e.target.closest('[data-f]');
    if (!b) return;
    chapter = b.getAttribute('data-f');
    apply();
  }});
  q.addEventListener('input', apply);
  apply();
}})();
</script>
</body>
</html>
"""
    open(os.path.join(ROOT, "tasks.html"), "w", encoding="utf-8").write(out)
    print(f"tasks.html written: {len(rows)} tasks, ~{total_min} min")
    if missing:
        print(f"MISSING fragments: {', '.join(missing)}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
