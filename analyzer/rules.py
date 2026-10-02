# -*- coding: utf-8 -*-
"""
规则引擎：全量统计所有指标。
不依赖大模型，纯关键词 + 时间戳统计。
"""
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

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

def month_key(dt):
    return f"{dt.year}-{dt.month:02d}"

def run_rules(msgs):
    text = [m for m in msgs if m["msg_type"] == 1 and isinstance(m["content"], str)]
    by_self = [m for m in text if m["is_self"]]
    by_her = [m for m in text if not m["is_self"]]

    months = sorted(set(month_key(m["dt"]) for m in msgs))
    result = {"months": months}

    result["monthly_volume"] = {
        "self": [sum(1 for m in by_self if month_key(m["dt"]) == mo) for mo in months],
        "her":  [sum(1 for m in by_her if month_key(m["dt"]) == mo) for mo in months],
    }

    def count_words(msg_list, words):
        return sum(1 for m in msg_list if any(w in m["content"] for w in words))
    pos_self = [count_words([m for m in by_self if month_key(m["dt"]) == mo], POS_WORDS) for mo in months]
    neg_self = [count_words([m for m in by_self if month_key(m["dt"]) == mo], NEG_WORDS) for mo in months]
    pos_her  = [count_words([m for m in by_her if month_key(m["dt"]) == mo], POS_WORDS) for mo in months]
    neg_her  = [count_words([m for m in by_her if month_key(m["dt"]) == mo], NEG_WORDS) for mo in months]
    result["gottman"] = [
        round((pos_self[i]+pos_her[i]) / max(1, neg_self[i]+neg_her[i]), 2)
        for i in range(len(months))
    ]

    result["horsemen"] = {
        "complaint_self": [count_words([m for m in by_self if month_key(m["dt"]) == mo], COMPLAINT_WORDS) for mo in months],
        "defense_self":   [count_words([m for m in by_self if month_key(m["dt"]) == mo], DEFENSE_WORDS) for mo in months],
        "contempt_her":   [count_words([m for m in by_her if month_key(m["dt"]) == mo], CONTEMPT_WORDS) for mo in months],
        "stonewall_all":  [count_words([m for m in text if month_key(m["dt"]) == mo], STONEWALL_WORDS) for mo in months],
    }

    result["sternberg"] = {
        "intimacy":  [count_words([m for m in text if month_key(m["dt"]) == mo], LOVE_WORDS) / max(1, sum(1 for m in text if month_key(m["dt"]) == mo)) * 1000 for mo in months],
        "passion":   [count_words([m for m in text if month_key(m["dt"]) == mo], ["么么","亲亲","抱抱","想你","宝贝","老公","老婆"]) / max(1, sum(1 for m in text if month_key(m["dt"]) == mo)) * 1000 for mo in months],
        "commitment":[count_words([m for m in text if month_key(m["dt"]) == mo], FUTURE_WORDS) / max(1, sum(1 for m in text if month_key(m["dt"]) == mo)) * 1000 for mo in months],
    }

    result["care"] = {"self": count_words(by_self, CARE_WORDS), "her": count_words(by_her, CARE_WORDS)}
    result["address"] = {
        "laogong": sum(1 for m in by_her if "老公" in m["content"]),
        "laopo":   sum(1 for m in by_self if "老婆" in m["content"]),
        "baobao":  sum(1 for m in text if "宝宝" in m["content"]),
    }

    days = sorted(set(m["dt"].date() for m in msgs))
    day_open = {"self": 0, "her": 0}
    for d in days:
        day_msgs = [m for m in msgs if m["dt"].date() == d]
        if not day_msgs: continue
        first = day_msgs[0]
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
        dt = (msgs[i]["ts"] - msgs[i-1]["ts"]) / 60
        if dt > 120: continue
        if msgs[i]["is_self"] and not msgs[i-1]["is_self"]:
            delays_self.append(dt)
        elif not msgs[i]["is_self"] and msgs[i-1]["is_self"]:
            delays_her.append(dt)
    result["reply_delay"] = {
        "self_median": round(sorted(delays_self)[len(delays_self)//2], 1) if delays_self else 0,
        "her_median":  round(sorted(delays_her)[len(delays_her)//2], 1) if delays_her else 0,
    }

    streak_self, streak_her, max_self, max_her = 1, 1, 1, 1
    for i in range(1, len(msgs)):
        if msgs[i]["is_self"] == msgs[i-1]["is_self"]:
            if msgs[i]["is_self"]:
                streak_self += 1; max_self = max(max_self, streak_self)
            else:
                streak_her += 1; max_her = max(max_her, streak_her)
        else:
            streak_self = 1 if msgs[i]["is_self"] else streak_self
            streak_her = 1 if not msgs[i]["is_self"] else streak_her
    result["max_streak"] = {"self": max_self, "her": max_her}

    return result
