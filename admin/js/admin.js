(function () {
  "use strict";

  var config = null;

  function escapeHtml(s) {
    if (s == null) return "";
    var div = document.createElement("div");
    div.textContent = String(s);
    return div.innerHTML;
  }

  function loadConfig() {
    try {
      var saved = localStorage.getItem("3c_categories_config");
      if (saved) { config = JSON.parse(saved); return; }
    } catch (e) {}
    // Load from server or use empty
    config = { categories: [] };
  }

  function saveConfigLocal() {
    try { localStorage.setItem("3c_categories_config", JSON.stringify(config)); } catch (e) {}
  }

  function renderCategories() {
    var $list = document.getElementById("cat-list");
    if (!config || !config.categories || !config.categories.length) {
      $list.innerHTML = '<div class="empty-msg">暂无品类配置，请点击"添加品类"或从服务器加载</div>';
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
      '<div class="field-group"><label>品类ID</label>' +
        '<input type="text" value="' + escapeHtml(cat.id) + '" onchange="updateCatField(' + idx + ',\'id\',this.value)"></div>' +
      '<div class="field-group"><label>品类名称</label>' +
        '<input type="text" value="' + escapeHtml(cat.name) + '" onchange="updateCatField(' + idx + ',\'name\',this.value)"></div>' +
      '<div class="field-group"><label>图标 (Emoji)</label>' +
        '<input type="text" value="' + escapeHtml(cat.icon) + '" onchange="updateCatField(' + idx + ',\'icon\',this.value)" style="width:80px"></div>' +
      '<div class="field-group"><label>关键词</label>' +
        '<div class="tag-list">' + kwHtml + '</div>' +
        '<div class="add-row"><input type="text" id="kw-add-' + idx + '" placeholder="输入关键词">' +
          '<button class="btn-sm btn-primary" onclick="addKeyword(' + idx + ')">添加</button></div></div>' +
      '<div class="field-group"><label>媒体源</label>' + srcHtml +
        '<div class="add-row"><input type="text" id="src-id-add-' + idx + '" placeholder="源ID">' +
          '<input type="text" id="src-name-add-' + idx + '" placeholder="源名称">' +
          '<input type="text" id="src-type-add-' + idx + '" placeholder="类型" style="width:80px">' +
          '<button class="btn-sm btn-primary" onclick="addSource(' + idx + ')">添加</button></div></div>' +
      '<div class="field-group"><label>信息类型</label>' +
        '<div class="tag-list">' + itHtml + '</div>' +
        '<div class="add-row"><input type="text" id="it-add-' + idx + '" placeholder="输入信息类型">' +
          '<button class="btn-sm btn-primary" onclick="addInfoType(' + idx + ')">添加</button></div></div>' +
    '</div>';
  }

  window.addCategory = function () {
    config.categories.push({ id: "new-category", name: "新品类", icon: "📦", keywords: [], sources: [], info_types: ["公司财报", "行业报告", "媒体新闻", "招标信息"] });
    renderCategories();
  };
  window.removeCategory = function (idx) {
    if (confirm("确定删除品类「" + config.categories[idx].name + "」？")) { config.categories.splice(idx, 1); renderCategories(); }
  };
  window.updateCatField = function (idx, field, value) { config.categories[idx][field] = value; };
  window.addKeyword = function (idx) {
    var input = document.getElementById("kw-add-" + idx); var kw = (input.value || "").trim();
    if (!kw) return; if (!config.categories[idx].keywords) config.categories[idx].keywords = [];
    config.categories[idx].keywords.push(kw); input.value = ""; renderCategories();
  };
  window.removeKeyword = function (catIdx, kwIdx) { config.categories[catIdx].keywords.splice(kwIdx, 1); renderCategories(); };
  window.addSource = function (idx) {
    var sid = (document.getElementById("src-id-add-" + idx).value || "").trim();
    var sname = (document.getElementById("src-name-add-" + idx).value || "").trim();
    var stype = (document.getElementById("src-type-add-" + idx).value || "").trim() || "search";
    if (!sid || !sname) { alert("请填写源ID和名称"); return; }
    if (!config.categories[idx].sources) config.categories[idx].sources = [];
    config.categories[idx].sources.push({ id: sid, name: sname, type: stype, enabled: true });
    document.getElementById("src-id-add-" + idx).value = ""; document.getElementById("src-name-add-" + idx).value = ""; document.getElementById("src-type-add-" + idx).value = "";
    renderCategories();
  };
  window.removeSource = function (catIdx, srcIdx) { config.categories[catIdx].sources.splice(srcIdx, 1); renderCategories(); };
  window.toggleSource = function (catIdx, srcIdx) { config.categories[catIdx].sources[srcIdx].enabled = !config.categories[catIdx].sources[srcIdx].enabled; renderCategories(); };
  window.addInfoType = function (idx) {
    var input = document.getElementById("it-add-" + idx); var it = (input.value || "").trim();
    if (!it) return; if (!config.categories[idx].info_types) config.categories[idx].info_types = [];
    config.categories[idx].info_types.push(it); input.value = ""; renderCategories();
  };
  window.removeInfoType = function (catIdx, itIdx) { config.categories[catIdx].info_types.splice(itIdx, 1); renderCategories(); };

  window.saveConfig = function () {
    saveConfigLocal();
    var json = JSON.stringify(config, null, 2);
    var blob = new Blob([json], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a"); a.href = url; a.download = "categories.json"; a.click();
    URL.revokeObjectURL(url);
    showToast("配置已保存！categories.json 已下载，请放到 data/ 目录替换原文件。");
  };
  window.exportConfig = function () {
    var json = JSON.stringify(config, null, 2);
    var blob = new Blob([json], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a"); a.href = url; a.download = "categories.json"; a.click();
    URL.revokeObjectURL(url);
    showToast("配置已导出");
  };
  window.importConfig = function () { document.getElementById("import-file").click(); };
  window.handleImport = function (event) {
    var file = event.target.files[0]; if (!file) return;
    var reader = new FileReader();
    reader.onload = function (e) {
      try {
        var data = JSON.parse(e.target.result);
        if (data && data.categories && Array.isArray(data.categories)) { config = data; renderCategories(); showToast("配置已导入，请点击保存配置"); }
        else { alert("无效的配置文件格式"); }
      } catch (err) { alert("解析失败: " + err.message); }
    };
    reader.readAsText(file); event.target.value = "";
  };

  function showToast(msg) {
    var toast = document.createElement("div"); toast.className = "toast"; toast.textContent = msg;
    document.body.appendChild(toast); setTimeout(function () { toast.remove(); }, 3000);
  }

  loadConfig();
  renderCategories();

  // Try to load from server
  try {
    fetch("../data/categories.json", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.categories) {
          var savedStr = localStorage.getItem("3c_categories_config");
          var serverStr = JSON.stringify(data);
          if (!savedStr || savedStr !== serverStr) { config = data; saveConfigLocal(); renderCategories(); }
        }
      }).catch(function () {});
  } catch (e) {}
})();