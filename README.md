# 保险柜行业资讯（safe-box-news）

聚合最近 7 天保险柜 / 保险箱 / 保管箱行业权威媒体动态，并为每条新闻自动生成「💡 京东采销操盘建议」。纯静态站点，可托管在 GitHub Pages、Surge、Netlify Drop 等任意静态平台，PC + 手机均可正常浏览。

## 目录结构

```
safe-box-news/
├── index.html              # 网站入口
├── style.css               # 浅色调样式
├── js/app.js               # 前端交互逻辑
├── data/
│   ├── news.json           # 爬虫产出的最终数据
│   └── news.sample.json    # 兜底示例数据
├── crawler/
│   ├── run.py              # 爬虫主入口
│   ├── parser.py           # 日期/HTML 工具
│   ├── filter.py           # 关键词/7天/去重
│   ├── insight.py          # 京东采销建议生成
│   ├── sources.json        # 媒体来源配置
│   ├── insight_rules.json  # 采销建议规则库
│   └── fetchers/           # 多源抓取实现（6 个独立 fetcher + 通用基类）
├── serve.ps1               # 本地预览服务
├── publish.ps1             # 一键发布到 git 远程
├── .nojekyll               # 防止 GitHub Pages Jekyll 处理
└── .gitignore
```

## 环境准备

- **Python 3.8+**（仅使用标准库 urllib，**无需 pip install 任何第三方包**）
- 任意可启动静态服务器的环境（脚本默认调用 `python -m http.server`）
- 如使用 GitHub Pages 自动发布：需要 git ≥ 2.x

## 本地预览

```powershell
# 1. 运行爬虫生成数据（若所有源抓取为空将自动复用 news.sample.json 兜底）
python crawler/run.py

# 2. 启动本地服务
.\serve.ps1

# 3. 浏览器访问 http://localhost:8080
#    手机访问同一局域网：http://<电脑IP>:8080
```

## 公网部署

### 方案 A：Netlify Drop（推荐 · 免账号 · 拖拽 30 秒）

1. 打开 https://app.netlify.com/drop
2. 把整个 `safe-box-news/` 文件夹拖入虚线框
3. 等待 ~30 秒，页面会返回 `https://<random>.netlify.app` 公网 URL
4. 手机直接打开 URL 即可访问

### 方案 B：Surge.sh（命令行 · 免账号）

```powershell
npm install -g surge
cd safe-box-news
surge .   # 按提示选择域名，如 safe-box-news.surge.sh
```

### 方案 C：GitHub Pages（持久 · 支持自动发布）

1. 在 GitHub 新建仓库 `safe-box-news`
2. 本地仓库初始化并推送：
   ```powershell
   cd safe-box-news
   git init
   git remote add origin https://github.com/<username>/safe-box-news.git
   git add .
   git commit -m "init: safe-box news aggregator"
   git branch -M main
   git push -u origin main
   ```
3. 仓库页面 → Settings → Pages → Source 选择 `main` 分支、`/`（root）目录 → Save
4. 等待 1~2 分钟，访问 `https://<username>.github.io/safe-box-news/`

## 一键更新（publish.ps1）

```powershell
.\publish.ps1
```

内部流水线：
1. 调用 `python crawler/run.py` 刷新 `data/news.json`
2. 自动校验是否在 git 仓库 + 是否配置 remote（缺失时给出黄色提示并优雅退出）
3. `git add data/news.json` → `git commit` → `git push origin main`

每次推送后 GitHub Pages 会在 1~2 分钟内自动重新发布。

## 数据规则

- **时间窗口**：仅展示发布时间在最近 7 天内的新闻
- **来源覆盖**：新浪家居、网易家居、中华网、太平洋家居、搜狐、品牌官网等 6 个一级来源
- **关键词**：保险柜 / 保险箱 / 保管箱 / 防盗保险箱 / 家用保险柜 / 智能保险柜 / 安防柜
- **去重策略**：标题归一化（剥离标点+小写化）后去重，冲突时保留发布更早版本
- **采销建议**：基于 `crawler/insight_rules.json` 的规则引擎生成（品牌识别 + 关键词模板 + 长度截断 80 字），可按业务自由扩展

## 常见问题（FAQ）

**Q1：页面打开后显示"新闻数据加载失败 😢"？**
A：前端会自动级联尝试 `data/news.json → data/news.sample.json`。若两者都加载失败，通常是文件路径错误或托管平台禁止读取 `data/` 目录。检查 `data/news.json` 是否随静态资源一同上传。

**Q2：GitHub Pages 部署后页面 404 或样式错乱？**
A：仓库根目录必须包含 `.nojekyll`（防止 Jekyll 跳过 `_` 开头的文件），且所有资源使用相对路径（`./style.css`、`./js/app.js`）—— 当前项目已满足。

**Q3：爬虫运行后 `data/news.json` 里只有示例数据？**
A：说明所有来源抓取均为空（搜索引擎短暂限流或 DOM 改版），脚本会自动回退到 `news.sample.json` 写入 `news.json`，保证站点始终有内容。可调整 `crawler/sources.json` 中的 `search_url` 或新增来源。

**Q4：能否新增 / 修改采销建议规则？**
A：直接编辑 `crawler/insight_rules.json`，按现有 `match_any + template` 结构追加规则即可。规则按数组顺序匹配，首个命中即停止；未命中走 fallback。

**Q5：能否扩展新的媒体来源？**
A：在 `crawler/sources.json` 的 `sources` 数组添加配置，并在 `crawler/fetchers/` 新建对应 `xxx_fetcher.py`（继承 `GenericSearchFetcher` 即可），最后在 `fetchers/__init__.py` 的 `FETCHER_CLASSES` 中注册 `id → class` 映射。

**Q6：手机访问字号/排版有问题？**
A：项目已在 `style.css` 内置 1024 / 768 双断点 + 移动端 chip 横向滚动适配。若浏览器太老旧建议升级到 Chrome / Safari 最新版。

## License

仅供学习与内部商业研究使用，新闻原文版权归各源媒体所有；点击卡片可跳转原文阅读。