#!/usr/bin/env bash
# 图书受注管理 —— OData 验收脚本（本地实测用）
#
#   bash test/odata-verify.sh                        # 假定服务已在 localhost:4004 运行
#   BASE=http://localhost:4004 bash test/odata-verify.sh
#
# 每个用例都打印「期望 → 实际」，最后给出通过数。这是课件里「每节都有测试」
# 中『集成测试』一节可以直接复制给学生运行的脚本。
set -u
BASE="${BASE:-http://localhost:4004}"
SVC="$BASE/odata/v4/book-order"
AUTH=( -u alice:alice )
PASS=0; FAIL=0

code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
body() { curl -s "$@"; }

chk() {                       # chk "<用例>" <期望> <实际>
  local name="$1" want="$2" got="$3"
  if [ "$want" = "$got" ]; then PASS=$((PASS+1)); printf '  PASS  %-58s %s\n' "$name" "$got"
  else FAIL=$((FAIL+1)); printf '  FAIL  %-58s want=%s got=%s\n' "$name" "$want" "$got"; fi
}

echo "== 1. 服务可达性与认证 =="
chk 'GET $metadata (alice)'            200 "$(code "${AUTH[@]}" "$SVC/\$metadata")"
chk 'GET /BookOrders 匿名 → 401'        401 "$(code "$SVC/BookOrders")"
chk 'GET /BookOrders (bob)'            200 "$(code -u bob:bob "$SVC/BookOrders")"
# mocked 认证会接受任意用户名/口令（它不是真正的认证，只是开发期模拟）——因此这里期望 200
chk 'GET /BookOrders 任意用户(mocked 放行)' 200 "$(code -u nosuch:wrong "$SVC/BookOrders")"

echo "== 2. 读：过滤 / 展开 / 只读视图 =="
chk 'GET BookOrders?$filter=status eq OPEN → 2 张' 2 \
    "$(body "${AUTH[@]}" "$SVC/BookOrders?\$filter=status%20eq%20'OPEN'" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)["value"]))')"
chk 'GET BookOrders 带 $expand=items 行数'        3 \
    "$(body "${AUTH[@]}" "$SVC/BookOrders?\$filter=orderNo%20eq%20'BO-1001'&\$expand=items" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)["value"][0]["items"]))')"
chk 'GET OrderItemView (带主键视图，可暴露)'      9 \
    "$(body "${AUTH[@]}" "$SVC/OrderItemView" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)["value"]))')"
chk 'GET OrderItemView 含关联展开的列名'  BO-1001 \
    "$(body "${AUTH[@]}" "$SVC/OrderItemView?\$orderby=ID&\$top=1" | python3 -c 'import sys,json;print(json.load(sys.stdin)["value"][0]["orderNo"])')"

echo "== 3. 函数（无绑定）：聚合走函数而不是实体 =="
chk 'getOrderTotal(BO-1003) = 17400'   17400 "$(body "${AUTH[@]}" "$SVC/getOrderTotal(orderNo='BO-1003')" | python3 -c 'import sys,json;print(json.load(sys.stdin)["value"])')"
chk 'getOrderTotal(不存在) → 404'         404 "$(code "${AUTH[@]}" "$SVC/getOrderTotal(orderNo='BO-9999')")"
chk 'getOrderSummary() 4 行'             4 \
    "$(body "${AUTH[@]}" "$SVC/getOrderSummary()" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)["value"]))')"
chk 'getOrderSummary() BO-1001 合计'     16000 \
    "$(body "${AUTH[@]}" "$SVC/getOrderSummary()" | python3 -c 'import sys,json;print([r["totalAmount"] for r in json.load(sys.stdin)["value"] if r["orderNo"]=="BO-1001"][0])')"

echo "== 4. 写：派生字段与汇总回写 =="
BO1002_ID="$(body "${AUTH[@]}" "$SVC/BookOrders?\$select=ID&\$filter=orderNo%20eq%20'BO-1002'" | python3 -c 'import sys,json;print(json.load(sys.stdin)["value"][0]["ID"])')"
NEW="$(body "${AUTH[@]}" -X POST "$SVC/BookOrderItems" -H 'Content-Type: application/json' \
       -d "{\"order_ID\":\"$BO1002_ID\",\"book_ID\":1003,\"quantity\":3}")"
chk 'POST 明细：金额自动计算 = 2800×3'   8400 "$(echo "$NEW" | python3 -c 'import sys,json;print(json.load(sys.stdin)["amount"])')"
chk 'POST 明细后父订单合计被回写 = 12000' 12000 \
    "$(body "${AUTH[@]}" "$SVC/BookOrders?\$select=totalAmount&\$filter=orderNo%20eq%20'BO-1002'" | python3 -c 'import sys,json;print(json.load(sys.stdin)["value"][0]["totalAmount"])')"

