#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate CAP培训_手顺书_学习WBS.xlsx from the site's own data.

    python3 tools/make_cap_xlsx.py

Sheets
  1_课程总览      课程地图与学习路线（含完成判据）
  2_手顺书        全部任务：板块 / 任务号 / 任务 / 完成基准 / 预计 / 所在页面
  3_学習WBS       2_手顺书 + 自己判定（○/△/× 下拉）+ 备注，供学员当进度表
  4_环境清单      组件 / 要求 / 本机实测版本 / 说明
  5_实测证据      环节 / 命令 / 实测结果
  6_交付物        目录 / 内容 / 本机状态

Data sources: work/tasks/*.json (per-page task fragments) + the constants below.
"""
import glob
import html
import json
import os
import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "CAP培训_手顺书_学习WBS.xlsx")

ORDER = [("btp", "① BTP 注册", "btp.html"), ("bas", "② BAS 环境", "bas.html"),
         ("hana", "③ HANA 云", "hana.html"), ("cds", "④ CDS 建模", "cds.html"),
         ("node", "⑤ Node 服务", "node.html"), ("java", "⑥ Java 服务", "java.html"),
         ("testing", "⑦ 测试", "testing.html"), ("security", "⑧ 权限", "security.html"),
         ("fiori", "⑨ Fiori UI", "fiori.html"), ("deploy", "⑩ 部署", "deploy.html"),
         ("concept", "概念（理解型）", "concept.html"), ("project", "示范项目", "project.html")]

OVERVIEW = [
    ("0 准备", "注册 BTP 试用、创建子账户与 CF 空间、装 cf/btp CLI", "btp.html", "90 分", "cf target 输出正确的 org / space"),
    ("1 环境", "Dev Space、项目脚手架、HANA 实例", "bas.html · hana.html", "120 分", "cds watch 起得来；实例状态 Created"),
    ("2 建模", "领域模型、关联、视图、种子数据", "cds.html", "150 分", "cds deploy 后 sqlite 里有表且有数据"),
    ("3 服务", "服务定义、事件处理器、业务规则", "node.html", "240 分", "curl 能查到数据、能触发规则"),
    ("3' 服务(Java)", "同一套模型的 Java 实现", "java.html", "180 分", "mvn compile 成功、$metadata 200"),
    ("4 测试", "单元测试 + OData 集成测试", "testing.html", "120 分", "odata-verify.sh 全绿"),
    ("5 权限", "认证、角色集合、授权注解", "security.html", "90 分", "匿名 401、授权用户 200"),
    ("6 界面", "Fiori Elements 注解与本地运行", "fiori.html", "150 分", "浏览器里能列出订单并进明细页"),
    ("7 部署", "MTA 构建、cf deploy、部署后验证", "deploy.html", "120 分", "路由上 curl $metadata 返回 200"),
    ("综合", "端到端示范项目（含作业改造）", "project.html", "180 分", "项目验收清单全部勾上"),
]

ENVIRONMENT = [
    ("Node.js", "20 LTS 或 22 LTS", "v22.23.2", "必须 LTS：better-sqlite3 原生模块要匹配 ABI"),
    ("@sap/cds", "9.x", "9.9.3", "与 cds-dk 同大版本"),
    ("@sap/cds-dk", "9.x", "9.x（devDependency）", "提供 cds CLI；cds-dk 10 要求 cds ≥ 9"),
    ("@cap-js/sqlite", "2.x", "2.x（SQLite 3.53.2）", "本地数据库，零配置"),
    ("JDK", "17 或 21", "OpenJDK 21.0.12.1", "只有 Java 板块需要"),
    ("Maven", "3.9+", "3.9.16", "CAP Java 构建"),
    ("SAPUI5（Fiori）", "带 sap.fe.* 的版本", "1.136.0（ui5.sap.com）", "sap.fe 不在 OpenUI5 里，必须用 SAPUI5 CDN 或本地部署"),
    ("浏览器", "Chrome / Edge 最新", "Google Chrome", "调试 $metadata 与 Fiori 必备"),
    ("BTP 试用账号", "1 个（可选）", "未开通（未实测云端部分）", "无账号也能完成 ④–⑦ 全部内容"),
]

EVIDENCE = [
    ("安装", "npm install（Node 22）", "328 packages；better-sqlite3 原生模块可用（SQLite 3.53.2）"),
    ("建库", "npm run deploy", "6 张表；Books 5 / Customers 3 / BookOrders 4 / BookOrderItems 9 行"),
    ("启动", "npm start", "server listening on http://localhost:4004；服务挂载 /odata/v4/book-order"),
    ("OData 验收", "bash test/odata-verify.sh", "PASS 26 / FAIL 0（含匿名 401、草稿 409/400、状态迁移 409）"),
    ("Fiori", "cds watch + node test/dev-proxy.js + tools/shot.js", "List Report 渲染成功（assets/fig/real/fiori_list_report.png）"),
    ("Java 编译", "mvn -DskipTests compile", "BUILD SUCCESS（71 个源文件，cds.gen 已生成）"),
    ("Java 运行", "mvn spring-boot:run", "服务启动、CSV 灌入 H2、handler 挂载；$metadata 200"),
    ("Java 认证", "curl -u alice:alice …/BookOrders", "⚠ 401 —— 本地 mock 用户配置未解决（见 java.html §10）"),
]

DELIVERABLES = [
    ("index.html …（20 页）", "课程页面：概念 + ①–⑩ 板块 + 示范项目 + 源码/速查/排错/索引/讲师/学员/自测/术语", "已生成，check_page 全绿（cli.html 缺失时除外）"),
    ("assets/fig/*.svg", "92 张高保真重绘画面（BTP / BAS / HANA / Fiori / CF CLI）", "92/92 由 figkit 渲染成功；抽样 12 张用 Chrome 栅格化验证非空白"),
    ("assets/fig/real/fiori_list_report.png", "本机真实运行的 Fiori Elements List Report 截图", "已用视觉核对：4 张订单 + 状态着色 + 行内动作按钮"),
    ("project-code/demo-node/", "可运行的 CAP Node.js 示范项目（模型 / 服务 / 规则 / Fiori / 验收脚本 / MTA）", "实测通过（26/26 断言）"),
    ("project-code/demo-java/", "同一套 CDS 模型的 Java 实现", "编译与启动通过；认证相关验证未通过"),
    ("work/evidence/*.txt", "全部真实运行的原始输出（8 个文件）", "见 5_实测证据"),
    ("quiz.html / tasks.html / code.html", "自测 196 题 / 任务 119 条 / 源码全文 75 文件 8886 行", "由 tools/build_*.py 从片段与磁盘文件生成"),
]


def load_tasks():
    rows = []
    for key, label, page in ORDER:
        p = os.path.join(ROOT, "work", "tasks", key + ".json")
        if not os.path.exists(p):
            continue
        for t in json.load(open(p, encoding="utf-8")):
            rows.append((label, t.get("no", ""), t.get("title", ""), t.get("basis", ""),
                         t.get("time", ""), t.get("rel", page)))
    return rows


HEAD_FILL = PatternFill("solid", fgColor="0A6ED1")
HEAD_FONT = Font(color="FFFFFF", bold=True, size=11)
THIN = Side(style="thin", color="D9E1E8")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def sheet(wb, title, headers, rows, widths, freeze="A2", wrap_cols=()):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill, cell.font = HEAD_FILL, HEAD_FONT
        cell.alignment = Alignment(vertical="center", horizontal="left")
        ws.column_dimensions[get_column_letter(c)].width = widths[c - 1]
    for r in rows:
        ws.append(list(r))
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=len(headers)):
        for cell in row:
            cell.border = BORDER
            cell.alignment = Alignment(vertical="top",
                                       wrap_text=(cell.column in wrap_cols or not wrap_cols))
    if freeze:
        ws.freeze_panes = freeze
    return ws


def main():
    wb = Workbook()
    wb.remove(wb.active)

    sheet(wb, "1_课程总览", ["阶段", "内容", "对应页面", "预计", "完成判据"], OVERVIEW,
          [12, 46, 22, 10, 44])
    tasks = load_tasks()
    sheet(wb, "2_手顺书", ["板块", "任务号", "任务", "完成基准（可观察）", "预计", "所在页面"],
          tasks, [16, 12, 50, 58, 10, 16])
    wbs = sheet(wb, "3_学習WBS",
                ["板块", "任务号", "任务", "完成基准（可观察）", "预计", "自己判定", "备注"],
                [list(t) + ["", ""] for t in tasks], [16, 12, 44, 52, 10, 12, 24])
    dv = DataValidation(type="list", formula1='"○,△,×"', allow_blank=True)
    wbs.add_data_validation(dv)
    dv.add(f"F2:F{max(wbs.max_row, 2)}")
    sheet(wb, "4_环境清单", ["组件", "要求", "本机实测版本", "说明"], ENVIRONMENT, [18, 22, 30, 56])
    sheet(wb, "5_实测证据", ["环节", "命令", "实测结果"], EVIDENCE, [14, 46, 74])
    sheet(wb, "6_交付物", ["交付物", "内容", "本机状态"], DELIVERABLES, [34, 62, 46])
    wb.save(OUT)
    print(f"written: {OUT}")
    print(f"  sheets: 1_课程总览 / 2_手顺书({len(tasks)}) / 3_学習WBS({len(tasks)}) / "
          f"4_环境清单 / 5_实测证据 / 6_交付物")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
