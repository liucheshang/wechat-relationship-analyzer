# -*- coding: utf-8 -*-
"""
LLM 判断：用本地 Ollama 判断 Capitalization 回应类型（Gable 2004）。

v2：并发 4 路 + 断点续跑 + 如实标注抽样覆盖率。
"""
import json, os, io, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

PROMPT = """你是关系分析师。判断对方在分享好事后，另一方的回应属于哪类：
AC=主动建设性（追问、一起开心、"在哪吃的？拍给我"）
PC=被动建设性（"哦挺好""不错"）
AD=主动破坏性（泼冷水、指出问题、"这有什么好开心的"）
PD=被动破坏性（不接话、转移话题、单字回）

只输出一个词：AC / PC / AD / PD。

对方分享：{share}
我的回应：{reply}
判断："""

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
_print_lock = threading.Lock()


def _log(*a):
    with _print_lock:
        print(*a)


def _ask(prompt, model, timeout=60):
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode(),
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    return resp.get("response", "").strip().upper()


def _parse(label):
    for k in ("AC", "PC", "AD", "PD"):
        if k in label:
            return k
    return "?"


def judge_capitalization(msgs, sample=200, model="qwen2.5:3b",
                         workers=4, out_path=None):
    good = ["开心", "高兴", "喜欢", "好吃", "买到", "考上", "通过", "完成",
            "涨", "发了", "终于", "太好了", "哈哈", "嘿嘿", "赞", "棒"]
    segs = []
    for i, m in enumerate(msgs):
        if m["msg_type"] != 1 or m["is_self"]:
            continue
        if any(g in m["content"] for g in good) and len(m["content"]) >= 4:
            replies = []
            for j in range(i + 1, min(i + 5, len(msgs))):
                if msgs[j]["is_self"]:
                    replies.append(msgs[j]["content"])
                if len(replies) >= 2:
                    break
            if replies:
                segs.append({"share": m["content"], "reply": " | ".join(replies)})

    candidate = len(segs)
    if candidate == 0:
        return {"AC": 0, "PC": 0, "AD": 0, "PD": 0, "?": 0, "detail": [],
                "pct": {}, "candidate": 0, "judged": 0, "sampled": False}

    if sample and 0 < sample < candidate:
        import random
        random.seed(42)
        segs = random.sample(segs, sample)
        sampled = True
    else:
        sampled = False

    results = {"AC": 0, "PC": 0, "AD": 0, "PD": 0, "?": 0, "detail": []}
    done = set()
    if out_path and os.path.exists(out_path):
        try:
            old = json.load(io.open(out_path, encoding="utf-8"))
            for d in old.get("detail", []):
                if d.get("label") != "?":
                    done.add(d["share"])
                    results[d["label"]] += 1
                    results["detail"].append(d)
            if done:
                _log(f"  断点续跑：已有 {len(done)} 条结果，跳过")
        except Exception:
            pass

    todo = [s for s in segs if s["share"] not in done]
    if not todo:
        total = sum(v for k, v in results.items() if k != "detail")
        results["pct"] = {k: round(v / total * 100, 1)
                          for k, v in results.items() if k != "detail"}
        results.update({"candidate": candidate, "judged": total, "sampled": sampled})
        return results

    def work(s):
        p = PROMPT.format(share=s["share"][:200], reply=s["reply"][:200])
        try:
            lab = _parse(_ask(p, model))
        except Exception:
            lab = "?"
        return s, lab

    n_ok = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = [ex.submit(work, s) for s in todo]
        for k, f in enumerate(as_completed(futs), 1):
            s, lab = f.result()
            with _print_lock:
                results[lab] += 1
                results["detail"].append(
                    {"share": s["share"], "reply": s["reply"], "label": lab})
                if lab != "?":
                    n_ok += 1
            if k % 25 == 0 or k == len(todo):
                _log(f"  {k}/{len(todo)}  "
                     f"{ {kk: vv for kk, vv in results.items() if kk != 'detail'} }")
                if out_path:
                    snap = dict(results)
                    snap.update({"candidate": candidate, "sampled": sampled})
                    json.dump(snap, io.open(out_path, "w", encoding="utf-8"),
                              ensure_ascii=False, indent=2)

    total = sum(v for k, v in results.items() if k != "detail")
    results["pct"] = {k: round(v / total * 100, 1)
                      for k, v in results.items() if k != "detail"}
    results.update({
        "candidate": candidate,
        "judged": total,
        "sampled": sampled,
        "model": model,
        "coverage": round(total / candidate * 100, 1),
        "note": ("只抽样了部分候选，比例见 coverage；结论是抽样推断不是全量结论"
                 if sampled else "全量判断"),
    })
    return results
