# linux.do 授权公益站阶段汇总

## 已确认站点

### 1. 冰の公益
- 站点：`https://ice.v.ua`
- 站名（前端配置）：`冰のCodex`
- 类型判断：AI API Gateway
- 已确认事实：
  - 首页可访问
  - `linuxdo_oauth_enabled: true`
  - 前端配置中 `api_base_url` 为 `https://ice.v.ua`
  - 存在自定义菜单 `签到/重置`
  - 签到菜单 id：`f8c961a6027f9cb0`
  - 存在额外入口：`https://pool.ice.v.ua/`
- 模型接口探测：
  - `GET https://ice.v.ua/v1/models` → `401`
  - 返回：`API_KEY_REQUIRED`
- 结论：
  - 存在 OpenAI 兼容模型接口
  - 需要 key
  - 存在签到能力

### 2. 97公益站（高概率映射）
- 候选站点：`https://api.mmkg.cloud`
- 类型判断：AI API Gateway / 公益 API 站
- 已确认事实：
  - 首页可访问
  - `/dashboard`、`/login`、`/models` 可访问
- 模型接口探测：
  - `GET https://api.mmkg.cloud/v1/models` → `401`
  - 返回：`未提供令牌`
  - `GET https://api.mmkg.cloud/api/models` → `401`
- 结论：
  - 模型接口存在
  - 需要 token
  - 站点真实存在，非占位页

## 当前阻塞
- `connect.linux.do` 当前被 Cloudflare / Turnstile 拦截，不适合继续把时间消耗在重抓授权日志上。
- 其他站点仍需完成“站名 → 真实域名”的映射。

## 当前策略
- 继续基于 22 个授权站名逐个映射真实域名
- 优先筛出能落地访问的 API 站
- 对已识别站点继续查：
  - key / token 获取方式
  - `/v1/models` 或等效模型接口
  - 是否存在签到/奖励/重置页面
