# 微信聊天记录关系分析 · 一键生成报告提示词

> 用法：把下面整段（提示词 + 模拟数据 JSON）一起发给豆包 / Claude / Kimi / 任意 AI，
> 它会生成一份完整的深色风格 HTML 关系分析报告。
> 你自己跑完分析工具后，把 JSON 换成你自己的 stats.json 就行。

---

## 提示词（直接复制下面全部内容发给 AI）

你是一位资深亲密关系分析师，擅长用聊天记录数据解读关系。

下面是我和 TA 的微信聊天记录统计结果。请生成一份完整的深色风格 HTML 报告。

### 硬性要求
1. 所有数字必须来自下面的数据，不许编造；找不到的字段写"样本不足"
2. 配色固定：背景 #0f1115，面板 #1a1d24，你=蓝 #60a5fa，TA=粉 #f778ba，强调=紫 #a78bfa
3. 图表用 ECharts（CDN 引入），颜色从上面取
4. 末尾加声明：本报告为统计推断，非心理诊断
5. 单文件自包含 HTML，直接保存 .html 可打开
6. 左侧固定目录导航，右侧内容滚动，目录高亮跟随滚动

### 报告结构（按顺序）
1. **总览**：核心KPI卡片 + 关系判词（三行：关系总断/TA画像/你画像）
2. **互动模式**：谁更主动、回复速度、消息长度、深夜聊天
3. **情感趋势**：Gottman比率月度折线、四骑士对比、爱情三角三线
4. **关系动态**：爱的五种语言、权力动态、情绪同步性
5. **冲突与修复**：吵架时间线、关系韧性评分、谁先和好
6. **话题分布**：8大话题双向对比条形图
7. **改进建议**：TA该改什么、你该改什么、互相该怎么磨合

### 数据（模拟示例）

```json
{
  "period": {"start": "2024-05-15", "end": "2025-02-20", "days": 280},
  "total_messages": 32900,
  "by_sender": {"self": 22300, "her": 10600},
  "self_ratio": 0.678,
  "her_ratio": 0.322,
  "her_initiate_rate": 0.286,
  "her_initiate_days": 80,
  "max_silence_days": 3,
  "reply_median_minutes": {"self": 8, "her": 72},
  "reply_p90_minutes": {"self": 30, "her": 420},
  "avg_msg_len": {"self": 18.5, "her": 6.2},
  "late_night_msgs": {"self": 3200, "her": 890},
  "gottman_ratio": {"overall": 2.1, "monthly": [3.2, 2.8, 2.1, 1.8, 1.5, 1.2, 1.8, 2.0, 2.3, 1.9]},
  "four_horsemen": {
    "criticism": {"self": 28, "her": 12},
    "defensiveness": {"self": 45, "her": 8},
    "contempt": {"self": 6, "her": 19},
    "stonewalling": {"self": 3, "her": 38}
  },
  "love_triangle": {
    "intimacy": {"self": 1200, "her": 680},
    "passion": {"self": 850, "her": 320},
    "commitment": {"self": 420, "her": 95}
  },
  "love_languages": {
    "affirmation": {"self": 89, "her": 23},
    "service": {"self": 214, "her": 76},
    "gifts": {"self": 12, "her": 3},
    "time": {"self": 3200, "her": 890},
    "touch": {"self": 45, "her": 8}
  },
  "power": {
    "end_convo": {"self": 67, "her": 156},
    "compromise": {"self": 189, "her": 45},
    "questions": {"self": 1240, "her": 320}
  },
  "emotion_sync": {"correlation": -0.32},
  "resilience": {
    "total_conflicts": 14,
    "repaired": 11,
    "avg_silence_hours": 42,
    "self_first_repair": 9,
    "her_first_repair": 2
  },
  "topics": {
    "家庭": {"self": 340, "her": 180},
    "朋友": {"self": 280, "her": 150},
    "工作": {"self": 560, "her": 320},
    "钱": {"self": 120, "her": 45},
    "感情": {"self": 890, "her": 230},
    "身体": {"self": 180, "her": 90},
    "娱乐": {"self": 420, "her": 280},
    "出行": {"self": 260, "her": 110}
  },
  "nicknames": {"self_uses": 45, "her_uses": 12},
  "care_count": {"self_to_her": 214, "her_to_self": 76}
}
```

---

## 说明

- 上面的 JSON 是**模拟数据**，对应"单向投入型（你追TA跑）"的关系模式
- 你自己跑完 `python run.py` 后，把生成的 `stats.json` 替换进去就行
- 不同 AI 生成的报告风格会不一样，但数据结论是一致的
- 这就是这个项目的核心价值：**本地算数字，AI 出报告，隐私不泄露**
