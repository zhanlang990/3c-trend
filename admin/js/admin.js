(function () {
  "use strict";

  // Default categories config (fallback)
  var DEFAULT_CATEGORIES = {
    categories: [
      {
        id: "safe-box", name: "保险柜", icon: "🔒",
        keywords: ["保险柜", "保险箱", "保管箱", "防盗保险箱", "家用保险柜", "智能保险柜", "安防柜", "床头柜", "收纳箱", "收纳柜", "储物柜"],
        sources: [
          { id: "sina", name: "新浪家居", type: "search", search_url: "https://search.sina.com.cn/?q={keyword}&c=news&from=channel&ie=utf-8", enabled: true },
          { id: "netease", name: "网易家居", type: "search", search_url: "https://www.163.com/search?keyword={keyword}", enabled: true },
          { id: "china", name: "中华网", type: "search", search_url: "https://so.china.com/cse/search?q={keyword}", enabled: true },
          { id: "pchouse", name: "太平洋家居", type: "search", enabled: true },
          { id: "sohu", name: "搜狐", type: "search", enabled: true },
          { id: "aipu", name: "艾谱官网", type: "html_list", enabled: true },
          { id: "chinairn", name: "中研网", type: "search", enabled: true },
          { id: "taobao-baike", name: "淘宝百科", type: "search", enabled: true }
        ],
        info_types: ["公司财报", "行业报告", "媒体新闻", "招标信息"]
      },
      {
        id: "phone", name: "手机", icon: "📱",
        keywords: ["手机", "智能手机", "5G手机", "折叠屏", "旗舰手机"],
        sources: [
          { id: "ithome", name: "IT之家", type: "search", enabled: true },
          { id: "cnbeta", name: "cnBeta", type: "search", enabled: true },
          { id: "mydrivers", name: "快科技", type: "search", enabled: true }
        ],
        info_types: ["公司财报", "行业报告", "媒体新闻", "招标信息"]
      },
      {
        id: "laptop", name: "笔记本", icon: "💻",
        keywords: ["笔记本", "笔记本电脑", "游戏本", "轻薄本", "商务本"],
        sources: [
          { id: "ithome", name: "IT之家", type: "search", enabled: true },
          { id: "zol", name: "中关村在线", type: "search", enabled: true },
          { id: "pconline", name: "太平洋电脑", type: "search", enabled: true }
        ],
        info_types: ["公司财报", "行业报告", "媒体新闻", "招标信息"]
      },
      {
        id: "tablet", name: "平板", icon: "📲",
        keywords: ["平板电脑", "平板", "iPad", "安卓平板", "学习平板"],
        sources: [
          { id: "ithome", name: "IT之家", type: "search", enabled: true },
          { id: "zol", name: "中关村在线", type: "search", enabled: true }
        ],
        info_types: ["公司财报", "行业报告", "媒体新闻", "招标信息"]
      },
      {
        id: "wearable", name: "穿戴设备", icon: "⌚",
        keywords: ["智能手表", "手环", "穿戴设备", "健康监测", "运动手环"],
        sources: [
          { id: "ithome", name: "IT之家", type: "search", enabled: true },
          { id: "sohu", name: "搜狐", type: "search", enabled: true }
        ],
        info_types: ["公司财报", "行业报告", "媒体新闻", "招标信息"]
      },
      {
        id: "smart-home", name: "智能家居", icon: "🏠",
        keywords: ["智能家居", "智能门锁", "智能照明", "扫地机器人", "智能音箱"],
        sources: [
          { id: "sina", name: "新浪家居", type: "search", enabled: true },
          { id: "pchouse", name: "太平洋家居", type: "search", enabled: true },
          { id: "sohu", name: "搜狐", type: "search", enabled: true }
        ],
        info_types: ["公司财报", "行业报告", "媒体新闻", "招标信息"]
      },
      {
        id: "audio", name: "音频设备", icon: "🎧",
        keywords: ["耳机", "蓝牙耳机", "降噪耳机", "音箱", "智能音箱"],
        sources: [
          { id: "ithome", name: "IT之家", type: "search", enabled: true },
          { id: "zol", name: "中关村在线", type: "search", enabled: true }
        ],
        info_types: ["公司财报", "行业报告", "媒体新闻", "招标信息"]
      }
    ]
  };

  var config = null;

  function escapeHtml(s) {
    if (s == null) return "";
    var div = document.createElement("div");
    div.textContent = String(s);
    return div.innerHTML;
  }

  function loadConfig() {
    // Try to load from localStorage first, then use defaults
    try {
      var saved = localStorage.getItem("3c_categories_config");
      if (saved) {
        config = JSON.parse(saved);
        return;
      }
    } catch (e) {}
    config = JSON.parse(JSON.stringify(DEFAULT_CATEGORIES));
  }

  function saveConfigLocal() {
    try {
      localStorage.setItem("3c_categories_config", JSON.stringify(config));
    } catch (e) {}
  }

  function renderCategories() {
    var $list = document.getElementById("cat-list");
    if (!config || !config.categories || !config.categories.length) {
      $list.innerHTML = '<div class="empty-msg">暂无品类配置，请点击"添加品类"</div>';
      return;
    }
    $list.innerHTML = config.categories.map(function (cat, idx) {
      return renderCategoryItem(cat, idx);
    }).join("");
  }

  function renderCategoryItem(cat, idx) {
    var kwHtml = (cat.keywords || []).map(function (kw, ki) {
      return '<span class="tag">' + escapeHtml(kw) + ' <span class="remove" onclick="removeKeyword(' + idx + ',' + ki + ')">×</span></span>';
    }).join("");

    var srcHtml = (cat.sources || []).map(function (src, si) {
      return '<div class="source-item">' +
        '<span class="sname">' + escapeHtml(src.name) + '</span>' +
        '<span class="sid">(' + escapeHtml(src.id) + ')</span>' +
        '<span class="stype">' + escapeHtml(src.type || "search") + '</span>' +
        (src.enabled ? "" : '<span style="color:#EF4444;font-size:12px;">已禁用</span>') +
        '<span class="sactions">' +
          '<button class="btn-sm" onclick="toggleSource(' + idx + ',' + si + ')">' + (src.enabled ? "禁用" : "启用") + '</button>' +
          '<button class="btn-sm btn-danger" onclick="removeSource(' + idx + ',' + si + ')">删除</button>' +
        '</span></div>';
    }).join("");

    var itHtml = (cat.info_types || []).map(function (it, ii) {
      return '<span class="tag">' + escapeHtml(it) + ' <span class="remove" onclick="removeInfoType(' + idx + ',' + ii + ')">×</span></span>';
    }).join("");

    return '<div class="cat-item">' +
      '<div class="cat-header">' +
        '<span class="icon">' + escapeHtml(cat.icon) + '</span>' +
        '<span class="name">' + escapeHtml(cat.name) + '</span>' +
        '<span class="id">(' + escapeHtml(cat.id) + ')</span>' +
        '<div class="actions">' +
          '<button class="btn-sm btn-danger" onclick="removeCategory(' + idx + ')">删除品类</button>' +
        '</div>' +
      '</div>' +
      '<div class="field-group">' +
        '<label>品类ID</label>' +
        '<input type="text" value="' + escapeHtml(cat.id) + '" onchange="updateCatField(' + idx + ',\'id\',this.value)">' +
      '</div>' +
      '<div class="field-group">' +
        '<label>品类名称</label>' +
        '<input type="text" value="' + escapeHtml(cat.name) + '" onchange="updateCatField(' + idx + ',\'name\',this.value)">' +
      '</div>' +
      '<div class="field-group">' +
        '<label>图标 (Emoji)</label>' +
        '<input type="text" value="' + escapeHtml(cat.icon) + '" onchange="updateCatField(' + idx + ',\'icon\',this.value)" style="width:80px">' +
      '</div>' +
      '<div class="field-group">' +
        '<label>关键词</label>' +
        '<div class="tag-list">' + kwHtml + '</div>' +
        '<div class="add-row">' +
          '<input type="text" id="kw-add-' + idx + '" placeholder="输入关键词后回车">' +
          '<button class="btn-sm btn-primary" onclick="addKeyword(' + idx + ')">添加</button>' +
        '</div>' +
      '</div>' +
      '<div class="field-group">' +
        '<label>媒体源</label>' +
        srcHtml +
        '<div class="add-row">' +
          '<input type="text" id="src-id-add-' + idx + '" placeholder="源ID(英文)">' +
          '<input type="text" id="src-name-add-' + idx + '" placeholder="源名称">' +
          '<input type="text" id="src-type-add-' + idx + '" placeholder="类型(search)" style="width:100px">' +
          '<button class="btn-sm btn-primary" onclick="addSource(' + idx + ')">添加</button>' +
        '</div>' +
      '</div>' +
      '<div class="field-group">' +
        '<label>信息类型</label>' +
        '<div class="tag-list">' + itHtml + '</div>' +
        '<div class="add-row">' +
          '<input type="text" id="it-add-' + idx + '" placeholder="输入信息类型">' +
          '<button class="btn-sm btn-primary" onclick="addInfoType(' + idx + ')">添加</button>' +
        '</div>' +
      '</div>' +
    '</div>';
  }

  // --- Global functions exposed to onclick handlers ---
  window.addCategory = function () {
    config.categories.push({
      id: "new-category",
      name: "新品类",
      icon: "📦",
      keywords: [],
      sources: [],
      info_types: ["公司财报", "行业报告", "媒体新闻", "招标信息"]
    });
    renderCategories();
  };

  window.removeCategory = function (idx) {
    if (confirm("确定删除品类「" + config.categories[idx].name + "」？")) {
      config.categories.splice(idx, 1);
      renderCategories();
    }
  };

  window.updateCatField = function (idx, field, value) {
    config.categories[idx][field] = value;
  };

  window.addKeyword = function (idx) {
    var input = document.getElementById("kw-add-" + idx);
    var kw = (input.value || "").trim();
    if (!kw) return;
    if (!config.categories[idx].keywords) config.categories[idx].keywords = [];
    config.categories[idx].keywords.push(kw);
    input.value = "";
    renderCategories();
  };

  window.removeKeyword = function (catIdx, kwIdx) {
    config.categories[catIdx].keywords.splice(kwIdx, 1);
    renderCategories();
  };

  window.addSource = function (idx) {
    var idInput = document.getElementById("src-id-add-" + idx);
    var nameInput = document.getElementById("src-name-add-" + idx);
    var typeInput = document.getElementById("src-type-add-" + idx);
    var sid = (idInput.value || "").trim();
    var sname = (nameInput.value || "").trim();
    var stype = (typeInput.value || "").trim() || "search";
    if (!sid || !sname) { alert("请填写源ID和名称"); return; }
    if (!config.categories[idx].sources) config.categories[idx].sources = [];
    config.categories[idx].sources.push({ id: sid, name: sname, type: stype, enabled: true });
    idInput.value = "";
    nameInput.value = "";
    typeInput.value = "";
    renderCategories();
  };

  window.removeSource = function (catIdx, srcIdx) {
    config.categories[catIdx].sources.splice(srcIdx, 1);
    renderCategories();
  };

  window.toggleSource = function (catIdx, srcIdx) {
    config.categories[catIdx].sources[srcIdx].enabled = !config.categories[catIdx].sources[srcIdx].enabled;
    renderCategories();
  };

  window.addInfoType = function (idx) {
    var input = document.getElementById("it-add-" + idx);
    var it = (input.value || "").trim();
    if (!it) return;
    if (!config.categories[idx].info_types) config.categories[idx].info_types = [];
    config.categories[idx].info_types.push(it);
    input.value = "";
    renderCategories();
  };

  window.removeInfoType = function (catIdx, itIdx) {
    config.categories[catIdx].info_types.splice(itIdx, 1);
    renderCategories();
  };

  window.saveConfig = function () {
    saveConfigLocal();
    // Also offer to download as categories.json
    var json = JSON.stringify(config, null, 2);
    var blob = new Blob([json], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "categories.json";
    a.click();
    URL.revokeObjectURL(url);
    showToast("配置已保存！categories.json 文件已下载，请将其放到 data/ 目录下替换原文件。");
  };

  window.exportConfig = function () {
    var json = JSON.stringify(config, null, 2);
    var blob = new Blob([json], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "categories.json";
    a.click();
    URL.revokeObjectURL(url);
    showToast("配置已导出");
  };

  window.importConfig = function () {
    document.getElementById("import-file").click();
  };

  window.handleImport = function (event) {
    var file = event.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function (e) {
      try {
        var data = JSON.parse(e.target.result);
        if (data && data.categories && Array.isArray(data.categories)) {
          config = data;
          renderCategories();
          showToast("配置已导入，请点击"保存配置"生效");
        } else {
          alert("无效的配置文件格式，需要包含 categories 数组");
        }
      } catch (err) {
        alert("解析文件失败: " + err.message);
      }
    };
    reader.readAsText(file);
    event.target.value = "";
  };

  function showToast(msg) {
    var toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 3000);
  }

  // Initialize
  loadConfig();
  renderCategories();

  // Try to load categories.json from the parent directory (works when served via HTTP)
  try {
    fetch("../data/categories.json", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.categories) {
          // Only override if server version is different
          var savedStr = localStorage.getItem("3c_categories_config");
          var serverStr = JSON.stringify(data);
          if (!savedStr || savedStr !== serverStr) {
            config = data;
            saveConfigLocal();
            renderCategories();
          }
        }
      })
      .catch(function () {
        // Silently fail - use defaults/localStorage
      });
  } catch (e) {}
})();