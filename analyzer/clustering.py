# -*- coding: utf-8 -*-
"""话题聚类：embedding + KMeans。可选模块，需要 sentence-transformers。"""
from collections import Counter

def cluster_topics(text_msgs, k=20, min_len=6):
    """
    输入文本消息列表，输出 k 个话题簇。
    需要：pip install sentence-transformers scikit-learn jieba
    """
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

    try:
        import jieba
        use_jieba = True
    except ImportError:
        use_jieba = False

    clusters = []
    texts_by_label = {}
    for t, l in zip(texts, labels):
        texts_by_label.setdefault(l, []).append(t)
    for l, ts in sorted(texts_by_label.items(), key=lambda x: -len(x[1])):
        words = Counter()
        for t in ts:
            if use_jieba:
                for w in jieba.cut(t):
                    w = w.strip()
                    if len(w) >= 2 and not w.isdigit():
                        words[w] += 1
            else:
                for i in range(len(t)-1):
                    w = t[i:i+2]
                    if not w.isdigit():
                        words[w] += 1
        clusters.append({
            "size": len(ts),
            "top_words": [w for w, _ in words.most_common(10)],
            "samples": ts[:3],
        })
    return {"total_texts": len(texts), "k": k, "clusters": clusters}
