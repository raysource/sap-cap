#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble quiz.html from the per-page fragments in work/quiz/*.json.

    python3 tools/build_quiz.py

Each page author writes work/quiz/<page>.json (a JSON array of question objects).
This script merges them in course order, writes quiz.html (grouped by chapter, with
anchors `#q-<page>` that the pages' 「本节测试」 blocks link to) and prints counts.

Question object:
  {"tag": "概念|操作|排错|最佳实践", "q": "题干",
   "opts": {"A": "...", "B": "...", "C": "...", "D": "..."},
   "answer": "B", "explain": "解说"}
"""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QDIR = os.path.join(ROOT, "work", "quiz")

# page -> (章节标题, 页面链接)
CHAPTERS = [
    ("concept", "概念：CAP 是什么", "concept.html"),
    ("btp", "① 从 BTP 注册到环境就绪", "btp.html"),
    ("bas", "② BAS 开发环境", "bas.html"),
    ("hana", "③ SAP HANA Cloud 与 HDI 容器", "hana.html"),
    ("cds", "④ CDS 建模", "cds.html"),
    ("node", "⑤ CAP Node.js 服务实现", "node.html"),
    ("java", "⑥ CAP Java 服务实现", "java.html"),
    ("testing", "⑦ 测试体系", "testing.html"),
    ("security", "⑧ 认证与授权", "security.html"),
    ("fiori", "⑨ Fiori UI", "fiori.html"),
    ("deploy", "⑩ 构建与部署", "deploy.html"),
    ("project", "示范项目（端到端）", "project.html"),
]

HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>能力自测 · SAP CAP 培训课程</title>
<meta name="description" content="SAP CAP 培训课程自测：按 11 个板块分组的能力测试，点击选项即时判分并显示解说，合格线 75%。">
<link rel="stylesheet" href="assets/style.css">
<link rel="stylesheet" href="assets/cap.css">
</head>
<body>
<!--NAV-->
<header class="site"><div class="nav-wrap"><a class="brand" href="index.html"><span class="logo">CAP</span><span class="txt">SAP CAP 培训</span></a><nav class="main"><a class="active" href="quiz.html">自测</a></nav></div></header>
<!--/NAV-->

<div class="wrap">
<main class="page">
<article>
<p class="breadcrumb"><a href="index.html">首页</a> / <span>能力自测</span></p>
<h1>能力自测：{total} 题，按板块分组</h1>
<p class="kicker">点击选项即判分并显示解说 · 合格线 75% · 全部题目来自正文的「本节测试」</p>

<div class="box info"><b class="t">怎么用</b>
<ul>
  <li>每题点击一个选项就会立刻判分并展开解说 —— <b>答错不要紧，看解说知道为什么错才是目的</b>。</li>
  <li>页面顶部的成绩条按<b>全部题目</b>统计；右上「全部重做」可清空重来。</li>
  <li>合格标准：正确率 ≥ 75%，且<a href="tasks.html">任务索引</a>里自己负责的任务全部达到完成基准。</li>
  <li>按板块复习：每道题都标了板块标签，答错就回到对应页面重读那一节。</li>
</ul></div>

<div class="toc">
{chips}
</div>
"""


def qhtml(n, q, chapter):
    opts = "".join(
        f'      <div class="opt" data-key="{k}">{k}. {html.escape(v)}</div>\n'
        for k, v in sorted(q["opts"].items()))
    return (f'<div class="quiz-q" data-answer="{q["answer"]}">\n'
            f'  <div class="q-meta"><span class="tag gray">{html.escape(q.get("tag", "概念"))}</span>'
            f'<span class="tag">{html.escape(chapter)}</span></div>\n'
            f'  <h4>{n}. {html.escape(q["q"])}</h4>\n'
            f'  <div class="opts">\n{opts}  </div>\n'
            f'  <div class="explain">{html.escape(q.get("explain", ""))}</div>\n'
            f'</div>\n')


def main():
    total = 0
    body, chips, missing, problems = [], [], [], []
    for key, title, page in CHAPTERS:
        path = os.path.join(QDIR, key + ".json")
        if not os.path.exists(path):
            missing.append(key)
            continue
        try:
            qs = json.load(open(path, encoding="utf-8"))
        except json.JSONDecodeError as e:
            problems.append(f"{key}: invalid JSON ({e})")
            continue
        if not isinstance(qs, list) or not qs:
            problems.append(f"{key}: not a non-empty list")
            continue
        chips.append(f'<a href="#q-{key}">{title}（{len(qs)} 题）</a>')
        body.append(f'<h2 id="q-{key}">{title} <a class="tag" href="{page}">回到本页</a></h2>')
        for q in qs:
            total += 1
            body.append(qhtml(total, q, title.split("：")[0].split(" ")[-1]))
    out = HEAD.replace("{total}", str(total)).replace("{chips}", "\n".join(chips))
    out += "\n".join(body)
    out += """
<div class="sectest">
  <b class="t">合格判定</b>
  <ol>
    <li>正确率 ≥ 75%（页面顶部成绩条）。</li>
    <li><a href="tasks.html">任务索引</a>中分配给你的任务全部达到「完成基准」。</li>
    <li>能不用查资料复述：CAP 三层结构、请求生命周期、Node/Java 的差异、草稿流程、部署链路。</li>
  </ol>
  <p class="go">未达标就回到对应板块重做手顺 —— 每个板块末尾的「本节测试」与这里的题目一一对应。</p>
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
    open(os.path.join(ROOT, "quiz.html"), "w", encoding="utf-8").write(out)
    print(f"quiz.html written: {total} questions from {len(CHAPTERS) - len(missing)} chapters")
    if missing:
        print(f"MISSING fragments: {', '.join(missing)}")
    for p in problems:
        print("PROBLEM " + p)
    return 1 if (missing or problems) else 0


if __name__ == "__main__":
    sys.exit(main())
