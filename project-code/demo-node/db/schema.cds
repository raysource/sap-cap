namespace sap.training.bookorder;

using { cuid, managed } from '@sap/cds/common';

/**
 * 図書（商品マスタ / 商品主数据）
 * 価格は主データ由来。通貨は列挙型を使わず String(3) にしてある（ローカル SQLite での
 * codelist 検証を避けるため。本番は Currency 型でよい）。
 */
entity Books {
  key ID       : Integer;
      title    : String(120) not null;
      author   : String(80);
      price    : Decimal(9,2) not null;
      currency : String(3) default 'JPY';
      stock    : Integer default 0;
}

/** 顧客（得意先 / 客户） */
entity Customers {
  key ID      : Integer;
      name    : String(80) not null;
      city    : String(60);
      country : String(20);
      email   : String(120);
}

/**
 * 受注ヘッダ（订单头）
 * 故意「不使用 Composition」：子表用普通 FK 列 + 显式 to-many 关联。
 * 这样 CSV 初始化（db/data）与 $expand 都能正常工作（Composition 的父侧 FK 列
 * 不会被 CSV 填充，$expand 会返回空数组）。
 */
entity BookOrders : managed {
  key ID          : UUID;
      orderNo     : String(16) not null;
      customer    : Association to Customers;
      orderDate   : Date default $now;
      status      : String(10) default 'OPEN';
      note        : String(255);
      totalAmount : Decimal(13,2) default 0;
      /* 派生字段：状态的 UI 语义（0=Neutral 1=Negative 2=Critical 3=Positive）
         由服务端维护，供 Fiori 的 UI.Criticality 着色使用（见 annotations.cds） */
      statusCriticality : Integer default 2;
      items       : Association to many BookOrderItems on items.order = $self;
}

/** 受注明细（订单行项目） */
entity BookOrderItems : managed {
  key ID       : UUID;
      order    : Association to BookOrders;
      book     : Association to Books;
      quantity : Integer default 1;
      amount   : Decimal(13,2);
}

/**
 * 参照ビュー（带主键的展开视图）
 * —— 视图只有在「有主键」时才能作为 OData 实体暴露（否则 cds2edm 报
 *    Expected entity to have a primary key）。集计（group by）视图拿不到主键，
 *    所以汇总一律走服务层的无绑定函数（见 srv/book-order-service.js）。
 */
entity OrderItemView as select from BookOrderItems {
  key ID,
      order.orderNo   as orderNo,
      order.orderDate as orderDate,
      book.ID         as bookID,
      book.title      as bookTitle,
      book.price      as unitPrice,
      quantity,
      amount
};
