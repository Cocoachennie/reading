# Leaf · 外刊阅读室

面向考研英语、IELTS、TOEFL 的静态外刊阅读网站。**部署仅使用 GitHub Pages + GitHub Actions，无需任何其他平台账号、授权或 API 密钥。**

## 开启网站：只需 GitHub 页面操作

1. 打开 [仓库 Pages 设置](https://github.com/Cocoachennie/reading/settings/pages)。在 **Build and deployment → Source** 中选择 **GitHub Actions**。不用选择分支或手动上传网页。
2. 打开 [文章更新和部署工作流](https://github.com/Cocoachennie/reading/actions/workflows/pages.yml)。如出现提示，点击 **I understand my workflows, go ahead and enable them**。然后点击 **Run workflow → main → Run workflow**。
3. 等待 `build` 和 `deploy` 都变绿，打开部署结果中的网站链接。默认地址为 **https://cocoachennie.github.io/reading/**；若仓库已有自定义域名，以 Pages 设置显示的网址为准。

以后更新 `main` 分支代码会自动重新采集、构建和发布。定时工作流也会采集并重新部署，无需人工提交数据文件或保持电脑开机。Actions 使用 GitHub 内置 `GITHUB_TOKEN`，不需要创建或粘贴个人 Token。

如果 Pages 设置提示当前套餐不能给私有仓库启用 Pages：免费公开站点一般需要公开仓库。是否公开由你决定；未决定前不要改变仓库可见性。仓库源码及发布的 RSS 元数据不包含访客的浏览器正文、收藏和阅读记录。

当前会话的 GitHub API 请求返回 403，无法代替仓库所有者修改 Pages 设置或确认 Actions 运行状态。因此提交工作流不等于已开启 Pages 或已完成线上验证，上述 GitHub 设置只需由所有者完成一次。

## 保留的功能

- 考研英语、IELTS、TOEFL 三个入口，各自使用独立编辑主题分类。
- 英文标题、中文简介、来源、原文链接、发表/收集日期、主题、推荐理由和分析依据。
- 按主题、来源、日期、词数和估计难度筛选，按英文标题、中文简介、主题、来源或本地正文进行关键词搜索。
- 合法文章链接和完整正文的浏览器本地导入；不自动抓取链接正文、不绕过付费墙。
- 有完整正文时，在浏览器统计词数、平均句长、长词比例及可调整的启发式难度；缺少全文则明确不可分析。
- 收藏、原文打开记录、JSON 备份导入/导出；正文只在当前浏览器，备份不包含正文。请另行保管合法原始文件。更换域名或清空浏览器会影响本地数据，迁移前请先导出备份。
- 源站获取状态、最后成功时间、数据生成时间、实际最近定时运行时间；数据下载失败时保留浏览器中已有文章，并使用最近一次成功读取的公共目录缓存。
- 手机和电脑布局、相对资源路径，支持 GitHub Pages `/reading/` 项目子目录。

## 文章如何自动更新

`.github/workflows/pages.yml` 的同一个流程负责采集、持久化、构建和部署：

1. 触发方式：推送至 `main`、手动运行，以及每天 **北京时间 08:23 和 20:23**（UTC `23 0,12 * * *`）。
2. 先运行 Python 测试及 JavaScript 语法检查。
3. 执行 `scripts/update_articles.py`，从固定公开 RSS 获取允许的元数据。默认三源：Guardian Science、Guardian Environment、NASA News。The Economist 没有接通自动接口，保留手动导入能力。
4. 只发布白名单元数据；自动条目不含正文或 RSS 全文。按原文 URL 去重、校验链接并做主题预标注；未达主题阈值保留为“待复核”，不会误判为全文阅读适配。
5. 将公开数据与真实获取状态写入 `static/data/articles.json` 并由机器人提交到当前 `main`。保留最早收集日期，更新重复条目的元数据。最多保留 500 条；来源全部失败时不清空、也不裁剪原有文章，并保留最后成功时间。
6. 打包静态目录为 Pages artifact，由官方 `actions/deploy-pages` 发布。机器人数据提交带 `[skip ci]`，由当前工作流继续部署，避免反复触发。

**时间是计划，不是保证。** GitHub 可能延迟或停用计划任务（例如公开仓库长期无活动），需在 Actions 中检查和重新启用。界面不会仅凭配置宣称某次更新成功，实际来源结果与时间来自采集脚本记录。当前已验证本机三源获取成功；GitHub runner 的联网和定时运行尚需以真实 Actions 日志验证。

“刷新文章”只下载最近已发布的 JSON。GitHub Pages 不能运行 Python，也不能安全地让匿名网页持有写入仓库的 Token，所以网页按钮不能直接触发服务器采集。替代方式是工作流定时执行，或仓库所有者通过来源状态中的链接打开 Actions，点击 **Run workflow**。访客仍可随时导入自己的合法文章。

若某个 RSS 失败，工作流继续发布其他成功来源及失败状态；若全部失败，仍发布原有文章与新的失败信息。若 GitHub 整个工作流未运行/部署失败，网站继续保留上次发布的数据，不伪造新状态。

## 分析与版权边界

主题库是编辑初始分类，**尚未从真实历年真题语料生成**。至少 2 个独立主题线索需在 60 词局部窗口共同出现；阈值可调整，依旧需要语境人工复核，不是语义模型或考试采用证明。

正文词数按英文词统计（内部撇号/连字符视为同一词）。至少 80 词且 3 句才估计难度，以平均句长和 ≥8 字母词比例作粗略代理；默认中等阈值 17 词/17%，较难阈值 25 词/27%，句长和篇幅阈值可调整。它不是 CEFR 或考试官方评分，也没有真正的句法或词频模型。

没有合法真实真题语料及其年份/范围/频次算法，**考研高频词覆盖率始终不可用**。IELTS/TOEFL 当前实现各自的主题初筛，未提供官方或专用全文评分。没有核实证据的来源只能是推荐阅读来源，不能标记为真题来源。

首次目录中保留明确标注的虚构演示，演示没有伪造发布日期或原文链接，可通过开关隐藏。真实 RSS 条目来自公开标题、链接和日期；未有人工中文简介时会明确提示，未启用自动翻译。可公开访问 RSS 不等于获得全文转载授权。

## 项目结构与本地验证

```text
static/                     GitHub Pages 网页和公共 JSON
scripts/update_articles.py  离线 RSS 采集和筛选预标注
scripts/build_site.py       校验并生成 _site/ 静态发布目录
.github/workflows/pages.yml 采集、定时更新与 Pages 自动部署
.github/workflows/checks.yml PR 校验（不写入、不发布）
server.py                   保留的本地兼容后端及共享分析函数；不部署到 Pages
```

Python 3.12+，无第三方运行依赖。下面命令供开发者复现，使用网站不需要执行：

```bash
python -m unittest discover -s tests -v
node --check static/app.js
python scripts/update_articles.py       # 实际请求公开 RSS
python scripts/update_articles.py --offline  # 无联网，仅验证/重新标注现有目录
python scripts/build_site.py
python -m http.server 8000 --directory _site
```

`server.py` 不再是网站运行前提。采集脚本复用其中的 RSS 和分析函数，不启动 HTTP 服务；本地遗留接口仅用于兼容原开发流程。纯静态服务即可完整运行现在的前端。

测试覆盖：分类及全文限制、RSS 元数据范围、失败保留、URL 去重和收集日期、调度时间真实性、公共数据剥离正文、静态产物与相对路径。浏览器检查 `python tests/browser_static.py` 使用独立纯静态服务器模拟 `/reading/` 子路径，覆盖本地导入/分析、收藏、记录、断网缓存、备份和移动端布局；需额外的 Playwright/Chromium，仅作为开发验证，不是网站依赖。

## GitHub 页面上的常见问题

- **找不到 Run workflow**：先确认工作流文件已在默认分支 `main`，且 Actions 已允许运行。
- **build 在机器人 git push 步骤失败**：查看仓库 **Settings → Actions → General → Workflow permissions** 及组织策略，确认允许该工作流写入仓库。若 `main` 有保护规则，也须允许相应机器人更新，或后续改用专门数据分支；不要使用强制推送绕过。
- **configure-pages 报 `Get Pages site failed` / 404**：工作流已设置 `enablement: true`，会先读取站点，站点不存在时尝试创建 workflow 类型的 Pages。`deploy` 显式具备 `contents: read`、`pages: write`、`id-token: write`。上传产物名与部署读取名均固定为 `github-pages`；官方 `deploy-pages` 会自行下载该产物，不需要额外 `download-artifact`。
- **重新触发修复版部署**：打开 Actions → Update articles and deploy Pages → Run workflow，选择 `main`，再点击 Run workflow。不要只对旧失败记录点 Re-run jobs，那可能继续使用旧版本工作流。此次修复提交推送到 `main` 也会自动触发一次。
- **启用参数后仍出现 `Create Pages site failed` / 403**：这与原来的“未尝试创建”不同。[configure-pages 官方参数说明](https://github.com/actions/configure-pages/blob/v5/action.yml)明确指出，首次创建站点需要默认 `GITHUB_TOKEN` 之外的凭据；仅增加工作流权限并不能保证初始化成功。仓库所有者可先在 Settings → Pages 确认 GitHub Actions 配置已保存、站点已真正启用，然后重跑。若 UI 仍无法初始化，可在 GitHub 创建仅授权本仓库、具有 **Pages: Read and write** 权限的短期 fine-grained PAT，并在仓库 Settings → Secrets and variables → Actions → New repository secret 中命名为 `PAGES_ENABLEMENT_TOKEN`。工作流已支持该可选 secret，不需修改代码；不要把 Token 发在聊天、提交进代码或写入日志。初始化完成后可删除该 secret，后续部署自动回退到内置 Token。GitHub App 凭据还需相应的 `administration:write` 和 `pages:write` 权限；组织策略或站点政策限制须由管理员处理。
- **网站 404**：等 `deploy` 成功，确认地址包含 `/reading/`；自定义域名以 Pages 设置为准。
- **页面有文章但未变新**：查看来源状态和 Actions 日志；页面刷新与源站采集是两步。计划任务被停用时，在 Actions 中重新启用并手动运行一次。

无需创建额外 Git worktree；直接使用当前隔离任务的现有仓库。

## V2.0 阶段一：独立推荐与授权正文

构建和浏览器共用 `static/analysis.js`。三个考试各自计算主题分（50）、语言参考分（30）、篇幅分（20），不是同一列表换名称；无正文时完整分、词数、CEFR 均不可用，只允许标明“主题预评分”的候选。默认隐藏演示，采集目录已移除虚构文章，未匹配条目仅在“全部真实文章”中显示。

新增 OpenStax 官方 GitHub 仓库的 8 篇开放教材叙述正文改编，补充社会科学、经济、天文和生命科学阅读，并非冒充外刊新闻。每次先确定上游 Git 提交、检查仓库 LICENSE 为 CC BY-NC-SA 4.0，保留作者、原文版本、许可链接、提取说明和正文哈希；只允许固定模块进入公共 JSON。非商业、署名及相同方式共享条件适用，未开放许可的 Guardian/NASA RSS 仍然只发布元数据。图表、练习和独立引文已移除，词数针对实际展示的改编正文，不伪装成原站全文统计。来源失败保留旧正文和真实失败状态。

CEFR B1/B2/C1/C2 仅是未经标准化校准的启发式参考；词汇形态复杂度、句长与从属线索、篇幅和主题抽象度共同参与。长难句数量也是规则估计。核心词按当前正文词频统计，学术词来自公开在代码中的小型编辑词表，既不是完整 AWL，也不是历年考研词频语料。考研覆盖率不提供虚构数值。

## V2.0 阶段二：精读与原文关联

卡片优先进入 `#article=...` 站内阅读器；没有授权正文的条目只展示详情与原文链接，不提供假正文。字号、行距、宽度可调；阅读状态与进度单独记录，阅读时长只累计前台聚焦且最近有活动的阅读会话（90 秒无活动暂停），不是精确注意力测量。

高亮有四种颜色，笔记关联字符偏移、原文摘录、前后文和正文哈希。相同正文准确恢复；正文更新后仅在唯一摘录或明确上下文下重新定位，重复/删除的句子标为待重新定位，不悄悄移到错误段落。支持编辑/删除、全文搜索、笔记搜索与定位。

学习数据单独保存在 `leaf-learning-v2`，不覆盖原 `leaf-personal`。阶段二的 Node 锚点/合并测试及真实静态子路径浏览器检查通过。
