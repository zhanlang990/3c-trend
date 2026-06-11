// ============================================
// 3C趋势品类 · 管理后台 JS
// ============================================

// --- State ---
let sources = [];
let categories = [];
let currentTab = 'sources';
let currentGroup = 'all';
let editingSourceId = null;

// --- Init ---
document.addEventListener('DOMContentLoaded', async () => {
  await loadConfig();
  renderSources();
  renderCategories();
  renderGroupFilter();
  updateStats();
  loadGitHubSettingsUI();
});

// --- Config Load/Save ---
async function loadConfig() {
  try {
    const [srcRes, catRes] = await Promise.all([
      fetch('../data/sources.json'),
      fetch('../data/categories.json')
    ]);
    const srcData = await srcRes.json();
    const catData = await catRes.json();
    sources = srcData.sources || [];
    categories = catData.categories || catData || [];
  } catch (e) {
    console.error('加载配置失败:', e);
    showToast('加载配置失败，使用空数据', 'error');
    sources = [];
    categories = [];
  }
}

async function saveConfig() {
  const settings = getGitHubSettings();
  if (settings.repo && settings.token) {
    // GitHub sync mode
    const statusEl = document.getElementById('gh-status');
    if (statusEl) statusEl.innerHTML = '<span style="color:#3B82F6;">⏳ 正在提交到GitHub...</span>';
    try {
      const srcContent = JSON.stringify({ sources }, null, 2);
      const catContent = JSON.stringify({ categories }, null, 2);

      await githubUpsertFile('data/sources.json', srcContent, 'admin: update sources.json');
      await githubUpsertFile('data/categories.json', catContent, 'admin: update categories.json');

      if (statusEl) statusEl.innerHTML = '<span style="color:#059669;">✅ 配置已同步到GitHub，爬虫下次运行将自动读取</span>';
      showToast('配置已同步到GitHub');
      return;
    } catch (e) {
      console.error('GitHub同步失败:', e);
      if (statusEl) statusEl.innerHTML = `<span style="color:#DC2626;">❌ GitHub同步失败: ${e.message}，将改为本地导出</span>`;
      showToast('GitHub同步失败，改为本地导出', 'error');
      // Fall through to local export
    }
  }

  // Local export mode (fallback or no GitHub configured)
  try {
    const srcBlob = new Blob([JSON.stringify({ sources }, null, 2)], { type: 'application/json' });
    const srcUrl = URL.createObjectURL(srcBlob);
    const srcA = document.createElement('a');
    srcA.href = srcUrl;
    srcA.download = 'sources.json';
    srcA.click();
    URL.revokeObjectURL(srcUrl);

    const catBlob = new Blob([JSON.stringify({ categories }, null, 2)], { type: 'application/json' });
    const catUrl = URL.createObjectURL(catBlob);
    const catA = document.createElement('a');
    catA.href = catUrl;
    catA.download = 'categories.json';
    catA.click();
    URL.revokeObjectURL(catUrl);

    showToast('配置已导出，请手动替换 data/ 目录下对应文件');
  } catch (e) {
    console.error('保存失败:', e);
    showToast('保存失败', 'error');
  }
}

function exportConfig() {
  const config = { sources, categories };
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'config-export.json';
  a.click();
  URL.revokeObjectURL(url);
  showToast('配置已导出');
}

function importConfig() {
  document.getElementById('import-file').click();
}

function handleImport(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result);
      if (data.sources) sources = data.sources;
      if (data.categories) categories = data.categories;
      renderSources();
      renderCategories();
      renderGroupFilter();
      updateStats();
      showToast('配置导入成功');
    } catch (err) {
      showToast('导入失败：JSON格式错误', 'error');
    }
  };
  reader.readAsText(file);
  event.target.value = '';
}

// --- Tab Switch ---
function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('tab-' + tab).classList.add('active');
}

