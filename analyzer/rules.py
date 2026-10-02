# -*- coding: utf-8 -*-
"""
规则引擎：全量统计所有指标。
不依赖大模型，纯关键词 + 时间戳统计。
性能：预按月分组，O(n) 单趟扫描。
"""
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

# ---------- 词典 ----------
POS_WORDS = "开心 高兴 喜欢 爱 想你 宝贝 宝宝 老公 老婆 谢谢 好的 好呀 哈哈 嘿嘿 嗯嗯 可以 行 棒 赞 可爱 美 帅 舒服 幸福 温暖 感动 期待 终于 太好了 不错 可以的 没问题".split()
NEG_WORDS = "生气 烦 讨厌 不想 别 滚 分手 算了 呵呵 无语 失望 难过 哭 委屈 累 困 饿 忙 无聊 烂 差 糟糕 气 愤怒 争吵 吵 冷战 不理 随便".split()
CONFLICT_WORDS = "分手 吵架 吵 生气 烦 讨厌 算了 呵呵 无语 失望 难过 哭 委屈 冷战 不理 随便 滚 别 不想 不行 不对 错误 你总是 你从不 凭什么 为什么 解释 道歉 对不起".split()
LOVE_WORDS = ["爱你","喜欢你","想你","宝贝","宝宝","老公","老婆","么么","亲亲","抱抱","晚安","早安","在乎","心疼"]
FUTURE_WORDS = ["以后","下次","一起","以后我们","将来","未来","计划","旅行","旅游","见家长","结婚","买房","同居","我们"]
COMPLAINT_WORDS = ["你总是","你从不","你能不能","你怎么","你就不会","凭什么","你应该","你必须","每次你"]
DEFENSE_WORDS = ["不是我","那是因为","我没有","我也没办法","你也","你不也","我不是故意","本来就是"]
CONTEMPT_WORDS = ["呵呵","你可真行","随便你","无所谓","笑死","切","幼稚","可笑","你开心就好"]
STONEWALL_WORDS = ["算了","不想说","无所谓","随便","不说了","别讲","沉默","哦","嗯","好吧","行"]
CARE_WORDS = ["累吗","吃饭了吗","睡了吗","在干嘛","多喝水","注意身体","早点睡","冷不冷","饿不饿","开心吗","怎么了","不舒服吗","没事吧"]
NICKNAMES = ["宝贝","宝宝","乖乖","亲爱的","老公","老婆","猪猪","老婆大人","老公大人","哈尼","达令"]


def month_key(dt):
    return f"{dt.year}-{dt.month:02d}"


def _count_in(text_list, words):
    """批量统计：text_list 中包含任一 word 的消息条数。"""
    n = 0
    for c in text_list:
        if any(w in c for w in words):
            n += 1
    return n


