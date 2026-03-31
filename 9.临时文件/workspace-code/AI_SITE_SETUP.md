# /root/ai 静态网站方案

## 方案结论

最低成本、最好维护的方案：

- 托管：GitHub Pages
- 内容源：`/root/ai`
- 同步方式：本机定时任务 + git push
- 展示形式：静态文件镜像 + 自动生成 `index.html`

这个方案的优点：

1. 成本几乎为 0
2. 维护简单，只有 git + 一个脚本
3. 不需要数据库
4. 不需要后端服务
5. 出问题容易排查

## 已生成文件

- `site_sync.py`：把 `/root/ai` 镜像到网站仓库，并生成首页
- `sync_ai_to_site.sh`：执行同步、提交、推送
- `ai-site-sync.service`：systemd 单次同步任务
- `ai-site-sync.timer`：systemd 定时器，默认每 15 分钟同步一次

## 你需要准备的唯一东西

一个 GitHub 仓库，建议：

- 仓库名：`<github用户名>.github.io`

这样最省事，推上去直接就是主页站点。

## 一次性初始化步骤

### 1. 创建 GitHub 仓库

在 GitHub 新建一个公开仓库：

- 名称：`<your-name>.github.io`

### 2. 本机 clone 仓库

```bash
git clone git@github.com:<your-name>/<your-name>.github.io.git /root/ai-site
```

如果不用 SSH，也可以：

```bash
git clone https://github.com/<your-name>/<your-name>.github.io.git /root/ai-site
```

### 3. 配置 git 身份

```bash
git config --global user.name "YT"
git config --global user.email "your-email@example.com"
```

### 4. 如果是 HTTPS 推送

建议配置 GitHub token，避免每次输密码。

## 手动先跑一次

```bash
bash /root/.openclaw/workspace-code/sync_ai_to_site.sh
```

## 安装 systemd 定时同步

```bash
cp /root/.openclaw/workspace-code/ai-site-sync.service /etc/systemd/system/
cp /root/.openclaw/workspace-code/ai-site-sync.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now ai-site-sync.timer
```

## 常用命令

查看定时器：

```bash
systemctl status ai-site-sync.timer
systemctl list-timers | grep ai-site-sync
```

手动执行一次：

```bash
systemctl start ai-site-sync.service
```

看日志：

```bash
journalctl -u ai-site-sync.service -n 50 --no-pager
```

## 当前展示效果

脚本会：

1. 把 `/root/ai` 下文件镜像到网站仓库
2. 自动生成首页 `index.html`
3. 首页展示：
   - 文件目录
   - 文本文件预览
4. 每次有变化自动 commit + push

## 注意事项

### 1. 这是“公开静态站”

只适合公开内容。

如果 `/root/ai` 里有敏感信息、账号、密钥、隐私文档，不要直接同步。

### 2. 二进制大文件不适合

GitHub Pages 不适合放很大的文件。

### 3. 目前是全量公开镜像思路

如果后面你要：

- 只同步某几个子目录
- 排除某些文件类型
- 给首页做更好看的导航
- 加搜索
- 加密码保护

我可以继续在这个 MVP 上往上加。

## 我建议的下一步

最实用的顺序：

1. 你先建 GitHub Pages 仓库
2. 给我仓库地址
3. 我把 clone、首次 push、定时器启用全部给你接好

如果你愿意，我下一步可以直接把它做成：

- 首页更像知识库
- 自动排除敏感目录
- 支持按目录导航
- 支持 Markdown 更好显示