echo "== 5. 负向：业务校验必须返回 4xx 且带消息 =="
chk 'POST 数量 0 → 400'    400 "$(code "${AUTH[@]}" -X POST "$SVC/BookOrderItems" -H 'Content-Type: application/json' -d "{\"order_ID\":\"$BO1002_ID\",\"book_ID\":1003,\"quantity\":0}")"
chk 'POST 图书不存在 → 400' 400 "$(code "${AUTH[@]}" -X POST "$SVC/BookOrderItems" -H 'Content-Type: application/json' -d "{\"order_ID\":\"$BO1002_ID\",\"book_ID\":9999,\"quantity\":1}")"
chk '只读实体 POST → 405'   405 "$(code "${AUTH[@]}" -X POST "$SVC/OrderItemView" -H 'Content-Type: application/json' -d '{}')"

echo "== 6. 草稿（@odata.draft.enabled）创建与激活 =="
DRAFT="$(body "${AUTH[@]}" -X POST "$SVC/BookOrders" -H 'Content-Type: application/json' -d '{"orderNo":"BO-1001","customer_ID":1000}')"
DID="$(echo "$DRAFT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["ID"])')"
chk 'POST 新建订单 → 草稿未激活'  False "$(echo "$DRAFT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["IsActiveEntity"])')"
chk '重复订单号激活 → 409'      409 "$(code "${AUTH[@]}" -X POST "$SVC/BookOrders(ID=$DID,IsActiveEntity=false)/BookOrderService.draftActivate" -H 'Content-Type: application/json' -d '{}')"
D2="$(body "${AUTH[@]}" -X POST "$SVC/BookOrders" -H 'Content-Type: application/json' -d '{"customer_ID":9999}')"
D2ID="$(echo "$D2" | python3 -c 'import sys,json;print(json.load(sys.stdin)["ID"])')"
chk '顾客不存在激活 → 400'      400 "$(code "${AUTH[@]}" -X POST "$SVC/BookOrders(ID=$D2ID,IsActiveEntity=false)/BookOrderService.draftActivate" -H 'Content-Type: application/json' -d '{}')"
D3="$(body "${AUTH[@]}" -X POST "$SVC/BookOrders" -H 'Content-Type: application/json' -d '{"customer_ID":1000}')"
D3ID="$(echo "$D3" | python3 -c 'import sys,json;print(json.load(sys.stdin)["ID"])')"
chk '正常激活 → 201 并自动编号'  201 "$(code "${AUTH[@]}" -X POST "$SVC/BookOrders(ID=$D3ID,IsActiveEntity=false)/BookOrderService.draftActivate" -H 'Content-Type: application/json' -d '{}')"
chk '自动编号 = BO-1005'         BO-1005 \
    "$(body "${AUTH[@]}" "$SVC/BookOrders?\$orderby=orderNo%20desc&\$top=1&\$select=orderNo" | python3 -c 'import sys,json;print(json.load(sys.stdin)["value"][0]["orderNo"])')"

echo "== 7. 绑定动作 submitOrder（状态迁移） =="
EMPTY_ID="$(body "${AUTH[@]}" "$SVC/BookOrders?\$select=ID&\$filter=orderNo%20eq%20'BO-1005'" | python3 -c 'import sys,json;print(json.load(sys.stdin)["value"][0]["ID"])')"
chk '空订单提交 → 400'   400 "$(code "${AUTH[@]}" -X POST "$SVC/BookOrders(ID=$EMPTY_ID,IsActiveEntity=true)/submitOrder" -H 'Content-Type: application/json' -d '{}')"
BO1001_ID="$(body "${AUTH[@]}" "$SVC/BookOrders?\$select=ID&\$filter=orderNo%20eq%20'BO-1001'" | python3 -c 'import sys,json;print(json.load(sys.stdin)["value"][0]["ID"])')"
chk 'BO-1001 提交 → 200' 200 "$(code "${AUTH[@]}" -X POST "$SVC/BookOrders(ID=$BO1001_ID,IsActiveEntity=true)/submitOrder" -H 'Content-Type: application/json' -d '{}')"
chk '状态已变为 SUBMITTED' SUBMITTED \
    "$(body "${AUTH[@]}" "$SVC/BookOrders?\$select=status&\$filter=orderNo%20eq%20'BO-1001'" | python3 -c 'import sys,json;print(json.load(sys.stdin)["value"][0]["status"])')"
chk '重复提交 → 409'      409 "$(code "${AUTH[@]}" -X POST "$SVC/BookOrders(ID=$BO1001_ID,IsActiveEntity=true)/submitOrder" -H 'Content-Type: application/json' -d '{}')"

echo
echo "==================== 结果 ===================="
echo "  PASS $PASS / FAIL $FAIL"
[ "$FAIL" = 0 ] || exit 1
