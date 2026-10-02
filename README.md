# 💬 wechat-relationship-analyzer

**把你和 TA 的聊天记录喂给它，它告诉你这段关系到底怎么样。**

全本地运行，你的聊天记录一个字都不会上传。

---

## 效果预览

![示例报告](https://cdn.jsdelivr.net/gh/liucheshang/wechat-relationship-analyzer@main/preview.png)

---

## 它能干什么？

简单说：它读你的聊天记录，然后告诉你——

- 谁更主动？谁更爱谁？
- 你们最近是在变热还是变冷？
- 吵架之后你们是怎么和好的？
- TA 分享好事的时候，你是真的在听，还是在敷衍？
- 你们这段关系有没有危险信号？
- 你们到底都在聊些什么？

它用的是心理学家研究了几十年的指标（Gottman 婚姻实验室、Sternberg 爱情三角理论等），但结论是大白话。

---

## 怎么用？

### 第一步：导出聊天记录

把你和某个人的聊天记录导出成一个 JSON 文件。格式长这样：

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

（`msg_type`：1=文字 3=图片 34=语音 43=视频 47=表情 50=通话）

### 第二步：跑分析

```bash
pip install -r requirements.txt

# 基础版（几秒钟出结果）
python run.py --input messages.json --output ./output/

# 完整版（加话题分析，需要装 sentence-transformers）
python run.py --input messages.json --output ./output/ --with-cluster

# 终极版（加 AI 判断，需要本地跑 Ollama）
python run.py --input messages.json --output ./output/ --with-cluster --with-llm
```

### 第三步：看结果

`output/` 里会生成几个 JSON 文件，把它们喂给任意 AI 大模型，用下面这个提示词就能生成一份漂亮的报告：

```
你是亲密关系分析师。根据下面的聊天记录统计数据，
生成一份报告：你们的互动模式、情感状态、关系稳定性、
性格冲突、以及改进建议。
```

---

## 它看了哪些指标？

| 它看什么 | 大白话解释 | 健康参考 |
|---|---|---|
| Gottman 比率 | 你们夸对方多还是骂对方多 | 健康关系是 5:1 |
| 四骑士 | 批评/防御/蔑视/冷战出现的频率 | 越少越好 |
| 爱情三角 | 亲密感/激情/未来承诺三条线 | 长期关系三条线都要稳 |
| 好事回应率 | TA 说好事时你是真开心还是敷衍 | 一起开心应占 30%+ |
| 接住率 | TA 发的小信号你有没有接住 | 86% 以上才健康 |
| 系统稳定性 | 吵架前系统有没有预警 | 突然波动 = 危险信号 |

---

## 隐私

- 所有计算都在你自己电脑上跑
- 你的聊天记录不会发到任何服务器
- 不联网、不上传、不注册

---

## 注意

- 它不是心理咨询，只是帮你从数据里看见模式
- 结论是统计学推断，不是读心术
- 真有问题还是找专业咨询师

---

## License

MIT
