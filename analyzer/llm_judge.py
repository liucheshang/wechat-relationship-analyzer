# -*- coding: utf-8 -*-
"""LLM 判断：用本地 Ollama 判断 Capitalization 回应类型。"""
import json, urllib.request

PROMPT = """你是关系分析师。判断对方在分享好事后，另一方的回应属于哪类：
AC=主动建设性（追问、一起开心、"在哪吃的？拍给我"）
PC=被动建设性（"哦挺好""不错"）
AD=主动破坏性（泼冷水、指出问题、"这有什么好开心的"）
PD=被动破坏性（不接话、转移话题、单字回）

只输出一个词：AC / PC / AD / PD。

对方分享：{share}
我的回应：{reply}
判断："""

def judge_capitalization(msgs, sample=200, model="qwen2.5:3b"):
    good = ["开心","高兴","喜欢","好吃","买到","考上","通过","完成","涨","发了","终于","太好了","哈哈","嘿嘿","赞","棒"]
    segs = []
    for i, m in enumerate(msgs):
        if m["msg_type"] != 1 or m["is_self"]: continue
        if any(g in m["content"] for g in good) and len(m["content"]) >= 4:
            replies = []
            for j in range(i+1, min(i+5, len(msgs))):
                if msgs[j]["is_self"]:
                    replies.append(msgs[j]["content"])
                if len(replies) >= 2: break
            if replies:
                segs.append({"share": m["content"], "reply": " | ".join(replies)})

    import random
    random.seed(42)
    sample_segs = random.sample(segs, min(sample, len(segs)))

    results = {"AC": 0, "PC": 0, "AD": 0, "PD": 0, "?": 0, "detail": []}
    for i, s in enumerate(sample_segs):
        prompt = PROMPT.format(share=s["share"][:200], reply=s["reply"][:200])
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/generate",
                data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode(),
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
            label = resp.get("response", "").strip().upper()[:2]
        except Exception:
            label = "?"
        if label not in results: label = "?"
        results[label] += 1
        results["detail"].append({"share": s["share"], "reply": s["reply"], "label": label})
        if (i+1) % 20 == 0:
            print(f"  {i+1}/{len(sample_segs)}  { {k:v for k,v in results.items() if k!='detail'} }")

    total = sum(v for k, v in results.items() if k != "detail")
    results["pct"] = {k: round(v/total*100, 1) for k, v in results.items() if k != "detail"}
    return results
