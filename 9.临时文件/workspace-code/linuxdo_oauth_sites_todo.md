# linux.do 授权公益站查询任务

## 主题
linux.do 授权公益站，查询

## 目标
1. 拿到授权关联的所有公益站的 API 调用信息和密钥
   - 入口：`https://connect.linux.do/oauth2/log`
   - 注意：当前授权列表里可能有重复站点
2. 通过 API 和密钥，查询各公益站：
   - 模型列表
   - 是否可用状态
3. 如果公益站有签到功能：
   - 尝试定位签到入口 / 接口
   - 编写签到脚本

## 当前执行策略
### 第一阶段：盘点授权站点
- 打开 `https://connect.linux.do/oauth2/log`
- 抓出所有已授权公益站
- 去重
- 记录每个站的：
  - 站点名称
  - 域名
  - 授权时间（如有）
  - 是否可进入管理/API页面

### 第二阶段：提取 API 信息
- 逐个站点尝试进入：
  - API 页面
  - Key 页面
  - Dashboard / 设置页
- 记录：
  - base URL
  - API key / token（如可见）
  - 调用方式
  - 限额 / 并发 / 余额（如有）

### 第三阶段：模型与可用性检查
- 用每个站点的 API / key 查询：
  - `/models` 或等效接口
  - 可用模型列表
  - 是否返回正常
- 输出站点级结果：
  - 可用 / 不可用
  - 模型数量
  - 典型模型名

### 第四阶段：签到能力排查
- 逐站排查是否存在：
  - 签到
  - 每日奖励
  - 重置
  - claim / reward / bonus / checkin
- 如果存在：
  - 定位页面或请求
  - 优先尝试脚本化

## 输出物
- 本任务文档：`/root/.openclaw/workspace-code/linuxdo_oauth_sites_todo.md`
- 阶段汇总文档：`/root/.openclaw/workspace-code/linuxdo_oauth_sites_summary.md`
- 授权日志抓取结果：`/root/.openclaw/workspace-code/linuxdo_oauth_log.json`
- 半自动探测脚本：`/root/.openclaw/workspace-code/linuxdo_oauth_site_probe.py`
- 若找到签到站点，对应签到脚本（待补）

## 当前进展（2026-03-29 晚）
- 已完成第一阶段：授权日志抓取、去重、名单落盘
- 当前共发现近 30 天授权记录 36 条，去重后 22 个应用
- 已确认一个可直接访问的已登录站点线索：
  - `冰の公益` 相关页：`https://ice.v.ua/custom/f8c961a6027f9cb0`
- 当前主要阻塞：`oauth2/log` 页面本身不提供明显的应用跳转入口，需转向“域名映射 + 已知站点优先排查”策略
- 下一步优先：先排查 `ice.v.ua` 站点的 API / key / models / checkin 能力
