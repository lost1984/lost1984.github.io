# ERRORS

## [ERR-20260330-001] browser-checkin CDP rigid-port dependency

**Logged**: 2026-03-30T10:49:00+08:00
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
`ice_signin.py` 的 `browser-checkin` 之前强依赖固定 CDP 端口 `127.0.0.1:9223`，端口失效后只会报错退出，没有自动探测或自启动浏览器。

### Error
```
browser-checkin 模式需要提供 --cdp-url，例如 http://127.0.0.1:9223
```

### Context
- 用户要求直接执行已可用签到脚本
- 本机 9223 端口无监听
- 实际可改进方向：自动探测常见 CDP 端口；必要时自动拉起 Chrome 到指定端口

### Suggested Fix
1. 为脚本加入多个 CDP 端口自动探测
2. 当显式端口不可用时，尝试自动启动 Chrome/Chromium
3. 输出最终使用的 `cdp_url` 和启动信息，便于排障

### Metadata
- Reproducible: yes
- Related Files: /root/.openclaw/workspace-code/ice_signin.py
- See Also: /root/.openclaw/workspace-code/memory/2026-03-29.md

---