def run_rules(msgs):
    """输入全部消息，输出所有规则指标。O(n) 单趟扫描。"""
    # 预分组：按月
    months_set = sorted(set(month_key(m["dt"]) for m in msgs))
    months = months_set
    by_month_self = defaultdict(list)
    by_month_her = defaultdict(list)
    by_month_all = defaultdict(list)
    by_month_total = defaultdict(int)

    for m in msgs:
        if m["msg_type"] != 1 or not isinstance(m["content"], str):
            continue
        mo = month_key(m["dt"])
        c = m["content"]
        by_month_total[mo] += 1
        by_month_all[mo].append(c)
        if m["is_self"]:
            by_month_self[mo].append(c)
        else:
            by_month_her[mo].append(c)

    all_self = [m["content"] for m in msgs if m["msg_type"] == 1 and m["is_self"] and isinstance(m["content"], str)]
    all_her = [m["content"] for m in msgs if m["msg_type"] == 1 and not m["is_self"] and isinstance(m["content"], str)]

    result = {"months": months}

    result["monthly_volume"] = {
        "self": [len(by_month_self[mo]) for mo in months],
        "her":  [len(by_month_her[mo]) for mo in months],
    }

    gottman = []
    for mo in months:
        pos = _count_in(by_month_self[mo], POS_WORDS) + _count_in(by_month_her[mo], POS_WORDS)
        neg = _count_in(by_month_self[mo], NEG_WORDS) + _count_in(by_month_her[mo], NEG_WORDS)
        gottman.append(round(pos / max(1, neg), 2))
    result["gottman"] = gottman

    result["horsemen"] = {
        "complaint_self": [_count_in(by_month_self[mo], COMPLAINT_WORDS) for mo in months],
        "defense_self":   [_count_in(by_month_self[mo], DEFENSE_WORDS) for mo in months],
        "contempt_her":   [_count_in(by_month_her[mo], CONTEMPT_WORDS) for mo in months],
        "stonewall_all":   [_count_in(by_month_all[mo], STONEWALL_WORDS) for mo in months],
    }

    passion_words = ["么么","亲亲","抱抱","想你","宝贝","老公","老婆"]
    result["sternberg"] = {
        "intimacy":  [round(_count_in(by_month_all[mo], LOVE_WORDS) / max(1, by_month_total[mo]) * 1000, 1) for mo in months],
        "passion":   [round(_count_in(by_month_all[mo], passion_words) / max(1, by_month_total[mo]) * 1000, 1) for mo in months],
        "commitment":[round(_count_in(by_month_all[mo], FUTURE_WORDS) / max(1, by_month_total[mo]) * 1000, 1) for mo in months],
    }

    result["care"] = {
        "self": _count_in(all_self, CARE_WORDS),
        "her":  _count_in(all_her, CARE_WORDS),
    }

    result["address"] = {
        "her_calls_you": {w: sum(1 for c in all_her if w in c) for w in NICKNAMES},
        "you_call_her":  {w: sum(1 for c in all_self if w in c) for w in NICKNAMES},
    }

    days = sorted(set(m["dt"].date() for m in msgs))
    day_open = {"self": 0, "her": 0}
    for d in days:
        day_msgs = [m for m in msgs if m["dt"].date() == d]
        if not day_msgs:
            continue
        first = day_msgs[0]
        if first["msg_type"] == 10000:
            continue
        if first["is_self"]:
            day_open["self"] += 1
        else:
            day_open["her"] += 1
    result["day_open"] = day_open

    result["calls"] = {
        "self": sum(1 for m in msgs if m["msg_type"] == 50 and m["is_self"]),
        "her":  sum(1 for m in msgs if m["msg_type"] == 50 and not m["is_self"]),
    }
    result["voice"] = {
        "self": sum(1 for m in msgs if m["msg_type"] == 34 and m["is_self"]),
        "her":  sum(1 for m in msgs if m["msg_type"] == 34 and not m["is_self"]),
    }

    delays_self, delays_her = [], []
    for i in range(1, len(msgs)):
        dt_min = (msgs[i]["ts"] - msgs[i-1]["ts"]) / 60
        if dt_min > 120 or dt_min < 0:
            continue
        if msgs[i]["is_self"] and not msgs[i-1]["is_self"]:
            delays_self.append(dt_min)
        elif not msgs[i]["is_self"] and msgs[i-1]["is_self"]:
            delays_her.append(dt_min)

    def _median(lst):
        if not lst:
            return 0
        s = sorted(lst)
        n = len(s)
        return round(s[n//2], 1) if n % 2 else round((s[n//2-1] + s[n//2]) / 2, 1)

    result["reply_delay"] = {
        "self_median": _median(delays_self),
        "her_median":  _median(delays_her),
        "self_samples": len(delays_self),
        "her_samples":  len(delays_her),
    }

    streak_self = streak_her = 1
    max_self = max_her = 1
    for i in range(1, len(msgs)):
        same = msgs[i]["is_self"] == msgs[i-1]["is_self"]
        if same:
            if msgs[i]["is_self"]:
                streak_self += 1
                max_self = max(max_self, streak_self)
            else:
                streak_her += 1
                max_her = max(max_her, streak_her)
        else:
            if msgs[i]["is_self"]:
                streak_self = 1
            else:
                streak_her = 1
    result["max_streak"] = {"self": max_self, "her": max_her}

    return result
