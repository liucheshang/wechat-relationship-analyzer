# 一键生成关系报告 · 完整提示词

> 用法：把下面整段（提示词 + sample_stats.json 内容）一起发给任意 AI，
> AI 会生成一份完整的深色风格 HTML 关系分析报告。

---

## 提示词（直接复制下面全部内容发给 AI）

你是一位资深亲密关系分析师，擅长用聊天记录数据解读关系。

下面是我和 TA 的微信聊天记录统计结果（stats.json）。请生成一份完整的深色风格 HTML 报告。

### 全局设置
- 配色：背景 #0f1115，面板 #1a1d24，边框 #2a2d35，正文 #e9eef4，次要文字 #8a93a6
- 你（self）= 蓝色 #60a5fa
- TA（her）= 粉色 #f778ba
- 强调色 = 紫色 #a78bfa
- 好/积极 = 绿色 #4ade80
- 坏/消极 = 红色 #f87171
- 警告/注意 = 金色 #fbbf24
- 图表用 ECharts（CDN: https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js）
- 单文件自包含 HTML，所有CSS/JS内联，直接保存 .html 可打开
- 左侧固定目录导航（宽220px），右侧内容滚动，目录高亮跟随滚动
- 页面最大宽度 1000px，居中

### 数据字段说明（对照下面的 JSON）

**基础数据**
- `period`：起止时间和天数
- `total_messages`：总消息数
- `by_sender.self / her`：双方各自发了多少条
- `self_ratio / her_ratio`：双方占比
- `her_initiate_rate`：TA主动开场的比例
- `her_initiate_days / self_initiate_days`：双方主动开场天数
- `max_silence_days`：最长断联天数
- `reply_median_minutes`：双方回复中位数（分钟）
- `reply_p90_minutes`：双方回复P90（分钟，越高说明越慢）
- `avg_msg_len`：双方平均消息长度（字）
- `late_night_msgs`：深夜消息数（23-6点）
- `voice_msgs`：语音条数
- `emoji_count`：表情数

**情感指标**
- `gottman_ratio.overall`：Gottman比率（积极÷消极，健康关系约5:1）
- `gottman_ratio.monthly`：逐月Gottman比率，用折线图画趋势
- `gottman_ratio.months`：对应的月份标签
- `four_horsemen`：四骑士（批评/防御/蔑视/筑墙）双向对比，用分组柱状图
- `love_triangle`：爱情三角（亲密/激情/承诺）双向对比，用雷达图或分组柱状图

**关系动态**
- `love_languages`：爱的五种语言（肯定言辞/服务行动/礼物/精心时刻/身体接触）双向对比
- `power`：权力动态（谁更常结束对话/谁更常妥协/谁更常发问）
- `emotion_sync.correlation`：情绪同步性相关系数（-1到1，正=同步，负=反向）

**冲突与修复**
- `resilience`：关系韧性（总冲突数/和好数/平均静默小时/谁先和好）
- `conflict_timeline`：吵架时间线（每次冲突的起止时间/静默时长/谁先修复）

**话题分布**
- `topics`：8大话题（家庭/朋友/工作/钱/感情/身体/娱乐/出行）双向对比，用横向分组条形图

**其他**
- `nicknames`：双方互相用昵称的次数
- `care_count`：双方关心对方的次数
- `top_words_self / top_words_her`：双方高频词

### 报告结构（按顺序）

**第一部分：总览**
- 顶部大标题 + 副标题（时间范围）
- 4个KPI卡片：总消息数 / TA主动开场率 / 最长断联 / Gottman比率
- 三行判词：
  - 关系总断：根据数据判断是什么类型的关系
  - TA画像：根据TA的数据特征写判词
  - 你画像：根据你的数据特征写判词

**第二部分：互动模式**
- 谁更主动：双方开场天数对比
- 回复速度：中位数 + P90对比
- 消息长度：谁写得更长
- 深夜聊天：谁更爱半夜聊

**第三部分：情感趋势**
- Gottman比率月度折线图
- 四骑士对比柱状图
- 爱情三角雷达图或柱状图

**第四部分：关系动态**
- 爱的五种语言：双向对比
- 权力动态：谁更有话语权
- 情绪同步性：相关系数是正还是负

**第五部分：冲突与修复**
- 关系韧性评分：修复率多少
- 吵架时间线：列出每次冲突
- 谁先和好：9次里你先和好9次

**第六部分：话题分布**
- 8大话题双向对比条形图

**第七部分：改进建议**
- TA该改什么（3条）
- 你该改什么（3条）
- 互相该怎么磨合（2条）

**末尾**：加一行小字：本报告为统计推断，非心理诊断。如有情感困扰请咨询专业人士。

---

### 数据（sample_stats.json）

```json
{
  "period": {"start": "2024-05-15", "end": "2025-02-20", "days": 280},
  "total_messages": 32900,
  "by_sender": {"self": 22300, "her": 10600},
  "self_ratio": 0.678,
  "her_ratio": 0.322,
  "her_initiate_rate": 0.286,
  "her_initiate_days": 80,
  "self_initiate_days": 200,
  "max_silence_days": 3,
  "reply_median_minutes": {"self": 8, "her": 72},
  "reply_p90_minutes": {"self": 30, "her": 420},
  "avg_msg_len": {"self": 18.5, "her": 6.2},
  "late_night_msgs": {"self": 3200, "her": 890},
  "voice_msgs": {"self": 45, "her": 23},
  "emoji_count": {"self": 1890, "her": 480},
  "gottman_ratio": {
    "overall": 2.1,
    "monthly": [3.2, 2.8, 2.1, 1.8, 1.5, 1.2, 1.8, 2.0, 2.3, 1.9, 2.1, 2.0],
    "months": ["5月","6月","7月","8月","9月","10月","11月","12月","1月","2月","3月","4月"]
  },
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
  "conflict_timeline": [
    {"start": "2024-07-12 14:30", "end": "2024-07-12 20:15", "silence_hours": 18, "first_repairer": "self"},
    {"start": "2024-09-03 22:40", "end": "2024-09-04 10:20", "silence_hours": 36, "first_repairer": "self"},
    {"start": "2024-11-18 16:00", "end": "2024-11-19 09:30", "silence_hours": 24, "first_repairer": "self"}
  ],
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
  "care_count": {"self_to_her": 214, "her_to_self": 76},
  "top_words_self": ["宝宝", "哈哈哈", "嗯", "好吧", "想你", "吃饭了吗", "早点睡"],
  "top_words_her": ["嗯", "哦", "哈哈", "好吧", "行", "忙", "嗯呢"]
}
```
