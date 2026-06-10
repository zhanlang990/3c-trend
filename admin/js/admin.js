(function () {
  "use strict";

  var config = null;

  function getDefaultConfig() {
    return {
      categories: [
        { id: "3d-printing", name: "3D打印", icon: "🖨️", keywords: ["3D打印","3D打印机","增材制造","3D建模","3D扫描"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"sohu",name:"搜狐",type:"search",enabled:true},{id:"chinairn",name:"中研网",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "uv-printing", name: "UV打印", icon: "🎨", keywords: ["UV打印","UV打印机","UV平板打印","UV卷材打印","UV固化"], sources: [{id:"sohu",name:"搜狐",type:"search",enabled:true},{id:"chinairn",name:"中研网",type:"search",enabled:true},{id:"taobao-baike",name:"淘宝百科",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "cnc", name: "CNC", icon: "⚙️", keywords: ["CNC","数控机床","CNC加工","数控车床","数控铣床","五轴加工"], sources: [{id:"sohu",name:"搜狐",type:"search",enabled:true},{id:"chinairn",name:"中研网",type:"search",enabled:true},{id:"sina",name:"新浪",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "ai-nas", name: "AI网络存储", icon: "💾", keywords: ["NAS","网络存储","AI存储","私有云","云存储","群晖","威联通"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"zol",name:"中关村在线",type:"search",enabled:true},{id:"sohu",name:"搜狐",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "ai-glasses", name: "AI眼镜", icon: "🥽", keywords: ["AI眼镜","智能眼镜","AR眼镜","MR眼镜","Ray-Ban Meta"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"sohu",name:"搜狐",type:"search",enabled:true},{id:"chinairn",name:"中研网",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "ai-pc", name: "AIPC", icon: "🤖", keywords: ["AIPC","AI PC","AI电脑","AI笔记本","Copilot PC","AI处理器"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"zol",name:"中关村在线",type:"search",enabled:true},{id:"pconline",name:"太平洋电脑",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "ai-phone", name: "AI手机", icon: "📱", keywords: ["AI手机","AI智能手机","AI拍照手机","AI语音助手","大模型手机"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"zol",name:"中关村在线",type:"search",enabled:true},{id:"cnbeta",name:"cnBeta",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "ai-learning", name: "AI学习硬件", icon: "📚", keywords: ["AI学习硬件","AI学习机","智能学习机","AI词典笔","AI错题本","学习平板"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"sohu",name:"搜狐",type:"search",enabled:true},{id:"chinairn",name:"中研网",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "safe-box", name: "保险柜", icon: "🔒", keywords: ["保险柜","保险箱","保管箱","防盗保险箱","家用保险柜","智能保险柜","安防柜","床头柜","收纳箱","收纳柜","储物柜"], sources: [{id:"sina",name:"新浪家居",type:"search",enabled:true},{id:"netease",name:"网易家居",type:"search",enabled:true},{id:"china",name:"中华网",type:"search",enabled:true},{id:"pchouse",name:"太平洋家居",type:"search",enabled:true},{id:"sohu",name:"搜狐",type:"search",enabled:true},{id:"aipu",name:"艾谱官网",type:"html_list",enabled:true},{id:"chinairn",name:"中研网",type:"search",enabled:true},{id:"taobao-baike",name:"淘宝百科",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "4k-projector", name: "4K投影", icon: "🎬", keywords: ["4K投影","4K投影仪","激光投影","家用投影","智能投影","超短焦投影"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"zol",name:"中关村在线",type:"search",enabled:true},{id:"pconline",name:"太平洋电脑",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "gaming-peripherals", name: "电竞键鼠", icon: "🎮", keywords: ["电竞键盘","电竞鼠标","机械键盘","游戏鼠标","电竞外设","RGB键盘"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"zol",name:"中关村在线",type:"search",enabled:true},{id:"sohu",name:"搜狐",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "monitor", name: "显示器", icon: "🖥️", keywords: ["高刷显示器","电竞显示器","高清显示器","专业显示器","4K显示器","OLED显示器","MiniLED显示器"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"zol",name:"中关村在线",type:"search",enabled:true},{id:"pconline",name:"太平洋电脑",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "smart-watch", name: "时尚智能手表", icon: "⌚", keywords: ["智能手表","时尚手表","运动手表","健康监测手表","智能腕表","Apple Watch","华为手表"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"zol",name:"中关村在线",type:"search",enabled:true},{id:"sohu",name:"搜狐",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "gaming-desktop", name: "游戏台式机", icon: "💻", keywords: ["游戏台式机","游戏主机","电竞电脑","组装电脑","品牌台式机","游戏PC"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"zol",name:"中关村在线",type:"search",enabled:true},{id:"pconline",name:"太平洋电脑",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "photography", name: "摄影摄像", icon: "📷", keywords: ["生态摄像","高清摄像","相机","微单相机","运动相机","无人机航拍","摄影器材"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"zol",name:"中关村在线",type:"search",enabled:true},{id:"pconline",name:"太平洋电脑",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "surveillance", name: "监控摄像", icon: "📹", keywords: ["无线免流监控","无线免流摄像","太阳能监控","太阳能摄像","智能监控","安防摄像","家用监控"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"sohu",name:"搜狐",type:"search",enabled:true},{id:"sina",name:"新浪",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "speaker", name: "音箱", icon: "🔊", keywords: ["艺术音箱","AI智能音箱","蓝牙音箱","智能家居音箱","HiFi音箱","桌面音箱"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"zol",name:"中关村在线",type:"search",enabled:true},{id:"sohu",name:"搜狐",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "magnetic-accessories", name: "磁吸配件", icon: "🧲", keywords: ["磁吸配件","磁吸充电","MagSafe","磁吸支架","磁吸手机壳","磁吸车载"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"zol",name:"中关村在线",type:"search",enabled:true},{id:"sohu",name:"搜狐",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] },
        { id: "foldable-phone", name: "折叠屏手机", icon: "📲", keywords: ["折叠屏手机","折叠屏","翻盖折叠","折叠屏旗舰","折叠屏新品"], sources: [{id:"ithome",name:"IT之家",type:"search",enabled:true},{id:"zol",name:"中关村在线",type:"search",enabled:true},{id:"cnbeta",name:"cnBeta",type:"search",enabled:true}], info_types: ["公司财报","行业报告","媒体新闻","招标信息"] }
      ]
    };
  }

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
    // Use inline defaults (same as categories.json)
    config = getDefaultConfig();
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