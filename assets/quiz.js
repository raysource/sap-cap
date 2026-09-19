/* ============================================================
   RAP 培训站 - 能力测试脚本
   自动评分: 点击选项 -> 立即判分 -> 显示解说 -> 汇总得分
   ============================================================ */
(function () {
  "use strict";

  function scoreBox() {
    var sb = document.getElementById("quiz-score");
    if (sb) return sb;
    var div = document.createElement("div");
    div.id = "quiz-score";
    div.className = "panel";
    div.style.cssText = "position:sticky;top:76px;z-index:30;";
    div.innerHTML =
      '<b class="t">成绩</b>' +
      '<div class="scorebar"><i id="quiz-bar" style="width:0%"></i></div>' +
      '<p id="quiz-text" style="margin:4px 0 0">尚未作答 / 共 0 题</p>';
    var wrap = document.querySelector("main.page .wrap article") ||
               document.querySelector("main.page") ||
               document.body;
    wrap.insertBefore(div, wrap.firstChild);
    return div;
  }

  function refresh() {
    var qs = document.querySelectorAll(".quiz-q");
    var total = qs.length;
    var done = 0, correct = 0;
    qs.forEach(function (q) {
      if (q.classList.contains("answered")) done++;
      if (q.classList.contains("right")) correct++;
    });
    var pct = total ? Math.round(correct / total * 100) : 0;
    var bar = document.getElementById("quiz-bar");
    if (bar) bar.style.width = pct + "%";
    var txt = document.getElementById("quiz-text");
    if (!txt) return;
    var grade = "";
    if (total && done === total) {
      grade = pct >= 90 ? " ★★★ 优秀 (90%+)" :
              pct >= 75 ? " ★★☆ 良好 (75%+)" :
              pct >= 60 ? " ★☆☆ 及格 (60%+)" : " ✗ 未达标 (<60%) —— 请回到对应手顺篇复习";
    }
    txt.innerHTML = "已答 " + done + " / " + total +
      " · 正确 " + correct + " · 正确率 " + pct + "% " + grade;
  }

  document.addEventListener("click", function (e) {
    var opt = e.target.closest(".opt");
    if (!opt) return;
    var q = opt.closest(".quiz-q");
    if (!q || q.classList.contains("answered")) return;
    var answer = (q.getAttribute("data-answer") || "").trim().toUpperCase();
    var key = (opt.getAttribute("data-key") || "").trim().toUpperCase();
    q.classList.add("answered");
    if (key === answer) {
      q.classList.add("right");
      opt.classList.add("correct");
    } else {
      opt.classList.add("wrong");
      q.querySelectorAll(".opt").forEach(function (o) {
        if ((o.getAttribute("data-key") || "").trim().toUpperCase() === answer) {
          o.classList.add("correct");
        }
      });
    }
    q.classList.add("show-exp");
    refresh();
  });

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-reset]");
    if (!btn) return;
    document.querySelectorAll(".quiz-q").forEach(function (q) {
      q.classList.remove("answered", "right", "wrong", "show-exp");
      q.querySelectorAll(".opt").forEach(function (o) {
        o.classList.remove("correct", "wrong");
      });
    });
    refresh();
  });

  document.addEventListener("DOMContentLoaded", function () {
    if (document.querySelector(".quiz-q")) {
      scoreBox();
      refresh();
      var reset = document.createElement("button");
      reset.className = "copy-btn";
      reset.setAttribute("data-reset", "1");
      reset.textContent = "全部重做 ↺";
      reset.style.cssText = "margin:0 0 4px 8px;background:#2a4154;";
      var h = document.querySelector(".quiz-q .q-meta");
      var firstQ = document.querySelector(".quiz-q");
      if (firstQ) {
        var host = firstQ.parentNode;
        var p = document.createElement("p");
        p.appendChild(reset);
        host.insertBefore(p, firstQ);
      }
    }
  });
})();
