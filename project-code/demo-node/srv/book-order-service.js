const cds = require('@sap/cds');

/**
 * 图书受注管理 —— 业务逻辑（CAP Node.js 事件处理器）
 *
 * 这里演示 CAP 的 5 类典型实现位置：
 *   ① before CREATE —— 主键/编号生成 + 入参校验（订单号、顾客存在性）
 *   ② before CREATE/UPDATE（子表）—— 派生字段计算（金额 = 单价 × 数量）
 *   ③ after（子表）—— 汇总回写父表（订单合计）
 *   ④ bound action —— 状态迁移（提交订单），带业务校验与错误消息
 *   ⑤ unbound function —— 聚合查询（视图无主键，不能直接暴露为实体）
 */
module.exports = class BookOrderService extends cds.ApplicationService {

  async init() {
    const { Books, Customers, BookOrders, BookOrderItems } = this.entities;

    /* ------------------------------------------------------------------
     * ① 订单头：自动编号 + 校验
     * 注意：BookOrders 开启了 @odata.draft.enabled，所以本钩子在「激活草稿」
     *       （即真正写入 active 表）时触发，Fiori 的 Create 流程同样会走到这里。
     * ------------------------------------------------------------------ */
    this.before('CREATE', BookOrders, async (req) => {
      const data = req.data;

      if (!data.orderNo) {
        data.orderNo = await nextOrderNo();
      } else {
        const dup = await SELECT.one.from(BookOrders).where({ orderNo: data.orderNo });
        if (dup) req.reject(409, `订单号 ${data.orderNo} 已存在，请更换`);
      }
      if (!data.orderDate) data.orderDate = new Date().toISOString().slice(0, 10);
      if (data.status == null) data.status = 'OPEN';
      data.statusCriticality = criticalityOf(data.status);

      if (data.customer_ID != null) {
        const cust = await SELECT.one.from(Customers).where({ ID: data.customer_ID });
        if (!cust) req.reject(400, `顾客 ${data.customer_ID} 不存在，请先维护主数据`);
      }
    });

    /* ③ 订单头：合计金额由子表汇总，客户端不可直接改 */
    this.before('UPDATE', BookOrders, (req) => {
      delete req.data.totalAmount;
    });

    /* ------------------------------------------------------------------
     * ② 明细：金额派生计算 + 数量校验
     * ------------------------------------------------------------------ */
    this.before(['CREATE', 'UPDATE'], BookOrderItems, async (req) => {
      const data = req.data;
      try {
        if (data.quantity != null && data.quantity <= 0) {
          req.reject(400, '数量必须大于 0');
        }
        const bookID = data.book_ID ?? (await SELECT.one.from(BookOrderItems).where({ ID: req.data.ID }))?.book_ID;
        if (bookID == null) req.reject(400, '必须指定图书（book）');

        const book = await SELECT.one.from(Books).where({ ID: bookID });
        if (!book) req.reject(400, `图书 ${bookID} 不存在`);

        const qty = data.quantity ?? (await SELECT.one.from(BookOrderItems).where({ ID: data.ID }))?.quantity ?? 0;
        data.amount = round2(Number(book.price) * Number(qty));
      } catch (e) {
        if (e.code === 400 || e.code === 409) throw e;       // 已用 req.reject 拒绝
        req.reject(500, `计算金额失败：${e.message}`);
      }
    });

    /* ③ 明细变化后回写订单合计（新增/修改/删除都要） */
    const recalc = async (orderID) => {
      if (!orderID) return;
      const row = await SELECT.one.from(BookOrderItems)
        .columns('sum(amount) as total')
        .where({ order_ID: orderID });
      const total = round2(Number(row?.total ?? 0));
      await UPDATE(BookOrders).set({ totalAmount: total }).where({ ID: orderID });
    };
    this.after('CREATE', BookOrderItems, async (_, req) => recalc(req.data.order_ID));
    this.after('UPDATE', BookOrderItems, async (_, req) => recalc(req.data.order_ID));
    this.after('DELETE', BookOrderItems, async (_, req) => {
      // 删除后的行不再返回键值，必须从请求里取（CAP 已确认的行为）
      const orderID = req.data?.order_ID ?? req.params?.[req.params.length - 1]?.order_ID;
      await recalc(orderID);
    });

    /* ------------------------------------------------------------------
     * ④ 绑定动作：提交订单（状态迁移 + 业务校验）
     * ------------------------------------------------------------------ */
    this.on('submitOrder', BookOrders, async (req) => {
      const ID = req.params[req.params.length - 1].ID;
      const order = await SELECT.one.from(BookOrders).where({ ID });
      if (!order) req.reject(404, `订单 ${ID} 不存在`);
      if (order.status === 'SUBMITTED' || order.status === 'CLOSED') {
        req.reject(409, `订单 ${order.orderNo} 当前状态为 ${order.status}，不能重复提交`);
      }
      const items = await SELECT.from(BookOrderItems).where({ order_ID: ID });
      if (items.length === 0) req.reject(400, `订单 ${order.orderNo} 没有明细，不能提交`);
      if (Number(order.totalAmount) <= 0) req.reject(400, `订单 ${order.orderNo} 合计金额为 0，请检查明细金额`);

      await UPDATE(BookOrders).set({ status: 'SUBMITTED', statusCriticality: criticalityOf('SUBMITTED') })
        .where({ ID });
      return `订单 ${order.orderNo} 已提交，合计 ${Number(order.totalAmount).toFixed(2)} JPY（${items.length} 行）`;
    });

    /* ------------------------------------------------------------------
     * ⑤ 无绑定函数：聚合结果没有主键，不能暴露为实体，
     *    所以用「函数 + 服务层聚合」返回（这是 CAP 里最常见的取舍）
     * ------------------------------------------------------------------ */
    this.on('getOrderTotal', async (req) => {
      const { orderNo } = req.data;
      const order = await SELECT.one.from(BookOrders).where({ orderNo });
      if (!order) req.reject(404, `订单号 ${orderNo} 不存在`);
      const row = await SELECT.one.from(BookOrderItems)
        .columns('sum(amount) as total')
        .where({ order_ID: order.ID });
      return round2(Number(row?.total ?? 0));
    });

    this.on('getOrderSummary', async () => {
      const orders = await SELECT.from(BookOrders)
        .columns('ID', 'orderNo', 'orderDate', 'status', 'customer.name as customerName')
        .orderBy('orderNo');
      const agg = await SELECT.from(BookOrderItems)
        .columns('order_ID', 'count(ID) as itemCount', 'sum(amount) as totalAmount')
        .groupBy('order_ID');
      const byOrder = new Map(agg.map((a) => [a.order_ID, a]));
      return orders.map((o) => ({
        orderNo: o.orderNo,
        customerName: o.customerName ?? '',
        orderDate: o.orderDate,
        status: o.status,
        itemCount: Number(byOrder.get(o.ID)?.itemCount ?? 0),
        totalAmount: round2(Number(byOrder.get(o.ID)?.totalAmount ?? 0))
      }));
    });

    /* 业务错误一律返回 4xx，未捕获异常会变成 500 —— 统一收敛 */
    this.on('error', (err, req) => {
      if (!err.status) cds.log('bookorder').error(`未预期错误 ${req?.event}: ${err.message}`);
    });

    return super.init();
  }
};

const round2 = (n) => Math.round((Number(n) + Number.EPSILON) * 100) / 100;

/** 状态 → UI.Criticality 值（0 Neutral / 1 Negative / 2 Critical / 3 Positive） */
const criticalityOf = (status) => ({
  OPEN: 2, SUBMITTED: 3, CLOSED: 0, CANCELLED: 1
}[status] ?? 0);

async function nextOrderNo() {
  const row = await SELECT.one.from('sap.training.bookorder.BookOrders')
    .columns('max(orderNo) as maxNo');
  const n = row?.maxNo ? Number(String(row.maxNo).replace(/\D/g, '')) : 1000;
  return `BO-${n + 1}`;
}
