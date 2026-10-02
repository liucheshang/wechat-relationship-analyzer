# -*- coding: utf-8 -*-
"""
入口：python run.py --input messages.json --output ./output/
"""
import argparse, json, io, os
from analyzer.io_loader import load_messages, filter_text
from analyzer.rules import run_rules

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="messages.json 路径")
    ap.add_argument("--output", default="./output", help="输出目录")
    ap.add_argument("--with-cluster", action="store_true", help="跑话题聚类（需 sentence-transformers）")
    ap.add_argument("--with-llm", action="store_true", help="跑 LLM 好事回应判断（需本地 Ollama）")
    ap.add_argument("--llm-sample", type=int, default=200,
                    help="LLM 抽样条数（默认 200；设 0 = 全跑）")
    args = ap.parse_args()

    os.makedirs(args.output, exist_ok=True)
    print(f"[1/4] 加载消息: {args.input}")
    msgs = load_messages(args.input)
    print(f"      共 {len(msgs)} 条消息")
    if not msgs:
        print("      没有可用消息，退出。")
        return

    print("[2/4] 规则统计...")
    stats = run_rules(msgs)
    json.dump(stats, io.open(os.path.join(args.output, "stats.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    g = [x for x in stats.get("gottman", []) if x is not None]
    if g:
        print(f"      月度 {len(stats['months'])} 个月，Gottman {min(g):.2f}~{max(g):.2f}")
    sil = stats.get("silence") or {}
    if sil.get("max_days"):
        print(f"      最长断联 {sil['max_days']:.1f} 天"
              f"（{sil.get('max_from')} → {sil.get('max_to')}）")
        if sil.get("empty_months"):
            print(f"      整月零交流：{', '.join(sil['empty_months'])}")
    rd = stats.get("reply_delay") or {}
    if rd:
        print(f"      回复延迟中位数 我 {rd.get('self_median')} / TA {rd.get('her_median')} 分钟"
              f"（P90：我 {rd.get('self_p90')} / TA {rd.get('her_p90')}）")

    if args.with_cluster:
        print("[3/4] 话题聚类...")
        from analyzer.clustering import cluster_topics
        text = filter_text(msgs)
        result = cluster_topics(text)
        json.dump(result, io.open(os.path.join(args.output, "clusters.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        if result.get("error"):
            print(f"      跳过：{result['error']}")
        else:
            print(f"      {len(result.get('clusters', []))} 个话题簇")
    else:
        print("[3/4] 跳过聚类（加 --with-cluster 启用）")

    if args.with_llm:
        print("[4/4] LLM 好事回应判断...")
        from analyzer.llm_judge import judge_capitalization
        cap_path = os.path.join(args.output, "capitalization.json")
        result = judge_capitalization(msgs, sample=args.llm_sample, out_path=cap_path)
        json.dump(result, io.open(cap_path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"      AC {result['pct'].get('AC', 0)}% / PD {result['pct'].get('PD', 0)}%"
              f"（判断 {result.get('judged', 0)} 条 / 候选 {result.get('candidate', 0)} 条，"
              f"覆盖 {result.get('coverage', 0)}%）")
    else:
        print("[4/4] 跳过 LLM（加 --with-llm 启用）")

    print(f"\n完成。产物在 {args.output}/")
    print("下一步：把 stats.json 喂给 AI 写报告，或看 docs/ 示例页面。")

if __name__ == "__main__":
    main()
