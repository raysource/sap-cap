#!/usr/bin/env bash
# 把 sap-cap（SAP CAP 培训课程站）作为独立仓库发布 / 同步到 GitHub。
#   https://github.com/raysource/sap-cap （public）
#
#   bash tools/publish_to_github.sh            # init（若无）+ remote + commit + push（可反复执行）
#   bash tools/publish_to_github.sh "提交信息"  # 指定本次提交信息
#
# 注意：本脚本在 sap-cap/ 下建 .git，因此父仓库（raysource/sap-consult）看到的是
#       「嵌套仓库」—— 父仓库里 `git add sap-cap/...` 会**静默无效**，必须用
#       `bash ../tools/include_nested_repo_files.sh "$PWD/.." sap-cap` 按 blob 折叠进去
#       （sap_sd_cn / sap_cn / sap_jp_sd 同做法）。
set -euo pipefail
cd "$(dirname "$0")/.."
R="raysource/sap-cap"
BR=main

if [ ! -d .git ]; then
  git init -q -b "$BR"
fi
# 只设本仓库的 identity（不动全局配置）
git config user.name  "$(git config user.name  || echo Jason)"
git config user.email "$(git config user.email || echo jason@localhost)"

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "https://github.com/$R.git"
else
  git remote add origin "https://github.com/$R.git"
fi

git add -A
if git diff --cached --quiet; then
  echo "没有需要提交的变更"
else
  git -c core.quotepath=false status --short | sed 's#^#  #' | head -20
  echo "  … 合计 $(git diff --cached --name-only | wc -l | tr -d ' ') 个文件"
  git commit -q -m "${1:-sap-cap: 同步课程站内容}"
fi

git push -u origin "$BR"
echo "---"
echo "local HEAD : $(git rev-parse HEAD)"
echo "remote main: $(git ls-remote origin -h "refs/heads/$BR" | cut -f1)"
echo "--- 远端与工作树逐路径对账 ---"
bash "$HOME/.hermes/skills/productivity/sap-training-sites/scripts/reconcile_published_repo.sh" "$PWD" "$R" "$BR" | tail -12