// --- Source Management ---
function renderSources() {
  const search = (document.getElementById('src-search')?.value || '').toLowerCase();
  const filtered = sources.filter(s => {
    const matchGroup = currentGroup === 'all' || s.group === currentGroup;
    const matchSearch = !search || s.name.toLowerCase().includes(search) ||
      s.url.toLowerCase().includes(search) || s.group.toLowerCase().includes(search) ||
      (s.focus || '').toLowerCase().includes(search);
    return matchGroup && matchSearch;
  });

  const tbody = document.getElementById('src-tbody');
  if (!tbody) return;
  tbody.innerHTML = filtered.map(s => `
    <tr>
      <td><input type="checkbox" data-id="${s.id}" ${s.enabled ? 'checked' : ''} onchange="toggleSource('${s.id}', this.checked)"></td>
      <td class="src-name">${s.name}</td>
      <td><a class="src-url" href="${s.url}" target="_blank" title="${s.url}">${s.url}</a></td>
      <td><span class="src-type-badge src-type-${s.type}">${typeLabel(s.type)}</span></td>
      <td>${s.group}</td>
      <td style="font-size:12px;color:#6B7280;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${s.focus || ''}">${s.focus || '-'}</td>
      <td>${s.enabled ? '<span style="color:#059669">启用</span>' : '<span style="color:#9CA3AF">禁用</span>'}</td>
      <td>
        <button class="btn-sm" onclick="editSource('${s.id}')">编辑</button>
        <button class="btn-sm btn-danger" onclick="deleteSource('${s.id}')">删除</button>
      </td>
    </tr>
  `).join('');
}

function typeLabel(t) {
  return { website: '网站', wechat: '微信', weibo: '微博', community: '社区' }[t] || t;
}

function filterSources() {
  renderSources();
}

// --- Source CRUD ---
function toggleSource(id, enabled) {
  const s = sources.find(x => x.id === id);
  if (s) { s.enabled = enabled; renderSources(); updateStats(); }
}

function toggleAllSources(el) {
  const checked = el.checked;
  sources.forEach(s => s.enabled = checked);
  renderSources();
  updateStats();
}

function deleteSource(id) {
  if (!confirm('确定删除该信源？')) return;
  sources = sources.filter(s => s.id !== id);
  renderSources();
  renderGroupFilter();
  updateStats();
  showToast('信源已删除');
}

function editSource(id) {
  const s = sources.find(x => x.id === id);
  if (!s) return;
  editingSourceId = id;
  document.getElementById('modal-title').textContent = '编辑信源';
  document.getElementById('m-name').value = s.name;
  document.getElementById('m-url').value = s.url || '';
  document.getElementById('m-type').value = s.type;
  document.getElementById('m-group').value = s.group;
  document.getElementById('m-focus').value = s.focus || '';
  document.getElementById('m-desc').value = s.desc || '';
  document.getElementById('m-id').value = s.id;
  document.getElementById('m-id').disabled = true;
  document.getElementById('source-modal').classList.add('show');
}

function openAddSourceModal() {
  editingSourceId = null;
  document.getElementById('modal-title').textContent = '添加信源';
  document.getElementById('m-name').value = '';
  document.getElementById('m-url').value = '';
  document.getElementById('m-type').value = 'website';
  document.getElementById('m-group').value = '综合科技';
  document.getElementById('m-focus').value = '';
  document.getElementById('m-desc').value = '';
  document.getElementById('m-id').value = '';
  document.getElementById('m-id').disabled = false;
  document.getElementById('source-modal').classList.add('show');
}

function closeSourceModal() {
  document.getElementById('source-modal').classList.remove('show');
  editingSourceId = null;
}

