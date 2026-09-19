package com.training.bookorder;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

/**
 * CAP Java 侧的集成测试（与 Node 版 test/odata-verify.sh 覆盖同一批规则）。
 *
 * 跑法：  mvn -pl srv test      （从 demo-java 根目录）
 * 说明：  H2 内存库在每次启动时按 schema-h2.sql 重建，所以测试之间互不影响；
 *        这正好解决了 Node 版「脚本跑一次就污染数据，要重新 deploy」的问题。
 */
@SpringBootTest
@AutoConfigureMockMvc
class BookOrderServiceTest {

    /** 种子数据里的订单 UUID（db/data/sap.training.bookorder-BookOrders.csv） */
    static final String BO1002 = "4a1f8c03-0002-4000-8000-000000000002";

    @Autowired
    MockMvc mvc;

    /**
     * 注意：认证中间件一旦生效（cds-starter-cloudfoundry 在场），**$metadata 也需要凭据**——
     * 这点与 Node 版不同：Node 的 mocked 认证下匿名取 $metadata 是 200。
     * 本机实测：匿名 → 401，带 alice → 200。所以断言要按运行时的真实行为写。
     */
    @Test
    @DisplayName("$metadata：匿名 → 401，带凭据 → 200")
    void metadataRequiresAuth() throws Exception {
        mvc.perform(get("/odata/v4/book-order/$metadata"))
                .andExpect(status().isUnauthorized());
        mvc.perform(get("/odata/v4/book-order/$metadata").with(httpBasic("alice", "alice")))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("匿名访问实体 → 401（服务上是 @(requires: 'authenticated-user')）")
    void anonymousIsRejected() throws Exception {
        mvc.perform(get("/odata/v4/book-order/BookOrders"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("mock 用户 alice 能读到 4 张种子订单")
    void ordersAreReadable() throws Exception {
        mvc.perform(get("/odata/v4/book-order/BookOrders?$select=orderNo,status,totalAmount")
                        .with(httpBasic("alice", "alice")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.value.length()").value(4))
                .andExpect(jsonPath("$.value[0].orderNo").value("BO-1001"))
                .andExpect(jsonPath("$.value[0].totalAmount").value(16000));
    }

    @Test
    @DisplayName("$expand=items 能取到明细（子表用普通 FK 列 + 显式关联的成果）")
    void expandItemsWorks() throws Exception {
        mvc.perform(get("/odata/v4/book-order/BookOrders?$filter=orderNo eq 'BO-1001'&$expand=items")
                        .with(httpBasic("alice", "alice")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.value[0].items.length()").value(3));
    }

    @Test
    @DisplayName("无绑定函数 getOrderTotal 返回聚合结果（聚合没有主键，不能做成实体）")
    void orderTotalFunction() throws Exception {
        mvc.perform(get("/odata/v4/book-order/getOrderTotal(orderNo='BO-1003')")
                        .with(httpBasic("alice", "alice")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.value").value(17400));
    }

    @Test
    @DisplayName("无绑定函数 getOrderSummary 返回 4 行汇总")
    void orderSummaryFunction() throws Exception {
        mvc.perform(get("/odata/v4/book-order/getOrderSummary()")
                        .with(httpBasic("alice", "alice")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.value.length()").value(4))
                .andExpect(jsonPath("$.value[0].itemCount").value(3));
    }

    @Test
    @DisplayName("业务校验：数量 <= 0 → 400（不是 500）")
    void quantityMustBePositive() throws Exception {
        mvc.perform(post("/odata/v4/book-order/BookOrderItems")
                        .with(httpBasic("alice", "alice"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"order_ID\":\"" + BO1002 + "\",\"book_ID\":1003,\"quantity\":0}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("派生的合计字段在写入明细后被回写（金额 = 单价 × 数量）")
    void itemAmountIsDerived() throws Exception {
        mvc.perform(post("/odata/v4/book-order/BookOrderItems")
                        .with(httpBasic("alice", "alice"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"order_ID\":\"" + BO1002 + "\",\"book_ID\":1003,\"quantity\":3}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.amount").value(8400));       // 2800 × 3

        mvc.perform(get("/odata/v4/book-order/BookOrders?$filter=orderNo eq 'BO-1002'&$select=totalAmount")
                        .with(httpBasic("alice", "alice")))
                .andExpect(jsonPath("$.value[0].totalAmount").value(12000));  // 3600 + 8400
    }
}
