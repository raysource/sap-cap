package com.training.bookorder.handlers;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

import org.springframework.stereotype.Component;

import com.sap.cds.Result;
import com.sap.cds.ql.Select;
import com.sap.cds.ql.Update;
import com.sap.cds.ql.cqn.CqnAnalyzer;
import com.sap.cds.reflect.CdsModel;
import com.sap.cds.services.ErrorStatuses;
import com.sap.cds.services.ServiceException;
import com.sap.cds.services.cds.CdsCreateEventContext;
import com.sap.cds.services.cds.CdsDeleteEventContext;
import com.sap.cds.services.cds.CdsUpdateEventContext;
import com.sap.cds.services.cds.CqnService;
import com.sap.cds.services.handler.EventHandler;
import com.sap.cds.services.handler.annotations.After;
import com.sap.cds.services.handler.annotations.Before;
import com.sap.cds.services.handler.annotations.On;
import com.sap.cds.services.handler.annotations.ServiceName;
import com.sap.cds.services.persistence.PersistenceService;

import cds.gen.bookorderservice.BookOrderItems;
import cds.gen.bookorderservice.BookOrderItems_;
import cds.gen.bookorderservice.BookOrderService_;
import cds.gen.bookorderservice.BookOrders;
import cds.gen.bookorderservice.BookOrdersSubmitOrderContext;
import cds.gen.bookorderservice.BookOrders_;
import cds.gen.bookorderservice.Books;
import cds.gen.bookorderservice.Books_;
import cds.gen.bookorderservice.Customers;
import cds.gen.bookorderservice.Customers_;
import cds.gen.bookorderservice.GetOrderSummaryContext;
import cds.gen.bookorderservice.GetOrderTotalContext;
import cds.gen.bookorderservice.OrderSummaryRow;

/**
 * 图书受注管理 —— 业务逻辑（CAP Java 事件处理器）
 *
 * 与 Node 版 (../demo-node/srv/book-order-service.js) 实现同一套规则，正好用来对照两种运行时：
 *   Node:  this.before('CREATE', BookOrders, async (req) => …)          运行时注册，鸭子类型
 *   Java:  @Before(event = CqnService.EVENT_CREATE, entity = …)         注解声明，编译期类型安全
 *
 * 5 类实现位置与 Node 版一一对应：
 *   ① before CREATE 订单头：编号生成 / 查重 / 主数据校验 / 派生字段（statusCriticality）
 *   ② before CREATE+UPDATE 明细：金额 = 图书单价 × 数量，数量必须 > 0
 *   ③ after 明细变化：汇总回写父订单的 totalAmount（删除前先用 before 记下父键）
 *   ④ on 绑定动作 submitOrder：状态迁移 + 业务校验
 *   ⑤ on 无绑定函数 getOrderTotal / getOrderSummary：聚合结果没有主键，不能作为实体暴露
 */
@Component
@ServiceName(BookOrderService_.CDS_NAME)
public class BookOrderServiceHandler implements EventHandler {

    private final PersistenceService db;
    private final CqnAnalyzer analyzer;

    public BookOrderServiceHandler(PersistenceService db, CdsModel model) {
        this.db = db;
        this.analyzer = CqnAnalyzer.create(model);
    }

    /* ------------------------------------------------------------------
     * ① 订单头：编号生成 + 校验 + 派生字段
     * 注意：BookOrders 开启了 @odata.draft.enabled，所以本钩子在「激活草稿」时触发，
     *      Fiori 的 Create → Save 流程同样会走到这里。
     * ------------------------------------------------------------------ */
    @Before(event = CqnService.EVENT_CREATE, entity = BookOrders_.CDS_NAME)
    public void beforeCreateOrder(BookOrders order) {
        if (order.getOrderNo() == null || order.getOrderNo().isBlank()) {
            order.setOrderNo(nextOrderNo());
        } else if (db.run(Select.from(BookOrders_.class)
                .where(o -> o.orderNo().eq(order.getOrderNo()))).first(BookOrders.class).isPresent()) {
            throw new ServiceException(ErrorStatuses.CONFLICT,
                    "订单号 " + order.getOrderNo() + " 已存在，请更换");
        }

        if (order.getOrderDate() == null) {
            order.setOrderDate(LocalDate.now());
        }
        if (order.getStatus() == null) {
            order.setStatus("OPEN");
        }
        order.setStatusCriticality(criticalityOf(order.getStatus()));   // 派生字段：给界面着色用

        Integer customerId = order.getCustomerId();
        if (customerId != null && db.run(Select.from(Customers_.class)
                .where(c -> c.ID().eq(customerId))).first(Customers.class).isEmpty()) {
            throw new ServiceException(ErrorStatuses.BAD_REQUEST,
                    "顾客 " + customerId + " 不存在，请先维护主数据");
        }
    }

