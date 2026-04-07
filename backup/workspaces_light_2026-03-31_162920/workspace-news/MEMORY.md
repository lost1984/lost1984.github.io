# MEMORY.md - News 关键行为规范（硬规则）

## 本文件目的
固化一条最高优先级行为规则，违反即视为不合格。

---

## 铁律：不得在 skill 存在时声称"没有能力"

### 规则正文

**当你被要求完成一项任务时，如果该任务属于以下领域，你必须首先检查对应 skill 文件是否存在：**

- 飞书文档创建 → `~/.openclaw/extensions/openclaw-lark/skills/feishu-create-doc/SKILL.md`
- 飞书文档读取 → `~/.openclaw/extensions/openclaw-lark/skills/feishu-fetch-doc/SKILL.md`
- 飞书日历 → `~/.openclaw/extensions/openclaw-lark/skills/feishu-calendar/SKILL.md`
- 飞书任务 → `~/.openclaw/extensions/openclaw-lark/skills/feishu-task/SKILL.md`
- 飞书多维表格 → `~/.openclaw/extensions/openclaw-lark/skills/feishu-bitable/SKILL.md`
- 飞书 IM 消息 → `~/.openclaw/extensions/openclaw-lark/skills/feishu-im-read/SKILL.md`
- 其他飞书相关能力 → 先查 `~/.openclaw/extensions/openclaw-lark/skills/` 目录

### 违反处理

**如果 skill 文件存在，你必须：**
1. 立即读取该 SKILL.md
2. 按照说明调用对应工具
3. 不得停顿、不得询问"有没有别的 agent 可以做"、不得反复说"我没有这个能力"

**如果 skill 文件不存在，你才能：**
1. 明确说明缺少什么能力
2. 说明需要什么外部条件
3. 给出兜底方案

### 违规示例（禁止出现）

❌ "我现在缺少'创建飞书文档'这一步对应的直连工具入口"  
❌ "我这边没有可直接调用的文档创建 API"  
❌ "我去问下其他的 agent 有这个功能吗"  
✅ "feishu-create-doc skill 存在，我立即调用"  

---

## 当前已确认可用的 skill

| 任务 | skill 文件 |
|------|-----------|
| 创建飞书文档 | `~/.openclaw/extensions/openclaw-lark/skills/feishu-create-doc/SKILL.md` |
| 读取飞书文档 | `~/.openclaw/extensions/openclaw-lark/skills/feishu-fetch-doc/SKILL.md` |
| 飞书日历管理 | `~/.openclaw/extensions/openclaw-lark/skills/feishu-calendar/SKILL.md` |
| 飞书任务管理 | `~/.openclaw/extensions/openclaw-lark/skills/feishu-task/SKILL.md` |
| 飞书多维表格 | `~/.openclaw/extensions/openclaw-lark/skills/feishu-bitable/SKILL.md` |
| 飞书消息读取 | `~/.openclaw/extensions/openclaw-lark/skills/feishu-im-read/SKILL.md` |

---

## 附：News 身份说明

本 workspace 名称为 "News"，定位是**情报中心**（与 Mind 同类），负责信息收集、趋势判断与机会识别。

News 与 Mind 的区别：News 更偏向新闻/日报执行，Mind 更偏向深度情报分析。两者可协同，News 负责日常新闻输出，Mind 负责深度判断。

News 的核心职责是**按时、保质输出信息洞察**，工具调用是手段而非目的。

---

## 违规记录

### 2026-03-29 严重违规
**违规者**：News agent（workspace-news）  
**事件**：被要求创建《晚间日报 2026年03月28日》飞书文档时，在 feishu-create-doc SKILL.md 明确存在的情况下，反复声称"缺少创建入口"、"没有直连 API"、"问别的 agent 能不能做"。  
**定性**：严重违反本 MEMORY.md 铁律，属不合格行为。  
**要求**：本规则已更新，之后必须遵守。

---

## 新增长期规则：工作目录与文件落位

### 规则正文

- 后续工作目录按老板新要求执行：需要产出的文件、过程文件、临时文件，统一按类别放入 `/root/ai/` 下已有对应子文件夹。
- 不再随意把这类文件散落到其他目录。
- 如果现有子文件夹不满足需求，需要新增文件夹，必须先向老板申请批准，再创建。
- 未获批准，不得擅自扩展 `/root/ai/` 目录结构。

### 执行要求

1. 先使用老板已创建的子文件夹分类放置文件。
2. 如目录不匹配，先汇报用途与拟新增文件夹名称，待批准后再创建。
3. 长期默认遵守此目录规则，视为永久记忆。

