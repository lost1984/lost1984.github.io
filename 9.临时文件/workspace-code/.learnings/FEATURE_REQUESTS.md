## [FEAT-20260328-001] douyu_scheduled_recorder

**Logged**: 2026-03-28T11:22:00Z
**Priority**: medium
**Status**: pending
**Area**: backend

### Requested Capability
按固定时间检查斗鱼指定直播间，若在线则自动录播到本地。

### User Context
用户需要在每晚 22:00 和 23:00 自动检查指定斗鱼房间（22619），希望发现目标内容时录制到本地。由于“有妹子跳舞”属于主观视觉判断，MVP 先收敛为“能拿到直播流就录”。

### Complexity Estimate
medium

### Suggested Implementation
先落地 Python + ffmpeg + cron 的本地录播 MVP；后续可增加截图识别/视觉判断层。

### Metadata
- Frequency: first_time
- Related Features: douyu stream recorder, scheduled capture

---
## [REQ-20260328-001] trigger_recording_by_visual_layout

**Logged**: 2026-03-28T22:02:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
User wants recording to start based on visual detection of "三块相似主体区域" or "两块相似主体区域", not by a fixed schedule.

### Details
Target behavior: periodically sample Minana's live room, detect whether the frame contains 3 similar主体区域 or 2 similar主体区域, and only then start recording.

### Suggested Action
Build a Minana-specific visual trigger pipeline: capture frame -> detect repeated person-like regions / repeated similar sub-images -> if matched, start `douyu_recorder.py`.

### Metadata
- Source: conversation
- Related Files: douyu_recorder.py
- Tags: vision, trigger, automation, douyu

---
