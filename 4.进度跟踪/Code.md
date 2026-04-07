# Code · 工具与自动化

> 维护人：Task 🐶
> 更新：2026-04-01 18:01

---

## 基本状态

- **当前状态**：待机
- **最后更新**：2026-04-01 17:50 GMT+8

---

## 最近完成项目

- **浏览器通道故障排查**（2026-04-01 17:50）
  - 发现：宿主机有 Chrome，但 OpenClaw browser 通道未启动
  - 结论：不要继续重试 browser 工具，会一直失败
  - 方案：gateway restart 或用户先在 linux.do 过验证

- **可见浏览器启动脚本升级**（2026-03-31 23:55）
  - 切换至独立中文 profile + 中文 locale + xrdp openbox 可见窗口模式
  - 提交：5171df7 "harden visible chrome launcher with zh locale and dedicated profile"

---

## 阻塞点

- ⚠️ 浏览器通道（browser）当前不可用，需 gateway restart 或用户验证

---

## 下一步

- 等待老板执行 gateway restart 后继续