    /** 合计金额由子表汇总，客户端不可直接改 */
    @Before(event = CqnService.EVENT_UPDATE, entity = BookOrders_.CDS_NAME)
    public void beforeUpdateOrder(BookOrders order) {
        order.setTotalAmount(null);
    }

    /* ------------------------------------------------------------------
     * ② 明细：金额派生计算 + 数量校验
     * ------------------------------------------------------------------ */
    @Before(event = { CqnService.EVENT_CREATE, CqnService.EVENT_UPDATE }, entity = BookOrderItems_.CDS_NAME)
    public void beforeBookOrderItems(BookOrderItems item) {
        Integer quantity = item.getQuantity();
        if (quantity != null && quantity <= 0) {
            throw new ServiceException(ErrorStatuses.BAD_REQUEST, "数量必须大于 0");
        }
        Integer bookId = item.getBookId();
        if (bookId == null) {
            return;                                   // 更新时没有换书 → 单价不变，金额随数量重算
        }
        Books book = db.run(Select.from(Books_.class).where(b -> b.ID().eq(bookId)))
                .first(Books.class).orElse(null);
        if (book == null) {
            throw new ServiceException(ErrorStatuses.BAD_REQUEST, "图书 " + bookId + " 不存在");
        }
        item.setAmount(book.getPrice().multiply(BigDecimal.valueOf(quantity == null ? 0 : quantity)));
    }

    /* ------------------------------------------------------------------
     * ③ 明细变化后回写订单合计
     * 删除时被删的行不再返回（与 Node 版同一个坑）→ 先在 before 里把父键查出来放到上下文
     * ------------------------------------------------------------------ */
    @After(event = CqnService.EVENT_CREATE, entity = BookOrderItems_.CDS_NAME)
    public void afterCreateItem(CdsCreateEventContext ctx) {
        recalcFromResult(ctx.getResult());
    }

    @After(event = CqnService.EVENT_UPDATE, entity = BookOrderItems_.CDS_NAME)
    public void afterUpdateItem(CdsUpdateEventContext ctx) {
        recalcFromResult(ctx.getResult());
    }

    @Before(event = CqnService.EVENT_DELETE, entity = BookOrderItems_.CDS_NAME)
    public void rememberParentOrders(CdsDeleteEventContext ctx) {
        List<String> ids = db.run(ctx.getCqn().asSelect()).stream()
                .map(r -> Objects.toString(r.get(BookOrderItems.ORDER_ID), null))
                .filter(Objects::nonNull).distinct().toList();
        ctx.put("ordersToRecalc", ids);
    }

    @After(event = CqnService.EVENT_DELETE, entity = BookOrderItems_.CDS_NAME)
    public void afterDeleteItem(CdsDeleteEventContext ctx) {
        Object remembered = ctx.get("ordersToRecalc");
        if (remembered instanceof List<?> ids) {
            ids.forEach(id -> recalcTotal((String) id));
        }
    }

    /* ------------------------------------------------------------------
     * ④ 绑定动作：提交订单（状态迁移 + 业务校验）
     * ------------------------------------------------------------------ */
    @On(event = "submitOrder", entity = BookOrders_.CDS_NAME)
    public void submitOrder(BookOrdersSubmitOrderContext ctx) {
        // 绑定动作的键在 CQN 里 → 用 CqnAnalyzer 取（不要自己解析 URL）
        Map<String, Object> keys = analyzer.analyze(ctx.getCqn()).rootKeys();
        String id = (String) keys.get(BookOrders.ID);

        BookOrders order = db.run(Select.from(BookOrders_.class)
                .where(o -> o.ID().eq(id))).first(BookOrders.class).orElse(null);
        if (order == null) {
            throw new ServiceException(ErrorStatuses.NOT_FOUND, "订单 " + id + " 不存在");
        }
        if ("SUBMITTED".equals(order.getStatus()) || "CLOSED".equals(order.getStatus())) {
            throw new ServiceException(ErrorStatuses.CONFLICT,
                    "订单 " + order.getOrderNo() + " 当前状态为 " + order.getStatus() + "，不能重复提交");
        }
        List<BookOrderItems> items = db.run(Select.from(BookOrderItems_.class)
                .where(i -> i.order_ID().eq(id))).listOf(BookOrderItems.class);
        if (items.isEmpty()) {
            throw new ServiceException(ErrorStatuses.BAD_REQUEST,
                    "订单 " + order.getOrderNo() + " 没有明细，不能提交");
        }
        if (order.getTotalAmount() == null || order.getTotalAmount().signum() <= 0) {
            throw new ServiceException(ErrorStatuses.BAD_REQUEST,
                    "订单 " + order.getOrderNo() + " 合计金额为 0，请检查明细金额");
        }

        db.run(Update.entity(BookOrders_.class).where(o -> o.ID().eq(id))
                .data(BookOrders.STATUS, "SUBMITTED")
                .data(BookOrders.STATUS_CRITICALITY, criticalityOf("SUBMITTED")));

        ctx.setResult(String.format("订单 %s 已提交，合计 %s JPY（%d 行）",
                order.getOrderNo(), order.getTotalAmount().toPlainString(), items.size()));
    }

