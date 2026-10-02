# -*- coding: utf-8 -*-
"""
入口：python run.py --input wechat_messages.json --output ./output/
"""
import argparse, json, io, os
from analyzer.io_loader import load_messages, filter_text
from analyzer.rules import run_rules

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="wechat_messages.json 路径")
    ap.add_argument("--output", default="./output", help="输出目录")
    ap.add_argument("--with-cluster", action="store_true", help="跑话题聚类（需要 sentence-transformers）")
    ap.add_argument("--with-llm", action="store_true", help="跑 LLM Capitalization 判断（需要 Ollama）")
    args = ap.parse_args()

    os.makedirs(args.output, exist_ok=True)
    print(f"[1/4] 加载消息: {args.input}")
    msgs = load_messages(args.input)
    print(f"      共 {len(msgs)} 条消息")

    print("[2/4] 规则统计...")
    stats = run_rules(msgs)
    json.dump(stats, io.open(os.path.join(args.output, "stats.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"      月度 {len(stats['months'])} 个月，Gottman 比率范围 {min(stats['gottman']):.2f}~{max(stats['gottman']):.2f}")

    if args.with_cluster:
        print("[3/4] 话题聚类...")
        from analyzer.clustering import cluster_topics
        text = filter_text(msgs)
        result = cluster_topics(text)
        json.dump(result, io.open(os.path.join(args.output, "clusters.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"      {len(result.get('clusters', []))} 个话题簇")
    else:
        print("[3/4] 跳过聚类（加 --with-cluster 启用）")

    if args.with_llm:
        print("[4/4] LLM Capitalization 判断...")
        from analyzer.llm_judge import judge_capitalization
        result = judge_capitalization(msgs)
        json.dump(result, io.open(os.path.join(args.output, "capitalization.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"      AC {result['pct'].get('AC', 0)}% / PD {result['pct'].get('PD', 0)}%")
    else:
        print("[4/4] 跳过 LLM（加 --with-llm 启用）")

    print(f"\n完成。产物在 {args.output}/")
    print("下一步：把 stats.json + clusters.json + capitalization.json 喂给 LLM，或用 HTML 模板渲染报告。")

if __name__ == "__main__":
    main()
