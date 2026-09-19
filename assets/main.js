/* ============================================================
   SAP BTP 开发者训练站 - 交互脚本
   - 代码块: 一键复制 + 轻量语法高亮(无外部依赖)
   - 返回顶部、页脚年份
   ============================================================ */
(function () {
  "use strict";

  /* ---------- 代码复制 ---------- */
  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".copy-btn");
    if (!btn) return;
    var pre = btn.closest("pre.hl");
    if (!pre) return;
    var text = pre.querySelector("code").innerText;
    var done = function () {
      var old = btn.textContent;
      btn.textContent = "已复制 ✓";
      setTimeout(function () { btn.textContent = old; }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
    } else { fallbackCopy(text); done(); }
  });
  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (err) {}
    document.body.removeChild(ta);
  }

  /* ---------- 轻量语法高亮 ----------
     分词顺序: 注释 -> 字符串 -> 标记(标签/属性/@注解/关键字/数字)
     只针对 <pre class="hl"> 中的 <code class="lang-xxx"> */
  var KEYWORDS = {
    js: ["function", "return", "var", "let", "const", "if", "else", "for", "while", "new", "this", "typeof", "async", "await", "try", "catch", "throw", "class", "extends", "null", "true", "false"],
    java: ["public", "private", "protected", "class", "interface", "extends", "implements", "void", "static", "final", "new", "return", "if", "else", "for", "while", "switch", "case", "break", "continue", "try", "catch", "throw", "import", "package", "this", "null", "true", "false", "boolean", "int", "long", "double", "String", "var", "record", "default", "enum", "instanceof"],
    abap: ["define", "entity", "view", "as", "select", "from", "where", "key", "managed", "implementation", "in", "class", "unique", "abstract", "root", "projection", "using", "for", "read", "modify", "on", "save", "field", "fields", "with", "create", "update", "delete", "action", "function", "result", "validation", "determination", "association", "to", "many", "one", "composite", "internal", "public", "section", "methods", "method", "endmethod", "data", "type", "types", "if", "endif", "else", "loop", "endloop", "importing", "exporting", "changing", "returning", "value", "abap_true", "abap_false", "new", "raise", "exception", "catch", "is", "not", "and", "or", "struct", "for", "strict"],
    cds: ["entity", "service", "using", "from", "as", "key", "projection", "on", "actions", "function", "aspect", "type", "many", "one", "to", "association", "compositions", "composition", "extend", "namespace", "annotate", "with", "true", "false", "null", "cuid", "managed", "localized", "array", "of", "select", "where", "order", "by", "limit", "group", "having", "in", "exists", "not", "and", "or", "between", "like"],
    groovy: ["def", "return", "if", "else", "for", "while", "new", "import", "class", "void", "static", "public", "private", "this", "null", "true", "false", "in", "as", "throw", "try", "catch", "finally", "switch", "case", "break", "continue", "each"],
    xml: [],
    yaml: [],
    sql: ["select", "from", "where", "and", "or", "order", "by", "insert", "into", "values", "update", "set", "delete", "create", "table", "key", "not", "null", "as", "join", "on", "group", "having", "limit", "distinct", "count", "sum", "min", "max", "like", "in", "exists", "inner", "left", "right"],
    bash: []
  };
  var COMMENT_OPEN = {
    js: ["//", "/*"], java: ["//", "/*"], groovy: ["//", "/*"], cds: ["//"], abap: ['"', "/*"], sql: ["--", "/*"], bash: ["#"], yaml: ["#"], xml: ["<!--"], json: []
  };
  var COMMENT_CLOSE = { "/*": "*/", "<!--": "-->" };

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function span(cls, inner) { return '<span class="tok-' + cls + '">' + inner + "</span>"; }

  function highlight(code, lang) {
    var kw = KEYWORDS[lang] || [];
    var openers = COMMENT_OPEN[lang] || [];
    var i = 0, out = "", n = code.length;

    function isKw(w) {
      if (kw.indexOf(w) < 0) return false;
      if (i + w.length < n && /[A-Za-z0-9_]/.test(code[i + w.length])) return false;
      if (i > 0 && /[A-Za-z0-9_]/.test(code[i - 1])) return false;
      return true;
    }

    while (i < n) {
      var c = code[i];

      /* 注释 */
      var cm = null;
      for (var k = 0; k < openers.length; k++) {
        if (code.startsWith(openers[k], i)) { cm = openers[k]; break; }
      }
      if (cm) {
        var ce = COMMENT_CLOSE[cm] || "\n";
        var j = code.indexOf(ce, i + cm.length);
        var end = j < 0 ? n : j + ce.length;
        out += span("c", esc(code.slice(i, end)));
        i = end;
        continue;
      }

      /* 字符串 */
      if (c === '"' || c === "'" || c === "`") {
        var q = c, j2 = i + 1, escaped = false;
        while (j2 < n) {
          var c2 = code[j2];
          if (c2 === "\\") { j2 += 2; continue; }
          if (c2 === q) { j2++; break; }
          j2++;
        }
        out += span("s", esc(code.slice(i, j2)));
        i = j2;
        continue;
      }

      /* 标记语言标签: <xxx ...> */
      if (lang === "xml" && c === "<") {
        var m = /^<\/?[A-Za-z0-9_:.-]+/.exec(code.slice(i));
        if (m) {
          var whole = /^<[^>"']*("(\\.|[^"\\])*"|'(\\.|[^'\\])*')*[^>"']*>/.exec(code.slice(i));
          if (whole) {
            var tag = whole[0];
            var pretty = tag.replace(/([A-Za-z_:][A-Za-z0-9_:.-]*)(=)("[^"]*"|'[^']*')/g, function (mm, name, eq, val) {
              return span("a", name) + span("o", eq) + span("s", val);
            });
            if (/^<!/.test(tag)) { pretty = tag; }
            else if (/^<\//.test(tag)) {
              var nameM = /^<\/?([A-Za-z0-9_:.-]+)/.exec(tag);
              pretty = "&lt;/" + span("t", nameM[1]) + "&gt;";
            } else {
              var nameM2 = /^<\/?([A-Za-z0-9_:.-]+)/.exec(tag);
              pretty = "&lt;" + span("t", nameM2[1]) + pretty.slice(nameM2[1].length + 1, -1) + "&gt;";
              /* 简化: 上面整块替换不可靠时退回原样 */
              if (pretty.indexOf("&lt;") !== 0) pretty = esc(tag);
            }
            out += span("t", pretty.replace(/^&lt;|&gt;$/g, ""));
            i += tag.length;
            continue;
          }
        }
      }

      /* @注解 / @title */
      if (c === "@" && /[A-Za-z]/.test(code[i + 1] || "")) {
        var m2 = /@[A-Za-z0-9_.:-]+/.exec(code.slice(i));
        if (m2) { out += span("an", m2[0]); i += m2[0].length; continue; }
      }

      /* 数字 */
      if (/[0-9]/.test(c) && (i === 0 || !/[A-Za-z0-9_.]/.test(code[i - 1]))) {
        var m3 = /(\$)?[0-9]+(?:\.[0-9]+)?/.exec(code.slice(i));
        if (m3) { out += span("n", m3[0]); i += m3[0].length; continue; }
      }

      /* 关键字 */
      if (/[A-Za-z_]/.test(c)) {
        var m4 = /[A-Za-z_][A-Za-z0-9_]*/.exec(code.slice(i));
        if (m4) {
          var w = m4[0];
          if (isKw(w)) { out += span("k", w); }
          else { out += esc(w); }
          i += w.length;
          continue;
        }
      }

      /* 其它: 注意要在输出前转义 */
      out += esc(c);
      i++;
    }
    return out;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var pres = document.querySelectorAll("pre.hl code[class^='lang-']");
    for (var i = 0; i < pres.length; i++) {
      var el = pres[i];
      var lang = /lang-([a-z0-9]+)/.exec(el.className);
      if (!lang) continue;
      var raw = el.textContent;
      if (lang[1] === "text") continue;
      el.innerHTML = highlight(raw, lang[1]);
    }

    /* 返回顶部 */
    var tt = document.createElement("button");
    tt.className = "to-top";
    tt.setAttribute("aria-label", "返回顶部");
    tt.innerHTML = "↑";
    document.body.appendChild(tt);
    tt.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: "smooth" }); });
    window.addEventListener("scroll", function () {
      if (window.scrollY > 400) tt.classList.add("show");
      else tt.classList.remove("show");
    });

    /* 页脚年份 */
    var y = document.querySelector("[data-year]");
    if (y) y.textContent = new Date().getFullYear();
  });
})();