    /* ------------------------------------------------------------------
     * ⑤ 无绑定函数：聚合结果没有主键，不能暴露为实体 → 用函数返回
     * ------------------------------------------------------------------ */
    @On(event = "getOrderTotal")
    public void getOrderTotal(GetOrderTotalContext ctx) {
        BookOrders order = db.run(Select.from(BookOrders_.class)
                .where(o -> o.orderNo().eq(ctx.getOrderNo()))).first(BookOrders.class).orElse(null);
        if (order == null) {
            throw new ServiceException(ErrorStatuses.NOT_FOUND, "订单号 " + ctx.getOrderNo() + " 不存在");
        }
        ctx.setResult(totalOf(order.getId()));
    }

    @On(event = "getOrderSummary")
    public void getOrderSummary(GetOrderSummaryContext ctx) {
        List<BookOrders> orders = db.run(Select.from(BookOrders_.class)
                .orderBy(o -> o.orderNo().asc())).listOf(BookOrders.class);
        Map<Integer, String> customerNames = new LinkedHashMap<>();
        db.run(Select.from(Customers_.class)).listOf(Customers.class)
                .forEach(c -> customerNames.put(c.getId(), c.getName()));

        List<OrderSummaryRow> rows = new ArrayList<>();
        for (BookOrders o : orders) {
            OrderSummaryRow row = OrderSummaryRow.create();
            row.setOrderNo(o.getOrderNo());
            row.setCustomerName(customerNames.getOrDefault(o.getCustomerId(), ""));
            row.setOrderDate(o.getOrderDate());
            row.setStatus(o.getStatus());
            row.setItemCount(db.run(Select.from(BookOrderItems_.class)
                    .where(i -> i.order_ID().eq(o.getId()))).listOf(BookOrderItems.class).size());
            row.setTotalAmount(totalOf(o.getId()));
            rows.add(row);
        }
        ctx.setResult(rows);
    }

    /* ------------------------------------------------------------------ helpers */

    private void recalcFromResult(Result result) {
        result.stream().map(r -> Objects.toString(r.get(BookOrderItems.ORDER_ID), null))
                .filter(Objects::nonNull).distinct().forEach(this::recalcTotal);
    }

    /** 明细之和 → 回写父订单合计（Java 侧直接求和；也演示了「不用 group by 也能做」的取舍） */
    private void recalcTotal(String orderId) {
        if (orderId == null) {
            return;
        }
        db.run(Update.entity(BookOrders_.class).where(o -> o.ID().eq(orderId))
                .data(BookOrders.TOTAL_AMOUNT, totalOf(orderId)));
    }

    private BigDecimal totalOf(String orderId) {
        return db.run(Select.from(BookOrderItems_.class).columns(i -> i.amount())
                        .where(i -> i.order_ID().eq(orderId))).stream()
                .map(r -> r.get(BookOrderItems.AMOUNT))
                .filter(Objects::nonNull)
                .map(a -> new BigDecimal(a.toString()))
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    /** 服务端编号：max(orderNo) + 1，格式 BO-#### */
    private String nextOrderNo() {
        int max = db.run(Select.from(BookOrders_.class).columns(o -> o.orderNo())).stream()
                .map(r -> (String) r.get(BookOrders.ORDER_NO))
                .filter(Objects::nonNull)
                .mapToInt(no -> {
                    try {
                        return Integer.parseInt(no.replaceAll("\\D", ""));
                    } catch (NumberFormatException e) {
                        return 1000;
                    }
                }).max().orElse(1000);
        return "BO-" + (max + 1);
    }

    /** 状态 → UI.Criticality 值（0 Neutral / 1 Negative / 2 Critical / 3 Positive） */
    private static Integer criticalityOf(String status) {
        return switch (status == null ? "" : status) {
            case "OPEN" -> 2;
            case "SUBMITTED" -> 3;
            case "CLOSED" -> 0;
            case "CANCELLED" -> 1;
            default -> 0;
        };
    }
}
