"""
模拟数据生成器 - 生成各种关系类型的 stats.json
用法：python generate_sample.py --type sweet|oneway|broken|cold|passionate
"""
import json
import random
import argparse

def gen_sweet():
    """甜蜜双向型：双方主动，Gottman比率高"""
    return {
        "type": "sweet",
        "type_name": "甜蜜双向型",
        "period": {"start": "2024-01-01", "end": "2024-12-31", "days": 365},
        "total_messages": 45600,
        "by_sender": {"self": 23400, "her": 22200},
        "self_ratio": 0.513,
        "her_ratio": 0.487,
        "her_initiate_rate": 0.52,
        "her_initiate_days": 190,
        "self_initiate_days": 175,
        "max_silence_days": 1,
        "reply_median_minutes": {"self": 12, "her": 15},
        "reply_p90_minutes": {"self": 45, "her": 60},
        "avg_msg_len": {"self": 15.2, "her": 14.8},
        "late_night_msgs": {"self": 2100, "her": 1980},
        "voice_msgs": {"self": 120, "her": 150},
        "emoji_count": {"self": 3200, "her": 3500},
        "gottman_ratio": {
            "overall": 6.2,
            "monthly": [5.8, 6.1, 6.5, 6.2, 5.9, 6.0, 6.3, 6.8, 6.5, 6.2, 6.0, 6.1],
            "months": ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
        },
        "four_horsemen": {
            "criticism": {"self": 8, "her": 7},
            "defensiveness": {"self": 5, "her": 6},
            "contempt": {"self": 2, "her": 3},
            "stonewalling": {"self": 3, "her": 2}
        },
        "love_triangle": {
            "intimacy": {"self": 2100, "her": 1980},
            "passion": {"self": 1500, "her": 1420},
            "commitment": {"self": 980, "her": 950}
        },
        "love_languages": {
            "affirmation": {"self": 280, "her": 260},
            "service": {"self": 350, "her": 320},
            "gifts": {"self": 85, "her": 92},
            "time": {"self": 2100, "her": 1980},
            "touch": {"self": 120, "her": 110}
        },
        "power": {
            "end_convo": {"self": 89, "her": 95},
            "compromise": {"self": 156, "her": 148},
            "questions": {"self": 890, "her": 850}
        },
        "emotion_sync": {"correlation": 0.68},
        "resilience": {
            "total_conflicts": 6,
            "repaired": 6,
            "avg_silence_hours": 8,
            "self_first_repair": 3,
            "her_first_repair": 3
        },
        "conflict_timeline": [
            {"start": "2024-03-15", "end": "2024-03-15", "silence_hours": 6, "first_repairer": "mutual"},
            {"start": "2024-07-22", "end": "2024-07-22", "silence_hours": 12, "first_repairer": "mutual"}
        ],
        "topics": {
            "家庭": {"self": 420, "her": 400},
            "朋友": {"self": 380, "her": 360},
            "工作": {"self": 560, "her": 520},
            "钱": {"self": 180, "her": 170},
            "感情": {"self": 680, "her": 650},
            "身体": {"self": 220, "her": 210},
            "娱乐": {"self": 520, "her": 500},
            "出行": {"self": 380, "her": 360}
        },
        "nicknames": {"self_uses": 320, "her_uses": 290},
        "care_count": {"self_to_her": 480, "her_to_self": 450},
        "top_words_self": ["宝宝","哈哈哈","爱你","想你","吃饭了吗","早点睡","好的"],
        "top_words_her": ["宝宝","哈哈哈","爱你","想你","好的","嗯嗯","好哒"]
    }