function saveSource() {
  const name = document.getElementById('m-name').value.trim();
  const url = document.getElementById('m-url').value.trim();
  const type = document.getElementById('m-type').value;
  const group = document.getElementById('m-group').value;
  const focus = document.getElementById('m-focus').value.trim();
  const desc = document.getElementById('m-desc').value.trim();
  let id = document.getElementById('m-id').value.trim();

  if (!name) { showToast('请输入名称', 'error'); return; }
  if (!id) { id = name.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-'); }

  if (editingSourceId) {
    const s = sources.find(x => x.id === editingSourceId);
    if (s) { Object.assign(s, { name, url, type, group, focus, desc }); }
  } else {
    if (sources.find(x => x.id === id)) { showToast('ID已存在', 'error'); return; }
    sources.push({ id, name, url, type, group, focus, desc, enabled: true });
  }

  closeSourceModal();
  renderSources();
  renderGroupFilter();
  updateStats();
  showToast(editingSourceId ? '信源已更新' : '信源已添加');
}

// --- Group Filter ---
function renderGroupFilter() {
  const groups = ['all', ...new Set(sources.map(s => s.group))];
  const container = document.getElementById('group-filter');
  if (!container) return;
  container.innerHTML = groups.map(g =>
    `<button class="group-btn ${currentGroup === g ? 'active' : ''}" onclick="setGroup('${g}')">${g === 'all' ? '全部' : g}</button>`
  ).join('');
}

function setGroup(g) {
  currentGroup = g;
  renderGroupFilter();
  renderSources();
}

// --- Stats ---
function updateStats() {
  const total = sources.length;
  const enabled = sources.filter(s => s.enabled).length;
  const groups = new Set(sources.map(s => s.group)).size;
  const container = document.getElementById('src-stats');
  if (!container) return;
  container.innerHTML = `
    <div class="stat-item"><div class="stat-num">${total}</div><div class="stat-label">总信源</div></div>
    <div class="stat-item"><div class="stat-num">${enabled}</div><div class="stat-label">已启用</div></div>
    <div class="stat-item"><div class="stat-num">${total - enabled}</div><div class="stat-label">已禁用</div></div>
    <div class="stat-item"><div class="stat-num">${groups}</div><div class="stat-label">分组数</div></div>
  `;
}

// --- Category Management ---
function renderCategories() {
  const container = document.getElementById('cat-list');
  if (!container) return;
  container.innerHTML = categories.map((cat, idx) => `
    <div class="cat-item" data-idx="${idx}">
      <div class="cat-header">
        <span class="icon">${cat.icon || '📁'}</span>
        <span class="name">${cat.name}</span>
        <span class="id">${cat.id}</span>
        <div class="actions">
          <button class="btn-sm btn-danger" onclick="removeCategory(${idx})">删除品类</button>
        </div>
      </div>
      <div class="field-group">
        <label>关键词</label>
        <div class="tag-list">
          ${(cat.keywords || []).map((kw, ki) => `
            <span class="tag">${kw}<span class="remove" onclick="removeKeyword(${idx}, ${ki})">×</span></span>
          `).join('')}
        </div>
        <div class="add-row">
          <input type="text" id="kw-add-${idx}" placeholder="输入关键词后回车" onkeydown="if(event.key==='Enter')addKeyword(${idx})">
          <button class="btn-sm btn-primary" onclick="addKeyword(${idx})">添加</button>
        </div>
      </div>

    </div>
  `).join('');
}

function addKeyword(catIdx) {
  const input = document.getElementById('kw-add-' + catIdx);
  const kw = input.value.trim();
  if (!kw) return;
  if (!categories[catIdx].keywords) categories[catIdx].keywords = [];
  if (categories[catIdx].keywords.includes(kw)) { showToast('关键词已存在', 'error'); return; }
  categories[catIdx].keywords.push(kw);
  input.value = '';
  renderCategories();
  showToast('关键词已添加');
}

function removeKeyword(catIdx, kwIdx) {
  categories[catIdx].keywords.splice(kwIdx, 1);
  renderCategories();
}



function addCategory() {
  const id = prompt('请输入品类ID（英文，如 ai-phone）：');
  if (!id) return;
  const name = prompt('请输入品类名称（中文）：');
  if (!name) return;
  const icon = prompt('请输入图标（emoji）：', '📁') || '📁';
  if (categories.find(c => c.id === id)) { showToast('ID已存在', 'error'); return; }
  categories.push({ id, name, icon, keywords: [], sources: [], info_types: ['媒体新闻'] });
  renderCategories();
  showToast('品类已添加');
}

function removeCategory(idx) {
  if (!confirm(`确定删除品类「${categories[idx].name}」？`)) return;
  categories.splice(idx, 1);
  renderCategories();
  showToast('品类已删除');
}

// --- GitHub Sync ---
const GH_SETTINGS_KEY = 'gh_sync_settings';

function getGitHubSettings() {
  try {
    return JSON.parse(localStorage.getItem(GH_SETTINGS_KEY)) || {};
  } catch { return {}; }
}

function saveGitHubSettings() {
  const repo = document.getElementById('gh-repo').value.trim();
  const token = document.getElementById('gh-token').value.trim();
  const branch = document.getElementById('gh-branch').value.trim() || 'main';
  if (!repo || !token) {
    showToast('请填写仓库地址和Token', 'error');
    return;
  }
  localStorage.setItem(GH_SETTINGS_KEY, JSON.stringify({ repo, token, branch }));
  showToast('GitHub同步设置已保存');
}

function clearGitHubSettings() {
  if (!confirm('确定清除GitHub同步设置？')) return;
  localStorage.removeItem(GH_SETTINGS_KEY);
  document.getElementById('gh-repo').value = '';
  document.getElementById('gh-token').value = '';
  document.getElementById('gh-branch').value = 'main';
  document.getElementById('gh-status').innerHTML = '';
  showToast('设置已清除');
}

async function testGitHubConnection() {
  const settings = getGitHubSettings();
  if (!settings.repo || !settings.token) {
    showToast('请先保存GitHub设置', 'error');
    return;
  }
  const statusEl = document.getElementById('gh-status');
  statusEl.innerHTML = '<span style="color:#3B82F6;">⏳ 正在测试连接...</span>';
  try {
    const res = await fetch(`https://api.github.com/repos/${settings.repo}`, {
      headers: { 'Authorization': `token ${settings.token}`, 'Accept': 'application/vnd.github.v3+json' }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    const data = await res.json();
    statusEl.innerHTML = `<span style="color:#059669;">✅ 连接成功！仓库: ${data.full_name} (${data.private ? '私有' : '公开'})，默认分支: ${data.default_branch}</span>`;
  } catch (e) {
    statusEl.innerHTML = `<span style="color:#DC2626;">❌ 连接失败: ${e.message}</span>`;
  }
}

function loadGitHubSettingsUI() {
  const settings = getGitHubSettings();
  const repoEl = document.getElementById('gh-repo');
  const tokenEl = document.getElementById('gh-token');
  const branchEl = document.getElementById('gh-branch');
  if (repoEl) repoEl.value = settings.repo || '';
  if (tokenEl) tokenEl.value = settings.token || '';
  if (branchEl) branchEl.value = settings.branch || 'main';
}

async function githubUpsertFile(filePath, content, message) {
  const settings = getGitHubSettings();
  if (!settings.repo || !settings.token) return false;
  const { repo, token, branch } = settings;

  // Get current file SHA (if exists) for update
  let sha = null;
  try {
    const res = await fetch(`https://api.github.com/repos/${repo}/contents/${filePath}?ref=${branch}`, {
      headers: { 'Authorization': `token ${token}`, 'Accept': 'application/vnd.github.v3+json' }
    });
    if (res.ok) {
      const data = await res.json();
      sha = data.sha;
    }
  } catch { /* file may not exist yet */ }

  // Create or update file
  const body = {
    message,
    content: btoa(unescape(encodeURIComponent(content))),
    branch,
  };
  if (sha) body.sha = sha;

  const res = await fetch(`https://api.github.com/repos/${repo}/contents/${filePath}`, {
    method: 'PUT',
    headers: { 'Authorization': `token ${token}`, 'Accept': 'application/vnd.github.v3+json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || `HTTP ${res.status}`);
  }
  return true;
}

// --- Toast ---
function showToast(msg, type = 'success') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();
  const toast = document.createElement('div');
  toast.className = 'toast';
  if (type === 'error') toast.style.background = '#DC2626';
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2500);
}