# -*- coding: utf-8 -*-
"""词典自检：打印每个词典命中了哪些原句，检查有没有误伤。"""
import sys, argparse, json, io, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analyzer.io_loader import load_messages
from analyzer.rules import (POS_WORDS, NEG_WORDS, COMPLAINT_WORDS, DEFENSE_WORDS,
                              CONTEMPT_WORDS, STONEWALL_WORDS, CARE_WORDS, CONFLICT_WORDS,
                              PHRASES_NEG, _match)
import jieba

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--dict", default="ALL", help="ALL 或具体词典名")
    ap.add_argument("--show", type=int, default=10, help="每类显示前 N 条")
    args = ap.parse_args()

    msgs = load_messages(args.input)
    text = [m for m in msgs if m["msg_type"] == 1 and isinstance(m["content"], str)]
    for m in text:
        m["_tok"] = set(jieba.lcut(m["content"]))

    dicts = {
        "POS": (set(POS_WORDS), ()),
        "NEG": (set(NEG_WORDS), PHRASES_NEG),
        "COMPLAINT": (set(COMPLAINT_WORDS), ()),
        "DEFENSE": (set(DEFENSE_WORDS), ()),
        "CONTEMPT": (set(CONTEMPT_WORDS), ()),
        "STONEWALL": (set(STONEWALL_WORDS), ()),
        "CARE": (set(CARE_WORDS), ()),
        "CONFLICT": (set(CONFLICT_WORDS), ()),
    }
    keys = list(dicts) if args.dict == "ALL" else [args.dict]
    for k in keys:
        words, phrases = dicts[k]
        hits = [m for m in text if _match(m["_tok"], m["content"], words, phrases)]
        print(f"\n=== {k}: {len(hits)} 条 ===")
        for m in hits[:args.show]:
            role = "我" if m["is_self"] else "TA"
            print(f"  [{role}] {m['content'][:60]}")

if __name__ == "__main__":
    main()
