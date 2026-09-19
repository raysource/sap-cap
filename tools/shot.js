#!/usr/bin/env node
/**
 * shot.js — 用 CDP 给本地运行中的应用拍真实截图（本站「本地实机运行」图就是它产出的）。
 *
 * 为什么不用 `chrome --screenshot`：那个开关在页面还在异步加载（UI5 要加载几百个模块）
 * 时就截了，经常得到一张白图；用 CDP 可以「等到页面上真的出现指定内容」再截图。
 *
 * 用法:
 *   node tools/shot.js --url http://localhost:4005/book-orders/webapp/index.html \
 *                      --wait "BO-1001" --out assets/fig/real/fiori_list_report.png \
 *                      [--size 1600x1000] [--delay 2500] [--port 9222]
 *
 * 依赖 Node 18+（用到全局 fetch 与 WebSocket）。Chrome 用 --remote-debugging-port 启动。
 */
const fs = require('fs');
const { spawn } = require('child_process');

const args = parse(process.argv.slice(2));
const PORT = Number(args.port || 9222);
const URL_ = args.url;
const OUT = args.out || 'shot.png';
const WAIT = args.wait || null;
const DELAY = Number(args.delay || 2000);
const [W, H] = (args.size || '1600x1000').split('x').map(Number);
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

function parse(a) {
  const o = {};
  for (let i = 0; i < a.length; i += 2) o[a[i].replace(/^--/, '')] = a[i + 1];
  return o;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const profile = fs.mkdtempSync('/tmp/shot-profile-');
  const chrome = spawn(CHROME, [
    '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
    `--remote-debugging-port=${PORT}`, `--window-size=${W},${H}`,
    `--user-data-dir=${profile}`, 'about:blank',
  ], { stdio: 'ignore', detached: false });
  console.error(`chrome headless :${PORT} window ${W}x${H} profile ${profile}`);

  let ws, id = 0;
  const pending = new Map();
  const send = (method, params = {}) => new Promise((res, rej) => {
    const msgId = ++id;
    pending.set(msgId, { res, rej });
    ws.send(JSON.stringify({ id: msgId, method, params }));
  });

  try {
    // wait for the debugger endpoint
    let target = null;
    for (let i = 0; i < 40 && !target; i++) {
      await sleep(250);
      try {
        const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
        target = list.find((t) => t.type === 'page');
      } catch { /* not up yet */ }
    }
    if (!target) throw new Error('Chrome devtools endpoint did not come up');

    ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    ws.onmessage = (m) => {
      const msg = JSON.parse(m.data);
      if (msg.id && pending.has(msg.id)) {
        const { res, rej } = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result);
      }
    };

    await send('Page.enable');
    await send('Runtime.enable');
    // headless 里页面默认可能被当作「不可见」，而 UI5 用 requestAnimationFrame 渲染 —— 不可见
    // 就不会绘制，截出来是空白的背景色。把生命周期设为 active 并伪造 visibilityState 即可。
    try { await send('Page.setWebLifecycleState', { state: 'active' }); } catch { /* older chrome */ }
    await send('Page.navigate', { url: URL_ });

    let ok = false;
    for (let i = 0; i < 60; i++) {                       // ≤ 30 s
      await sleep(500);
      const probe = WAIT
        ? `document.body.innerText.includes(${JSON.stringify(WAIT)})`
        : 'document.readyState === "complete"';
      const r = await send('Runtime.evaluate', { expression: probe, returnByValue: true });
      if (r.result && r.result.value === true) { ok = true; break; }
    }
    // 让 UI5 认为页面可见并重新布局（Fiori Elements 的 DynamicPage 依赖可视尺寸）
    await send('Runtime.evaluate', {
      expression: `
        try {
          Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true });
          Object.defineProperty(document, 'hidden', { value: false, configurable: true });
          document.dispatchEvent(new Event('visibilitychange'));
        } catch (e) {}
        window.dispatchEvent(new Event('resize'));
        try { sap.ui.getCore().getEventBus().publish('sap.ui', 'resize', ''); } catch (e) {}
        1;`,
    });
    await sleep(DELAY);
    if (args.probe) {
      const r = await send('Runtime.evaluate', {
        returnByValue: true,
        expression: `
          (() => {
            const pick = (sel) => {
              const el = document.querySelector(sel);
              if (!el) return null;
              const b = el.getBoundingClientRect();
              return { sel, x: Math.round(b.x), y: Math.round(b.y),
                       w: Math.round(b.width), h: Math.round(b.height),
                       cls: el.className && String(el.className).slice(0, 60) };
            };
            return {
              viewport: { w: innerWidth, h: innerHeight, vis: document.visibilityState },
              html: document.documentElement.getBoundingClientRect().height,
              body: document.body.getBoundingClientRect().height,
              bodyCls: document.body.className,
              textLen: document.body.innerText.length,
              textHead: document.body.innerText.slice(0, 120),
              boxes: ['#container', '.sapUiBody', '#book-orders', '.sapMShell',
                      '.sapFDynamicPage', '.sapMListTbl', '.sapMTable'].map(pick).filter(Boolean),
              styles: (() => {
                const c = document.querySelector('#container');
                if (!c) return null;
                const s = getComputedStyle(c);
                return { height: s.height, display: s.display, overflow: s.overflow, position: s.position };
              })()
            };
          })()`,
      });
      console.log(JSON.stringify(r.result.value, null, 1));
    }
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
    fs.writeFileSync(OUT, Buffer.from(shot.data, 'base64'));
    console.log(`${ok ? 'ready' : 'TIMEOUT(wait text not found)'}  ->  ${OUT}  ` +
                `${(fs.statSync(OUT).size / 1024).toFixed(0)} KB`);
    process.exitCode = ok ? 0 : 1;
  } finally {
    try { ws && ws.close(); } catch {}
    try { chrome.kill('SIGKILL'); } catch {}
  }
}

main().catch((e) => { console.error('shot.js failed:', e.message); process.exit(1); });
