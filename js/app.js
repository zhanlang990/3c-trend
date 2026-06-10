(function () {
  "use strict";

  var DATA_URL = "./data/news.json";

  // Stopwords (Chinese common words) to filter out from keyword stats
  var STOPWORDS = {
    "我们": 1, "你们": 1, "他们": 1, "什么": 1, "怎么": 1, "为什么": 1,
    "以及": 1, "通过": 1, "可以": 1, "已经": 1, "正在": 1, "成为": 1,
    "进入": 1, "增长": 1, "同比": 1, "环比": 1, "实现": 1, "用户": 1,
    "提供": 1, "需求": 1, "数据": 1, "公司": 1, "企业": 1, "产品": 1,
    "市场": 1, "行业": 1, "中国": 1, "国内": 1, "全国": 1, "国家": 1,
    "包括": 1, "采用": 1, "支持": 1, "提升": 1, "继续": 1, "目前": 1,
    "今年": 1, "今日": 1, "本次": 1, "本届": 1, "近日": 1, "日前": 1,
    "记者": 1, "报道": 1, "报告": 1, "消息": 1, "显示": 1, "表示": 1
  };

  var FEEDBACK_KEY = "safebox_feedback_v1";
  var HIDDEN_KEY = "safebox_hidden_v1";

  var CATEGORIES = ["公司财报", "行业报告", "媒体新闻", "招标信息"];

  var state = {
    all: [],
    source: "",
    keyword: "",
    category: "",
    query: "",
    catId: "3d-printing",  // current category tab id
  };

  // Category tabs configuration (loaded from categories.json or fallback)
  var CATEGORY_TABS = [
    { id: "3d-printing", name: "3D打印", icon: "🖨️" },
    { id: "uv-printing", name: "UV打印", icon: "🎨" },
    { id: "cnc", name: "CNC", icon: "⚙️" },
    { id: "ai-nas", name: "AI网络存储", icon: "💾" },
    { id: "ai-glasses", name: "AI眼镜", icon: "🥽" },
    { id: "ai-pc", name: "AIPC", icon: "🤖" },
    { id: "ai-phone", name: "AI手机", icon: "📱" },
    { id: "ai-learning", name: "AI学习硬件", icon: "📚" },
    { id: "safe-box", name: "保险柜", icon: "🔒" },
    { id: "4k-projector", name: "4K投影", icon: "🎬" },
    { id: "gaming-peripherals", name: "电竞键鼠", icon: "🎮" },
    { id: "monitor", name: "显示器", icon: "🖥️" },
    { id: "smart-watch", name: "时尚智能手表", icon: "⌚" },
    { id: "gaming-desktop", name: "游戏台式机", icon: "💻" },
    { id: "photography", name: "摄影摄像", icon: "📷" },
    { id: "surveillance", name: "监控摄像", icon: "📹" },
    { id: "speaker", name: "音箱", icon: "🔊" },
    { id: "magnetic-accessories", name: "磁吸配件", icon: "🧲" },
    { id: "foldable-phone", name: "折叠屏手机", icon: "📲" }
  ];

  // --- Hidden items (bad feedback → slide away, persist for all visitors) ---
  function loadHidden() {
    try { return JSON.parse(localStorage.getItem(HIDDEN_KEY)) || {}; }
    catch (e) { return {}; }
  }
  function saveHidden(data) {
    try { localStorage.setItem(HIDDEN_KEY, JSON.stringify(data)); } catch (e) {}
  }
  function hideItem(url) {
    var h = loadHidden();
    h[url] = true;
    saveHidden(h);
  }
  function isHidden(url) {
    return !!loadHidden()[url];
  }

  // --- Feedback (good/bad) persistence ---
  function loadFeedback() {
    try { return JSON.parse(localStorage.getItem(FEEDBACK_KEY)) || {}; }
    catch (e) { return {}; }
  }
  function saveFeedback(data) {
    try { localStorage.setItem(FEEDBACK_KEY, JSON.stringify(data)); } catch (e) {}
  }
  function recordFeedback(url, type) {
    var fb = loadFeedback();
    fb[url] = type;
    saveFeedback(fb);
  }
  function getFeedback(url) {
    return loadFeedback()[url] || "";
  }

  var $list = document.getElementById("news-list");
  var $empty = document.getElementById("empty-state");
  var $filter = document.getElementById("source-filter");
  var $keyword = document.getElementById("keyword-filter");
  var $category = document.getElementById("category-filter");
  var $search = document.getElementById("search-input");
  var $dateRange = document.getElementById("date-range");
  var $catTabs = document.getElementById("category-tabs");

  function escapeHtml(s) {
    if (s == null) return "";
    var div = document.createElement("div");
    div.textContent = String(s);
    return div.innerHTML.replace(/"/g, "&#34;").replace(/'/g, "&#39;");
  }

  // Get all sources of an item, normalized to an array.
  function getItemSources(it) {
    if (Array.isArray(it.sources) && it.sources.length) return it.sources;
    if (it.source) return [it.source];
    return [];
  }

  function uniqueSources(items) {
    var set = {};
    items.forEach(function (it) {
      getItemSources(it).forEach(function (s) {
        if (s) set[s] = true;
      });
    });
    return Object.keys(set);
  }

  function uniqueCategories(items) {
    var set = {};
    items.forEach(function (it) {
      var cat = it.category || "媒体新闻";
      if (cat) set[cat] = true;
    });
    // Ensure predefined categories appear even if no data
    CATEGORIES.forEach(function (c) { set[c] = true; });
    return CATEGORIES.filter(function (c) { return set[c]; });
  }

  // Tokenize Chinese text into 2-4 char n-grams (simple but effective).
  // Combined with stopwords + min-frequency filter to extract topical words.
  function tokenizeCJK(text) {
    if (!text) return [];
    var tokens = [];
    // Strip non-CJK / non-alnum noise
    var clean = String(text).replace(/[\s\.,;:'"()\[\]{}<>\/\\!?@#$%^&*+=|`~\-_·。,；：、！？""''《》【】（）]/g, "");
    // Use 2-gram by default; long brand/product words (3-4 char) handled below
    for (var i = 0; i < clean.length - 1; i++) {
      var two = clean.substr(i, 2);
      if (/^[\u4e00-\u9fa5A-Za-z0-9]{2}$/.test(two)) tokens.push(two);
    }
    return tokens;
  }

  // Pull explicit matched_keywords first; fall back to n-gram statistics.
  function computeTopKeywords(items, topN) {
    var freq = {};

    // Helper: drop tokens that are purely digits/punctuation/units, or whose
    // digit ratio is too high (e.g. "618", "20", "30cm", "2026").
    function isNumericLike(s) {
      if (!s) return true;
      // pure digits / digits + common units
      if (/^[0-9]+$/.test(s)) return true;
      if (/^[0-9]+(年|月|日|cm|mm|kg|元|倍|%|L|号)$/i.test(s)) return true;
      // count digit chars
      var digitCount = (s.match(/[0-9]/g) || []).length;
      if (digitCount && digitCount / s.length >= 0.5) return true;
      return false;
    }

    // (1) Explicit keywords from data weigh more (×3 boost)
    items.forEach(function (it) {
      (it.matched_keywords || []).forEach(function (kw) {
        if (!kw) return;
        kw = String(kw).trim();
        if (!kw || STOPWORDS[kw]) return;
        if (isNumericLike(kw)) return;
        freq[kw] = (freq[kw] || 0) + 3;
      });
    });

    // (2) Add n-gram statistics from title + summary
    items.forEach(function (it) {
      var text = (it.title || "") + " " + (it.summary || "");
      var grams = tokenizeCJK(text);
      var seen = {};
      grams.forEach(function (g) {
        if (STOPWORDS[g]) return;
        if (isNumericLike(g)) return;
        // count once per item to avoid one article dominating
        if (seen[g]) return;
        seen[g] = true;
        freq[g] = (freq[g] || 0) + 1;
      });
    });

    var list = Object.keys(freq).map(function (k) {
      return { word: k, count: freq[k] };
    });
    // Filter low-signal: count >= 2 OR length >= 3 (preserve named keywords)
    list = list.filter(function (e) {
      return e.count >= 2 || e.word.length >= 3;
    });
    list.sort(function (a, b) {
      if (b.count !== a.count) return b.count - a.count;
      return b.word.length - a.word.length;
    });
    return list.slice(0, topN || 20).map(function (e) { return e.word; });
  }

  function renderFilter(sources) {
    var html = '<button class="chip chip-active" data-source="">全部</button>';
    sources.forEach(function (s) {
      html += '<button class="chip" data-source="' + escapeHtml(s) + '">' + escapeHtml(s) + "</button>";
    });
    $filter.innerHTML = html;
    Array.prototype.forEach.call($filter.querySelectorAll(".chip"), function (btn) {
      btn.addEventListener("click", function () {
        state.source = btn.getAttribute("data-source") || "";
        Array.prototype.forEach.call($filter.querySelectorAll(".chip"), function (b) {
          b.classList.toggle("chip-active", b === btn);
        });
        applyFilters();
      });
    });
  }

  function renderKeywordFilter(keywords) {
    if (!$keyword) return;
    var html = '<button class="chip chip-keyword chip-active" data-keyword="">全部</button>';
    keywords.forEach(function (k) {
      html += '<button class="chip chip-keyword" data-keyword="' + escapeHtml(k) + '"># ' + escapeHtml(k) + "</button>";
    });
    $keyword.innerHTML = html;
    Array.prototype.forEach.call($keyword.querySelectorAll(".chip"), function (btn) {
      btn.addEventListener("click", function () {
        state.keyword = btn.getAttribute("data-keyword") || "";
        Array.prototype.forEach.call($keyword.querySelectorAll(".chip"), function (b) {
          b.classList.toggle("chip-active", b === btn);
        });
        applyFilters();
      });
    });
  }

  function renderCategoryFilter(categories) {
    if (!$category) return;
    var html = '<button class="chip chip-cat chip-active" data-category="">全部</button>';
    categories.forEach(function (c) {
      html += '<button class="chip chip-cat" data-category="' + escapeHtml(c) + '">' + escapeHtml(c) + "</button>";
    });
    $category.innerHTML = html;
    Array.prototype.forEach.call($category.querySelectorAll(".chip"), function (btn) {
      btn.addEventListener("click", function () {
        state.category = btn.getAttribute("data-category") || "";
        Array.prototype.forEach.call($category.querySelectorAll(".chip"), function (b) {
          b.classList.toggle("chip-active", b === btn);
        });
        applyFilters();
      });
    });
  }

  function initCategoryTabs() {
    if (!$catTabs) return;
    var html = "";
    CATEGORY_TABS.forEach(function (tab) {
      html += '<button class="tab-btn' + (tab.id === state.catId ? " tab-active" : "") + '" data-cat="' + escapeHtml(tab.id) + '">' + tab.icon + " " + escapeHtml(tab.name) + "</button>";
    });
    $catTabs.innerHTML = html;
    Array.prototype.forEach.call($catTabs.querySelectorAll(".tab-btn"), function (btn) {
      btn.addEventListener("click", function () {
        state.catId = btn.getAttribute("data-cat") || "";
        Array.prototype.forEach.call($catTabs.querySelectorAll(".tab-btn"), function (b) {
          b.classList.toggle("tab-active", b === btn);
        });
        applyFilters();
      });
    });
  }

  function renderStats(data) {
    // Show date range: yesterday minus 6 days to yesterday (YYMMDD-YYMMDD)
    var now = new Date();
    var yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
    var startDay = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 7);
    var fmt = function(d) {
      var yy = String(d.getFullYear()).slice(2);
      var mm = String(d.getMonth() + 1).padStart(2, "0");
      var dd = String(d.getDate()).padStart(2, "0");
      return yy + mm + dd;
    };
    $dateRange.textContent = fmt(startDay) + "-" + fmt(yesterday) + " 行业资讯";
  }

  function sourceBadgesHtml(it) {
    var arr = getItemSources(it);
    if (!arr.length) return '<span class="news-source">未知来源</span>';
    return arr.map(function (s) {
      return '<span class="news-source">' + escapeHtml(s) + "</span>";
    }).join("");
  }

  function cardHtml(it) {
    var url = it.url || "#";
    var brief = it.info_brief || "";
    var opp = it.opportunity_insight || "";
    var insight = it.procurement_insight || "";
    var summary = it.summary || "";

    function block(cls, label, icon, text) {
      if (!text) return "";
      return (
        '<div class="' + cls + '">' +
          '<span class="block-tag">' + icon + " " + label + "</span>" +
          escapeHtml(text) +
        "</div>"
      );
    }

    return (
      '<div class="news-card" data-url="' + escapeHtml(url) + '">' +
        '<div class="card-body">' +
          block("news-brief", "信息摘要", "📌", brief) +
          block("news-opportunity", "机会洞察", "🎯", opp) +
          block("news-insight", "操盘建议", "💡", insight) +
          '<div class="news-meta">' +
            '<div class="news-sources">' + sourceBadgesHtml(it) + "</div>" +
            '<span class="news-date">' + escapeHtml(it.publish_date || "") + "</span>" +
          "</div>" +
          '<h3 class="news-title"><a class="title-link" href="' + escapeHtml(url) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(it.title || "") + "</a></h3>" +
          (summary ? '<p class="news-summary">' + escapeHtml(summary) + "</p>" : "") +
        "</div>" +
        '<div class="card-feedback">' +
          '<button class="fb-btn fb-good' + (getFeedback(url) === "good" ? " fb-active" : "") + '" data-url="' + escapeHtml(url) + '" data-type="good" title="有价值，多抓此类资讯">👍 有价值</button>' +
          '<button class="fb-btn fb-bad' + (getFeedback(url) === "bad" ? " fb-active" : "") + '" data-url="' + escapeHtml(url) + '" data-type="bad" title="不相关，减少此类资讯">👎 不相关</button>' +
        "</div>" +
      "</div>"
    );
  }

  function renderList(items) {
    if (!items.length) {
      $list.innerHTML = "";
      $empty.hidden = false;
      return;
    }
    $empty.hidden = true;
    $list.innerHTML = items.map(cardHtml).join("");
    // Bind feedback buttons
    $list.querySelectorAll(".fb-btn").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        e.preventDefault();
        var url = btn.getAttribute("data-url");
        var type = btn.getAttribute("data-type");
        var prev = getFeedback(url);
        if (type === "bad") {
          // Record bad feedback and hide the card with slide animation
          recordFeedback(url, "bad");
          hideItem(url);
          var card = btn.closest(".news-card");
          if (card) {
            card.classList.add("card-slide-out");
            card.addEventListener("animationend", function () {
              card.remove();
              // Check if list is now empty
              if (!$list.children.length) {
                $empty.hidden = false;
              }
            });
          }
        } else if (type === "good") {
          // Toggle good
          if (prev === "good") {
            recordFeedback(url, "");
            btn.classList.remove("fb-active");
          } else {
            recordFeedback(url, "good");
            var card2 = btn.closest(".news-card");
            card2.querySelectorAll(".fb-btn").forEach(function (b) {
              b.classList.toggle("fb-active", b.getAttribute("data-type") === "good");
            });
          }
        }
      });
    });
  }

  function sortByDateDesc(items) {
    return items.slice().sort(function (a, b) {
      var ad = a.publish_date || "";
      var bd = b.publish_date || "";
      if (ad < bd) return 1;
      if (ad > bd) return -1;
      return 0;
    });
  }

  function applyFilters() {
    var src = state.source;
    var kw = state.keyword;
    var cat = state.category;
    var q = (state.query || "").trim().toLowerCase();
    var catId = state.catId;
    var hidden = loadHidden();
    var filtered = state.all.filter(function (it) {
      // Hide items marked as "bad" (swiped away)
      if (hidden[it.url]) return false;
      // Filter by category tab (category_id)
      if (catId) {
        var itemCatId = it.category_id || "";
        if (itemCatId !== catId) return false;
      }
      if (cat) {
        var itemCat = it.category || "媒体新闻";
        if (itemCat !== cat) return false;
      }
      if (src) {
        var arr = getItemSources(it);
        if (arr.indexOf(src) === -1) return false;
      }
      if (kw) {
        var hay = ((it.title || "") + " " + (it.summary || "") + " " + (it.matched_keywords || []).join(" "));
        if (hay.indexOf(kw) === -1) return false;
      }
      if (q) {
        var hay2 = ((it.title || "") + " " + (it.summary || "")).toLowerCase();
        if (hay2.indexOf(q) === -1) return false;
      }
      return true;
    });
    renderList(filtered);
  }

  function init(data) {
    var items = (data && data.items) || [];
    items = sortByDateDesc(items);
    state.all = items;
    initCategoryTabs();
    renderStats(data || {});
    renderCategoryFilter(uniqueCategories(items));
    renderKeywordFilter(computeTopKeywords(items, 20));
    renderFilter(uniqueSources(items));
    renderList(items);
    $search.addEventListener("input", function () {
      state.query = $search.value || "";
      applyFilters();
    });
  }

  function loadJson(url) {
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  // Prefer inlined window.__NEWS_DATA__ (works under file://); otherwise fetch.
  if (window.__NEWS_DATA__) {
    init(window.__NEWS_DATA__);
  } else {
    loadJson(DATA_URL)
      .catch(function () { return loadJson("./data/news.sample.json"); })
      .then(init)
      .catch(function (err) {
        $list.innerHTML = "";
        $empty.hidden = false;
        $empty.querySelector("p").textContent = "新闻数据加载失败 😢";
        $empty.querySelector(".empty-tip").textContent = "请检查 data/news.json 是否存在或网络是否通畅：" + err.message;
      });
  }

  // --- Export feedback button ---
  var $exportBtn = document.getElementById("export-feedback-btn");
  if ($exportBtn) {
    $exportBtn.addEventListener("click", function () {
      var fb = loadFeedback();
      var count = Object.keys(fb).length;
      if (count === 0) {
        alert("暂无反馈数据。请先点击卡片旁的 👍有价值 / 👎不相关 按钮。");
        return;
      }
      var jsonStr = JSON.stringify(fb, null, 2);
      // Copy to clipboard
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(jsonStr).then(function () {
          alert("已复制 " + count + " 条反馈数据到剪贴板！\n\n请将剪贴板内容保存为 data/feedback.json，\n下次运行爬虫时会自动优化抓取优先级。");
        });
      } else {
        // Fallback: open in new window
        var w = window.open("", "_blank");
        w.document.write("<pre>" + jsonStr + "</pre>");
        alert("已在新窗口打开 " + count + " 条反馈数据。\n\n请复制内容保存为 data/feedback.json，\n下次运行爬虫时会自动优化抓取优先级。");
      }
    });
  }
})();