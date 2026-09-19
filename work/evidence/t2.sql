
CREATE TABLE sap_training_bookorder_Books (
  ID INTEGER NOT NULL,
  title NVARCHAR(120) NOT NULL,
  author NVARCHAR(80),
  price DECIMAL(9, 2) NOT NULL,
  currency NVARCHAR(3) DEFAULT 'JPY',
  stock INTEGER DEFAULT 0,
  PRIMARY KEY(ID)
);

CREATE TABLE sap_training_bookorder_Customers (
  ID INTEGER NOT NULL,
  name NVARCHAR(80) NOT NULL,
  city NVARCHAR(60),
  country NVARCHAR(20),
  email NVARCHAR(120),
  PRIMARY KEY(ID)
);

CREATE TABLE sap_training_bookorder_BookOrders (
  createdAt TIMESTAMP_TEXT,
  createdBy NVARCHAR(255),
  modifiedAt TIMESTAMP_TEXT,
  modifiedBy NVARCHAR(255),
  ID NVARCHAR(36) NOT NULL,
  orderNo NVARCHAR(16) NOT NULL,
  customer_ID INTEGER,
  orderDate DATE_TEXT DEFAULT CURRENT_TIMESTAMP,
  status NVARCHAR(10) DEFAULT 'OPEN',
  note NVARCHAR(255),
  totalAmount DECIMAL(13, 2) DEFAULT 0,
  statusCriticality INTEGER DEFAULT 2,
  PRIMARY KEY(ID)
);

CREATE TABLE sap_training_bookorder_BookOrderItems (
  createdAt TIMESTAMP_TEXT,
  createdBy NVARCHAR(255),
  modifiedAt TIMESTAMP_TEXT,
  modifiedBy NVARCHAR(255),
  ID NVARCHAR(36) NOT NULL,
  order_ID NVARCHAR(36),
  book_ID INTEGER,
  quantity INTEGER DEFAULT 1,
  amount DECIMAL(13, 2),
  PRIMARY KEY(ID)
);

CREATE TABLE DRAFT_DraftAdministrativeData (
  DraftUUID NVARCHAR(36) NOT NULL,
  CreationDateTime TIMESTAMP_TEXT,
  CreatedByUser NVARCHAR(256),
  CreatedByUserDescription NVARCHAR(256),
  DraftIsCreatedByMe BOOLEAN,
  LastChangeDateTime TIMESTAMP_TEXT,
  LastChangedByUser NVARCHAR(256),
  LastChangedByUserDescription NVARCHAR(256),
  InProcessByUser NVARCHAR(256),
  InProcessByUserDescription NVARCHAR(256),
  DraftIsProcessedByMe BOOLEAN,
  DraftMessages NCLOB,
  PRIMARY KEY(DraftUUID)
);

CREATE TABLE BookOrderService_BookOrders_drafts (
  createdAt TIMESTAMP_TEXT NULL,
  createdBy NVARCHAR(255) NULL,
  modifiedAt TIMESTAMP_TEXT NULL,
  modifiedBy NVARCHAR(255) NULL,
  ID NVARCHAR(36) NOT NULL,
  orderNo NVARCHAR(16) NULL,
  customer_ID INTEGER NULL,
  orderDate DATE_TEXT NULL DEFAULT CURRENT_TIMESTAMP,
  status NVARCHAR(10) NULL DEFAULT 'OPEN',
  note NVARCHAR(255) NULL,
  totalAmount DECIMAL(13, 2) NULL DEFAULT 0,
  statusCriticality INTEGER NULL DEFAULT 2,
  IsActiveEntity BOOLEAN,
  HasActiveEntity BOOLEAN,
  HasDraftEntity BOOLEAN,
  DraftAdministrativeData_DraftUUID NVARCHAR(36) NOT NULL,
  PRIMARY KEY(ID)
);

CREATE VIEW BookOrderService_Books AS SELECT
  Books_0.ID,
  Books_0.title,
  Books_0.author,
  Books_0.price,
  Books_0.currency,
  Books_0.stock
FROM sap_training_bookorder_Books AS Books_0;

CREATE VIEW BookOrderService_Customers AS SELECT
  Customers_0.ID,
  Customers_0.name,
  Customers_0.city,
  Customers_0.country,
  Customers_0.email
FROM sap_training_bookorder_Customers AS Customers_0;

CREATE VIEW BookOrderService_BookOrders AS SELECT
  BookOrders_0.createdAt,
  BookOrders_0.createdBy,
  BookOrders_0.modifiedAt,
  BookOrders_0.modifiedBy,
  BookOrders_0.ID,
  BookOrders_0.orderNo,
  BookOrders_0.customer_ID,
  BookOrders_0.orderDate,
  BookOrders_0.status,
  BookOrders_0.note,
  BookOrders_0.totalAmount,
  BookOrders_0.statusCriticality
FROM sap_training_bookorder_BookOrders AS BookOrders_0;

CREATE VIEW BookOrderService_BookOrderItems AS SELECT
  BookOrderItems_0.createdAt,
  BookOrderItems_0.createdBy,
  BookOrderItems_0.modifiedAt,
  BookOrderItems_0.modifiedBy,
  BookOrderItems_0.ID,
  BookOrderItems_0.order_ID,
  BookOrderItems_0.book_ID,
  BookOrderItems_0.quantity,
  BookOrderItems_0.amount
FROM sap_training_bookorder_BookOrderItems AS BookOrderItems_0;

CREATE VIEW sap_training_bookorder_OrderItemView AS SELECT
  BookOrderItems_0.ID,
  order_1.orderNo AS orderNo,
  order_1.orderDate AS orderDate,
  BookOrderItems_0.book_ID AS bookID,
  book_2.title AS bookTitle,
  book_2.price AS unitPrice,
  BookOrderItems_0.quantity,
  BookOrderItems_0.amount
FROM ((sap_training_bookorder_BookOrderItems AS BookOrderItems_0 LEFT JOIN sap_training_bookorder_BookOrders AS order_1 ON BookOrderItems_0.order_ID = order_1.ID) LEFT JOIN sap_training_bookorder_Books AS book_2 ON BookOrderItems_0.book_ID = book_2.ID);

CREATE VIEW BookOrderService_DraftAdministrativeData AS SELECT
  DraftAdministrativeData.DraftUUID,
  DraftAdministrativeData.CreationDateTime,
  DraftAdministrativeData.CreatedByUser,
  DraftAdministrativeData.CreatedByUserDescription,
  DraftAdministrativeData.DraftIsCreatedByMe,
  DraftAdministrativeData.LastChangeDateTime,
  DraftAdministrativeData.LastChangedByUser,
  DraftAdministrativeData.LastChangedByUserDescription,
  DraftAdministrativeData.InProcessByUser,
  DraftAdministrativeData.InProcessByUserDescription,
  DraftAdministrativeData.DraftIsProcessedByMe,
  DraftAdministrativeData.DraftMessages
FROM DRAFT_DraftAdministrativeData AS DraftAdministrativeData;

CREATE VIEW BookOrderService_OrderItemView AS SELECT
  OrderItemView_0.ID,
  OrderItemView_0.orderNo,
  OrderItemView_0.orderDate,
  OrderItemView_0.bookID,
  OrderItemView_0.bookTitle,
  OrderItemView_0.unitPrice,
  OrderItemView_0.quantity,
  OrderItemView_0.amount
FROM sap_training_bookorder_OrderItemView AS OrderItemView_0;

