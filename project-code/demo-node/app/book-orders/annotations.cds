using BookOrderService as service from '../../srv/book-order-service';

/* ============================================================================
   Fiori Elements 用アノテーション（UI.*）
   —— 界面长什么样，几乎全部由这里决定；manifest.json 只决定「用哪个模板」。
   本文件被 CAP 编译进 OData $metadata 的 <Annotations> 段，浏览器里可直接核对：
       curl -u alice:alice "http://localhost:4004/odata/v4/book-order/\$metadata" | grep -A3 LineItem
   ========================================================================== */

annotate service.BookOrders with @(
  UI.HeaderInfo: {
    TypeName      : '订单',
    TypeNamePlural: '订单',
    Title         : { Value: orderNo },
    Description   : { Value: customer.name }
  },
  /* 列表页顶部的筛选字段（出现在 Adapt Filters 里） */
  UI.SelectionFields: [ orderNo, status, customer_ID ],
  /* 列表页的列 + 行内动作 */
  UI.LineItem: [
    { $Type: 'UI.DataField', Label: '订单号',      Value: orderNo },
    { $Type: 'UI.DataField', Label: '顾客',        Value: customer.name },
    { $Type: 'UI.DataField', Label: '订单日期',    Value: orderDate },
    { $Type: 'UI.DataField', Label: '状态',        Value: status, Criticality: statusCriticality },
    { $Type: 'UI.DataField', Label: '合计 (JPY)',  Value: totalAmount },
    {
      $Type: 'UI.DataFieldForAction',
      Label: '提交订单',
      Action: 'BookOrderService.BookOrders/submitOrder',
      Inline: true,
      Determining: true
    }
  ],
  /* 明细页（Object Page）的表头字段 */
  UI.FieldGroup #OrderData: {
    $Type: 'UI.FieldGroupType',
    Data: [
      { $Type: 'UI.DataField', Label: '订单号',  Value: orderNo },
      { $Type: 'UI.DataField', Label: '顾客',    Value: customer.name },
      { $Type: 'UI.DataField', Label: '订单日期', Value: orderDate },
      { $Type: 'UI.DataField', Label: '状态',    Value: status, Criticality: statusCriticality },
      { $Type: 'UI.DataField', Label: '备注',    Value: note }
    ]
  },
  UI.FieldGroup #Amounts: {
    $Type: 'UI.FieldGroupType',
    Data: [
      { $Type: 'UI.DataField', Label: '合计 (JPY)', Value: totalAmount }
    ]
  },
  UI.Facets: [
    { $Type: 'UI.ReferenceFacet', Label: '订单信息', Target: '@UI.FieldGroup#OrderData' },
    { $Type: 'UI.ReferenceFacet', Label: '金额',     Target: '@UI.FieldGroup#Amounts' },
    { $Type: 'UI.ReferenceFacet', Label: '订单明细', Target: 'items/@UI.LineItem' }
  ],
  /* 合计由服务端计算，界面上不可编辑 */
  totalAmount       : @readonly,
  statusCriticality : @UI.Hidden,
  items             : @UI.Hidden
);

/* 筛选字段的标签来自元素自身的 @title（不加就显示技术名 orderNo / status / customer_ID） */
annotate service.BookOrders with @(
  orderNo     : @title: '订单号',
  status      : @title: '状态',
  customer    : @title: '顾客',
  customer_ID : @title: '顾客编号',
  orderDate   : @title: '订单日期',
  totalAmount : @title: '合计'
);

/* 明细表（Object Page 里的 table section） */
annotate service.BookOrderItems with @(
  UI.HeaderInfo: { TypeName: '明细', TypeNamePlural: '明细', Title: { Value: book.title } },
  UI.LineItem: [
    { $Type: 'UI.DataField', Label: '图书',      Value: book.title },
    { $Type: 'UI.DataField', Label: '单价 (JPY)', Value: book.price },
    { $Type: 'UI.DataField', Label: '数量',      Value: quantity },
    { $Type: 'UI.DataField', Label: '金额 (JPY)', Value: amount, Criticality: #Neutral }
  ],
  amount : @readonly
);

/* 只读视图实体：不提供编辑入口 */
annotate service.OrderItemView with @readonly;
