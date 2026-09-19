using { sap.training.bookorder as db } from '../db/schema';

@path: '/odata/v4/book-order'
service BookOrderService @(requires: 'authenticated-user') {

  entity Books         as projection on db.Books;
  entity Customers     as projection on db.Customers;

  @odata.draft.enabled
  entity BookOrders    as projection on db.BookOrders
                       actions { action submitOrder() returns String; };

  /* 两张实体都源自 db.BookOrderItems → 必须显式指定重定向目标，
     否则 CAP 报 “can't auto-redirect BookOrders:items” */
  @cds.redirection.target
  entity BookOrderItems as projection on db.BookOrderItems;

  /** 带主键的视图可以直接暴露为只读实体（对比服务层函数） */
  @readonly
  entity OrderItemView as projection on db.OrderItemView;

  /** 单张订单的合计：聚合结果没有主键 → 只能用函数返回 */
  function getOrderTotal(orderNo : String) returns Decimal(13,2);

  /** 订单汇总一览：同上，函数返回结构体数组（结果结构体不需要主键） */
  type OrderSummaryRow : {
    orderNo      : String(16);
    customerName : String(80);
    orderDate    : Date;
    status       : String(10);
    itemCount    : Integer;
    totalAmount  : Decimal(13,2);
  };
  function getOrderSummary() returns array of OrderSummaryRow;

}

/** Fiori Elements 用のアノテーション（UI.*）は app/book-orders/annotations.cds に置く */