def gen_oneway():
    """单向投入型：你追TA跑"""
    return {
        "type": "oneway",
        "type_name": "单向投入型",
        "period": {"start": "2024-05-15", "end": "2025-02-20", "days": 280},
        "total_messages": 32900,
        "by_sender": {"self": 22300, "her": 10600},
        "self_ratio": 0.678,
        "her_ratio": 0.322,
        "her_initiate_rate": 0.286,
        "her_initiate_days": 80,
        "self_initiate_days": 200,
        "max_silence_days": 3,
        "reply_median_minutes": {"self": 8, "her": 72},
        "reply_p90_minutes": {"self": 30, "her": 420},
        "avg_msg_len": {"self": 18.5, "her": 6.2},
        "late_night_msgs": {"self": 3200, "her": 890},
        "voice_msgs": {"self": 45, "her": 23},
        "emoji_count": {"self": 1890, "her": 480},
        "gottman_ratio": {
            "overall": 2.1,
            "monthly": [3.2, 2.8, 2.1, 1.8, 1.5, 1.2, 1.8, 2.0, 2.3, 1.9, 2.1, 2.0],
            "months": ["5月","6月","7月","8月","9月","10月","11月","12月","1月","2月","3月","4月"]
        },
        "four_horsemen": {
            "criticism": {"self": 28, "her": 12},
            "defensiveness": {"self": 45, "her": 8},
            "contempt": {"self": 6, "her": 19},
            "stonewalling": {"self": 3, "her": 38}
        },
        "love_triangle": {
            "intimacy": {"self": 1200, "her": 680},
            "passion": {"self": 850, "her": 320},
            "commitment": {"self": 420, "her": 95}
        },
        "love_languages": {
            "affirmation": {"self": 89, "her": 23},
            "service": {"self": 214, "her": 76},
            "gifts": {"self": 12, "her": 3},
            "time": {"self": 3200, "her": 890},
            "touch": {"self": 45, "her": 8}
        },
        "power": {
            "end_convo": {"self": 67, "her": 156},
            "compromise": {"self": 189, "her": 45},
            "questions": {"self": 1240, "her": 320}
        },
        "emotion_sync": {"correlation": -0.32},
        "resilience": {
            "total_conflicts": 14,
            "repaired": 11,
            "avg_silence_hours": 42,
            "self_first_repair": 9,
            "her_first_repair": 2
        },
        "conflict_timeline": [
            {"start": "2024-07-12", "end": "2024-07-12", "silence_hours": 18, "first_repairer": "self"},
            {"start": "2024-09-03", "end": "2024-09-04", "silence_hours": 36, "first_repairer": "self"},
            {"start": "2024-11-18", "end": "2024-11-19", "silence_hours": 24, "first_repairer": "self"}
        ],
        "topics": {
            "家庭": {"self": 340, "her": 180},
            "朋友": {"self": 280, "her": 150},
            "工作": {"self": 560, "her": 320},
            "钱": {"self": 120, "her": 45},
            "感情": {"self": 890, "her": 230},
            "身体": {"self": 180, "her": 90},
            "娱乐": {"self": 420, "her": 280},
            "出行": {"self": 260, "her": 110}
        },
        "nicknames": {"self_uses": 45, "her_uses": 12},
        "care_count": {"self_to_her": 214, "her_to_self": 76},
        "top_words_self": ["宝宝","哈哈哈","嗯","好吧","想你","吃饭了吗","早点睡"],
        "top_words_her": ["嗯","哦","哈哈","好吧","行","忙","嗯呢"]
    }

def gen_broken():
    """分分合合型：断断续续，有大断联"""
    return {
        "type": "broken",
        "type_name": "分分合合型",
        "period": {"start": "2024-01-01", "end": "2024-12-31", "days": 365},
        "total_messages": 28500,
        "by_sender": {"self": 15800, "her": 12700},
        "self_ratio": 0.554,
        "her_ratio": 0.446,
        "her_initiate_rate": 0.38,
        "her_initiate_days": 110,
        "self_initiate_days": 180,
        "max_silence_days": 45,
        "reply_median_minutes": {"self": 25, "her": 95},
        "reply_p90_minutes": {"self": 120, "her": 1440},
        "avg_msg_len": {"self": 16.8, "her": 8.5},
        "late_night_msgs": {"self": 2800, "her": 1200},
        "voice_msgs": {"self": 89, "her": 45},
        "emoji_count": {"self": 2100, "her": 890},
        "gottman_ratio": {
            "overall": 2.8,
            "monthly": [4.5, 5.2, 3.8, 2.1, 0.5, 0.2, 1.8, 3.5, 4.2, 3.8, 2.9, 1.5],
            "months": ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
        },
        "four_horsemen": {
            "criticism": {"self": 45, "her": 38},
            "defensiveness": {"self": 32, "her": 28},
            "contempt": {"self": 18, "her": 22},
            "stonewalling": {"self": 25, "her": 42}
        },
        "love_triangle": {
            "intimacy": {"self": 1500, "her": 1100},
            "passion": {"self": 980, "her": 650},
            "commitment": {"self": 520, "her": 280}
        },
        "love_languages": {
            "affirmation": {"self": 120, "her": 68},
            "service": {"self": 180, "her": 120},
            "gifts": {"self": 45, "her": 38},
            "time": {"self": 2800, "her": 1800},
            "touch": {"self": 68, "her": 32}
        },
        "power": {
            "end_convo": {"self": 120, "her": 145},
            "compromise": {"self": 145, "her": 98},
            "questions": {"self": 890, "her": 560}
        },
        "emotion_sync": {"correlation": 0.25},
        "resilience": {
            "total_conflicts": 23,
            "repaired": 15,
            "avg_silence_hours": 72,
            "self_first_repair": 12,
            "her_first_repair": 5
        },
        "conflict_timeline": [
            {"start": "2024-05-20", "end": "2024-07-05", "silence_days": 45, "first_repairer": "mutual"},
            {"start": "2024-11-10", "end": "2024-11-25", "silence_days": 15, "first_repairer": "self"}
        ],
        "topics": {
            "家庭": {"self": 280, "her": 220},
            "朋友": {"self": 240, "her": 190},
            "工作": {"self": 420, "her": 350},
            "钱": {"self": 95, "her": 78},
            "感情": {"self": 780, "her": 520},
            "身体": {"self": 150, "her": 120},
            "娱乐": {"self": 350, "her": 280},
            "出行": {"self": 220, "her": 180}
        },
        "nicknames": {"self_uses": 180, "her_uses": 95},
        "care_count": {"self_to_her": 280, "her_to_self": 190},
        "top_words_self": ["为什么","算了","随便","好吧","想你","对不起","怎么办"],
        "top_words_her": ["嗯","哦","随便","累了","分手","算了","不知道"]
    }

