# wechat-relationship-analyzer

用数据科学的方法分析你的私聊记录，输出亲密关系深度报告。

**全本地运行，不上传任何数据。**

---

## 效果预览

### 判词三联：一眼看清你们的关系

![判词三联](docs/preview_verdict.jpg)

### 心理学指标：Gottman / Capitalization / 话题聚类

![心理学框架](docs/preview_frameworks.jpg)

---

## 这是什么

把你和某个人的聊天记录导出成 JSON，然后这个工具会从 40+ 个维度量化分析你们的关系：

- 谁更主动、谁更爱谁
- Gottman 比率（积极 vs 消极互动，预测关系稳定性）
- Four Horsemen（批评/防御/蔑视/筑墙，Gottman 的离婚预测指标）
- Sternberg 爱情三角（亲密/激情/承诺）
- Capitalization（回应好消息的方式，Gable 2004）
- Bids for Connection（微小信号的接住率）
- Critical Slowing（关系稳定性的早期预警信号）
- 话题聚类（embedding + KMeans，你们到底在聊什么）
- 回复延迟、连发长度、关心次数、称呼变化时间线
- 冲突后修复模式（事件研究法）

输出一份单文件 HTML 报告，20+ 张 ECharts 图表。

---

## 快速开始

### 1. 准备数据

你需要先把聊天记录导出成 JSON。格式：

```json
[
  {
    "ts": 1700000000.0,
    "sender": "对方昵称",
    "sender_wxid": "wxid_xxx",
    "content": "消息文本",
    "msg_type": 1,
    "is_self": false,
    "is_group_chat": false
  }
]
```

`msg_type`：1=文本 3=图片 34=语音 43=视频 47=表情 49=链接 50=通话

### 2. 安装

```bash
pip install -r requirements.txt
```

### 3. 跑分析

```bash
# 基础版（规则统计，秒出结果）
python run.py --input messages.json --output ./output/

# 完整版（加话题聚类，需要 sentence-transformers）
python run.py --input messages.json --output ./output/ --with-cluster

# 终极版（加 LLM 判断，需要本地跑 Ollama + qwen2.5:3b）
python run.py --input messages.json --output ./output/ --with-cluster --with-llm
```

### 4. 看结果

`output/` 目录下：
- `stats.json` — 所有规则统计指标
- `clusters.json` — 话题聚类（如果开了 --with-cluster）
- `capitalization.json` — LLM 判断的回应类型分布（如果开了 --with-llm）

把这些 JSON 喂给任意大模型生成报告：

```
你是亲密关系分析师。请根据以下聊天记录统计数据，生成一份深度分析报告，
包含：互动模式、情感动态、关系稳定性、性格冲突、改进建议。
数据：{stats.json 内容}
```

---

## 指标参考

| 指标 | 理论来源 | 健康值 |
|---|---|---|
| Gottman 比率 | Gottman Institute | > 5:1 |
| Bids 接住率 | Gottman Love Lab | > 86% |
| Capitalization AC 占比 | Gable 2004 | 30-50% |
| Four Horsemen 频率 | Gottman | 越低越好 |
| Sternberg 承诺线 | Sternberg 1986 | 长期关系应稳定上升 |
| Critical Slowing variance | Scheffer 2012 | 突然翻倍 = 预警 |

---

## 隐私

- 全流程本地运行，无任何网络请求（除了 Ollama 本地推理）
- 不上传聊天记录、不上传昵称、不上传任何个人信息
- 你导出的 JSON 和生成的报告都在你自己的磁盘上

---

## 免责声明

- 本工具只做数据描述，不提供心理咨询
- 所有结论都是统计学推断，不是读心术
- 关系问题请找专业心理咨询师
- 导出自己的聊天记录可能违反相关软件用户协议，风险自担

---

## License

MIT
