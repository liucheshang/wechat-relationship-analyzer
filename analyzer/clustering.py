# -*- coding: utf-8 -*-
"""话题聚类：embedding + KMeans。可选模块，需要 sentence-transformers。"""
from collections import Counter

def cluster_topics(text_msgs, k=20, min_len=6):
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.cluster import KMeans
    except ImportError:
        return {"error": "需要 pip install sentence-transformers scikit-learn", "clusters": []}

    texts = [m["content"] for m in text_msgs if len(m["content"]) >= min_len]
    if len(texts) < 100:
        return {"error": "文本消息太少（<100），跳过聚类", "clusters": []}

    model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    emb = model.encode(texts, show_progress_bar=True, batch_size=128)
    km = KMeans(n_clusters=min(k, len(texts)//50), random_state=42, n_init=5)
    labels = km.fit_predict(emb)

    clusters = []
    texts_by_label = {}
    for t, l in zip(texts, labels):
        texts_by_label.setdefault(l, []).append(t)
    for l, ts in sorted(texts_by_label.items(), key=lambda x: -len(x[1])):
        words = Counter()
        for t in ts:
            for w in t:
                if len(w) >= 2: words[w] += 1
        clusters.append({
            "size": len(ts),
            "top_words": [w for w, _ in words.most_common(10)],
            "samples": ts[:3],
        })
    return {"total_texts": len(texts), "k": k, "clusters": clusters}
