# 💬 wechat-relationship-analyzer

**微信聊天记录关系分析器 · 看看 TA 到底爱不爱你**

把你和 TA 的微信聊天记录喂给它，它用心理学方法告诉你这段关系怎么样。全本地运行，聊天记录一个字都不上传。

> 中文也能搜到：微信聊天记录分析 / 情侣关系分析 / 聊天记录看感情 / 微信导出分析 / Gottman 比率

---

## 效果预览

### 基础版

![基础版](https://cdn.jsdelivr.net/gh/liucheshang/wechat-relationship-analyzer@main/preview.png)

### 详细版

![详细版](https://cdn.jsdelivr.net/gh/liucheshang/wechat-relationship-analyzer@main/preview_detail.png)

---

## 它能干什么？

简单说：它读你的聊天记录，然后告诉你——

| 你想知道的 | 它怎么回答 |
|---|---|
| 谁更主动？谁更爱谁？ | 统计谁先开口、谁发语音、谁关心谁多 |
| 最近变热还是变冷？ | Gottman 积极/消极比率趋势线 |
| 吵架后怎么和好的？ | 事件研究：吵完消息量暴增说明什么 |
| TA 分享好事时你在听吗？ | Capitalization 四种回应方式占比 |
| 有没有危险信号？ | 四骑士（批评/防御/蔑视/筑墙）趋势 |
| 你们都在聊什么？ | AI 自动聚类成 10 个话题 |

它用的是心理学家研究了几十年的指标（Gottman 婚姻实验室、Sternberg 爱情三角、Gable 2004 好事回应等），但结论是大白话。

---

## 怎么用？

### 第一步：装环境

```bash
# 需要 Python 3.10+
pip install -r requirements.txt
```

> 详细版还需：`pip install sentence-transformers scikit-learn`
> 终极版还需：安装 [Ollama](https://ollama.com) 并 `ollama pull qwen2.5:3b`

### 第二步：导出聊天记录

把你和某个人的聊天记录导出成一个 JSON 文件，格式：

```json
[
  {
    "ts": 1700000000.0,
    "sender": "TA的昵称",
    "content": "今天吃到一家特别好吃的火锅！",
    "msg_type": 1,
    "is_self": false
  }
]
```

`msg_type`：1=文字 3=图片 34=语音 43=视频 47=表情 50=通话

### 第三步：跑分析

```bash
# 基础版（几秒钟出结果）
python run.py --input messages.json --output ./output/

# 详细版（加话题聚类）
python run.py --input messages.json --output ./output/ --with-cluster

# 终极版（加 AI 语义判断）
python run.py --input messages.json --output ./output/ --with-cluster --with-llm
```

### 第四步：让 AI 写报告

把 `output/` 里生成的 JSON 文件，连同下面这个提示词，一起丢给任意 AI（豆包、WorkBuddy、ChatGPT、Claude 都行）：

```
你是资深亲密关系分析师。下面是我和 TA 的微信聊天记录统计数据。
请生成一份报告，包含：
1. 互动模式：谁更主动、回复速度、话题主导权
2. 情感状态：Gottman 比率趋势、情绪波动、最近是热是冷
3. 关系质量：吵架修复方式、四骑士信号、好事回应率
4. 性格画像：TA 是什么性格、我是什么性格、我们配不配
5. 改进建议：TA 该改什么、我该改什么、我们该怎么磨合

要求：结论要有数据支撑，语气直接不啰嗦，用判词式短语总结。
```

---

## 它看了哪些心理学指标？

| 指标 | 大白话 | 健康参考 |
|---|---|---|
| Gottman 比率 | 夸对方多还是骂对方多 | 健康关系 5:1 |
| 四骑士 | 批评/防御/蔑视/筑墙频率 | 越少越好 |
| 爱情三角 | 亲密/激情/承诺三条线 | 长期关系都要稳 |
| Capitalization | TA 说好事你是真开心还是敷衍 | 一起开心占 30%+ |
| 接住率 | TA 发的小信号你有没有接住 | 86%+ |
| 事件研究 | 吵架后系统怎么恢复 | 突然波动=预警 |

---

## 隐私

- 所有计算都在你自己电脑上跑
- 聊天记录不会发到任何服务器
- 不联网、不上传、不注册

---

## 注意

- 它不是心理咨询，只是帮你从数据里看见模式
- 结论是统计学推断，不是读心术
- 打字冷淡可能只是习惯，线上热情也可能只是客套
- 真有问题找专业咨询师

---

## License

MIT
