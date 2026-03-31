# 斗鱼定时录播 MVP（streamlink 版）

目标：每天 **22:00** 和 **23:00** 检查并录制房间 `https://www.douyu.com/22619`。

当前版本策略：
- **通过 streamlink + douyu 插件 获取真实流**
- **只要能拿到直播流就录制**
- **暂不做“有妹子跳舞”视觉判断**
- 单次默认最长录 **120 分钟**

## 文件

- `douyu_recorder.py`：主脚本
- `install_douyu_recorder.sh`：安装 cron 定时任务

## 依赖

Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y python3 ffmpeg streamlink curl
```

## 下载 Douyu 插件

```bash
mkdir -p "$HOME/douyu-recorder/plugins"
curl -L https://raw.githubusercontent.com/v2wy/streamlink-plugin-for-douyu/master/douyu.py \
  -o "$HOME/douyu-recorder/plugins/douyu.py"
```

## 手动测试

```bash
python3 douyu_recorder.py \
  --room-url 'https://www.douyu.com/22619' \
  --room-id '5551871' \
  --room-alias 'douyu_22619' \
  --plugin-dir "$HOME/douyu-recorder/plugins" \
  --outdir "$HOME/videos/douyu"
```

测试 5 分钟可这样跑：

```bash
python3 douyu_recorder.py \
  --room-url 'https://www.douyu.com/6295904?dyshid=b72aa56-5348593090ef60b8c8bb643700021701' \
  --room-id '6295904' \
  --room-alias 'douyu_test_6295904' \
  --plugin-dir "$HOME/douyu-recorder/plugins" \
  --outdir "$HOME/videos/douyu" \
  --max-minutes 5
```

如果你怀疑 room_id 变了，可以试：

```bash
python3 douyu_recorder.py \
  --room-url 'https://www.douyu.com/22619' \
  --resolve-room-id
```

## 安装定时任务

```bash
bash install_douyu_recorder.sh
```

安装后：

```bash
crontab -l
```

会看到两条任务：
- `0 22 * * * ...`
- `0 23 * * * ...`

## 输出位置

- 录播目录：`$HOME/videos/douyu`
- 日志目录：`$HOME/douyu-recorder/logs`
- 插件目录：`$HOME/douyu-recorder/plugins`

## 注意事项

1. 斗鱼兼容性主要取决于 `streamlink` 和 `douyu.py` 插件是否还能用。
2. 如果插件失效，优先更新 `douyu.py`，不要先折腾主脚本。
3. ffmpeg 用 `-c copy`，速度快，不转码；如果源流异常，后续可改为转码模式。
4. 这个版本是 **MVP**，先保证“定时检查 + 能录就录”。

## 下一步可加

1. 开播前先抓封面/截图，做粗识别后再录。
2. 录完后自动剪掉前后无效片段。
3. 录制成功后发飞书提醒。
4. 支持多个房间轮询。
