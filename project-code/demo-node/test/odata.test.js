const cds = require('@sap/cds')
const { GET, POST, expect, defaults, data } = cds.test(__dirname + '/..')

defaults.auth = { username: 'alice', password: 'alice' }
const SVC = '/odata/v4/book-order'
const fail = (p) => p.then((r) => { throw new Error('expected an error, got ' + r.status) }, (e) => e)

describe('图书受注服务 —— OData 集成测试（mocha + cds.test）', () => {
  // 本站示范项目把 db 指向 db.sqlite，所以测试前必须把库重置为 CSV 初始状态
  before(async () => { await data.reset() })

  it('① GET $metadata → 200，且暴露 BookOrderService.BookOrders', async () => {
    const res = await GET(`${SVC}/$metadata`)
    expect(res.status).to.equal(200)
    expect(res.data).to.contain('BookOrderService.BookOrders')
  })

  it('② 匿名（无 Basic Auth）→ 401', async () => {
    const err = await fail(GET(`${SVC}/BookOrders`, { auth: false }))
    expect(err.response.status).to.equal(401)
  })

  it('③ 过滤 status eq OPEN → 2 张（BO-1001 / BO-1002）', async () => {
    const res = await GET(`${SVC}/BookOrders?$filter=status eq 'OPEN'&$select=orderNo&$orderby=orderNo`)
    expect(res.data.value.map((r) => r.orderNo)).to.deep.equal(['BO-1001', 'BO-1002'])
  })

  it('④ $expand=items → BO-1001 有 3 行明细', async () => {
    const res = await GET(`${SVC}/BookOrders?$filter=orderNo eq 'BO-1001'&$expand=items`)
    expect(res.data.value[0].items.length).to.equal(3)
  })

  it('⑤ 只读视图 OrderItemView → 9 行，首行 orderNo=BO-1001', async () => {
    const res = await GET(`${SVC}/OrderItemView?$orderby=ID`)
    expect(res.data.value.length).to.equal(9)
    expect(res.data.value[0].orderNo).to.equal('BO-1001')
  })

  it('⑥ 函数 getOrderTotal(BO-1003) → 17400', async () => {
    const res = await GET(`${SVC}/getOrderTotal(orderNo='BO-1003')`)
    expect(res.data.value).to.equal(17400)
  })

  it('⑦ 函数 getOrderSummary() → 4 行，BO-1001 合计 16000', async () => {
    const res = await GET(`${SVC}/getOrderSummary()`)
    expect(res.data.value.length).to.equal(4)
    expect(res.data.value.find((r) => r.orderNo === 'BO-1001').totalAmount).to.equal(16000)
  })

  it('⑧ 派生字段：POST 明细 2800×3 → amount 8400，父订单合计回写 12000', async () => {
    const orders = await GET(`${SVC}/BookOrders?$select=ID&$filter=orderNo eq 'BO-1002'`)
    const orderID = orders.data.value[0].ID
    const created = await POST(`${SVC}/BookOrderItems`, { order_ID: orderID, book_ID: 1003, quantity: 3 })
    expect(created.status).to.equal(201)
    expect(created.data.amount).to.equal(8400)
    const after = await GET(`${SVC}/BookOrders(ID=${orderID},IsActiveEntity=true)?$select=totalAmount`)
    expect(after.data.totalAmount).to.equal(12000)
  })

  it('⑨ 负向：数量 0 → 400 且带业务消息', async () => {
    const err = await fail(POST(`${SVC}/BookOrderItems`, { order_ID: 'x', book_ID: 1003, quantity: 0 }))
    expect(err.response.status).to.equal(400)
    expect(err.response.data.error.message).to.equal('数量必须大于 0')
  })

  it('⑩ 负向：图书 9999 不存在 → 400', async () => {
    const err = await fail(POST(`${SVC}/BookOrderItems`, { order_ID: 'x', book_ID: 9999, quantity: 1 }))
    expect(err.response.status).to.equal(400)
  })

  it('⑪ 负向：只读实体 POST → 405', async () => {
    const err = await fail(POST(`${SVC}/OrderItemView`, {}))
    expect(err.response.status).to.equal(405)
  })

  it('⑫ 草稿：POST 新建订单 → IsActiveEntity=false（未激活）', async () => {
    const draft = await POST(`${SVC}/BookOrders`, { customer_ID: 1000 })
    expect(draft.status).to.equal(201)
    expect(draft.data.IsActiveEntity).to.equal(false)
  })

  it('⑬ 草稿：draftActivate → 201，触发 before-CREATE 自动编号', async () => {
    const draft = await POST(`${SVC}/BookOrders`, { customer_ID: 1000 })
    const url = `${SVC}/BookOrders(ID=${draft.data.ID},IsActiveEntity=false)/BookOrderService.draftActivate`
    const activated = await POST(url, {})
    expect(activated.status).to.equal(201)
    expect(activated.data.orderNo).to.equal('BO-1005')
  })

  it('⑭ 绑定动作：空订单提交 → 400', async () => {
    const orders = await GET(`${SVC}/BookOrders?$select=ID&$filter=orderNo eq 'BO-1005'`)
    const id = orders.data.value[0].ID
    const err = await fail(POST(`${SVC}/BookOrders(ID=${id},IsActiveEntity=true)/submitOrder`, {}))
    expect(err.response.status).to.equal(400)
  })

  it('⑮ 绑定动作：BO-1001 提交 → 200，状态迁移为 SUBMITTED', async () => {
    const orders = await GET(`${SVC}/BookOrders?$select=ID&$filter=orderNo eq 'BO-1001'`)
    const id = orders.data.value[0].ID
    const res = await POST(`${SVC}/BookOrders(ID=${id},IsActiveEntity=true)/submitOrder`, {})
    expect(res.status).to.equal(200)
    expect(res.data.value).to.contain('BO-1001')
    const after = await GET(`${SVC}/BookOrders(ID=${id},IsActiveEntity=true)?$select=status`)
    expect(after.data.status).to.equal('SUBMITTED')
  })

  it('⑯ 绑定动作：重复提交同一张订单 → 409', async () => {
    const orders = await GET(`${SVC}/BookOrders?$select=ID&$filter=orderNo eq 'BO-1001'`)
    const id = orders.data.value[0].ID
    const err = await fail(POST(`${SVC}/BookOrders(ID=${id},IsActiveEntity=true)/submitOrder`, {}))
    expect(err.response.status).to.equal(409)
  })
})