def gen_cold():
    """冷战型：双方都不主动，Gottman低"""
    return {
        "type": "cold",
        "type_name": "冷战型",
        "period": {"start": "2024-03-01", "end": "2025-02-28", "days": 365},
        "total_messages": 15600,
        "by_sender": {"self": 8200, "her": 7400},
        "self_ratio": 0.526,
        "her_ratio": 0.474,
        "her_initiate_rate": 0.22,
        "her_initiate_days": 80,
        "self_initiate_days": 95,
        "max_silence_days": 12,
        "reply_median_minutes": {"self": 120, "her": 150},
        "reply_p90_minutes": {"self": 1440, "her": 1800},
        "avg_msg_len": {"self": 4.5, "her": 3.8},
        "late_night_msgs": {"self": 450, "her": 380},
        "voice_msgs": {"self": 8, "her": 5},
        "emoji_count": {"self": 120, "her": 95},
        "gottman_ratio": {
            "overall": 1.2,
            "monthly": [1.8, 1.5, 1.2, 1.0, 0.8, 0.9, 1.1, 1.3, 1.0, 0.9, 1.1, 1.2],
            "months": ["3月","4月","5月","6月","7月","8月","9月","10月","11月","12月","1月","2月"]
        },
        "four_horsemen": {
            "criticism": {"self": 15, "her": 12},
            "defensiveness": {"self": 28, "her": 32},
            "contempt": {"self": 25, "her": 28},
            "stonewalling": {"self": 45, "her": 52}
        },
        "love_triangle": {
            "intimacy": {"self": 320, "her": 280},
            "passion": {"self": 180, "her": 150},
            "commitment": {"self": 120, "her": 95}
        },
        "love_languages": {
            "affirmation": {"self": 12, "her": 8},
            "service": {"self": 45, "her": 38},
            "gifts": {"self": 5, "her": 3},
            "time": {"self": 450, "her": 380},
            "touch": {"self": 5, "her": 3}
        },
        "power": {
            "end_convo": {"self": 180, "her": 195},
            "compromise": {"self": 45, "her": 38},
            "questions": {"self": 180, "her": 150}
        },
        "emotion_sync": {"correlation": 0.12},
        "resilience": {
            "total_conflicts": 18,
            "repaired": 8,
            "avg_silence_hours": 168,
            "self_first_repair": 5,
            "her_first_repair": 3
        },
        "conflict_timeline": [
            {"start": "2024-06-15", "end": "2024-06-22", "silence_days": 7, "first_repairer": "self"},
            {"start": "2024-10-08", "end": "2024-10-20", "silence_days": 12, "first_repairer": "none"}
        ],
        "topics": {
            "家庭": {"self": 85, "her": 72},
            "朋友": {"self": 65, "her": 58},
            "工作": {"self": 180, "her": 165},
            "钱": {"self": 32, "her": 28},
            "感情": {"self": 120, "her": 95},
            "身体": {"self": 45, "her": 38},
            "娱乐": {"self": 95, "her": 82},
            "出行": {"self": 52, "her": 45}
        },
        "nicknames": {"self_uses": 8, "her_uses": 5},
        "care_count": {"self_to_her": 45, "her_to_self": 38},
        "top_words_self": ["嗯","哦","好吧","随便","忙","行","哦"],
        "top_words_her": ["嗯","哦","好吧","随便","忙","行","嗯"]
    }

TYPES = {
    "sweet": gen_sweet,
    "oneway": gen_oneway,
    "broken": gen_broken,
    "cold": gen_cold
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=TYPES.keys(), required=True)
    parser.add_argument("--output", default="sample_stats.json")
    args = parser.parse_args()
    
    data = TYPES[args.type]()
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Generated {args.type} -> {args.output}")
    print(f"Total messages: {data['total_messages']}")
    print(f"Type: {data['type_name']}")
