# -*- coding: utf-8 -*-
"""
微信聊天记录关系分析器 · 基础版一键启动
双击运行后会自动打开浏览器，拖入聊天记录文件即可出报告。
"""
import os
import sys
import json
import tempfile
import threading
import webbrowser
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).parent.resolve()


def analyze(uploaded_file):
    if uploaded_file is None:
        return "请先上传聊天记录文件（CSV 或 JSON）。"

    input_path = Path(uploaded_file)
    workdir = Path(tempfile.mkdtemp(prefix="wxra_"))
    messages_json = workdir / "messages.json"

    # 格式转换
    try:
        sys.path.insert(0, str(ROOT))
        from convert_input import convert
        convert(str(input_path), str(messages_json))
    except Exception as e:
        return f"格式转换失败：{e}\n\n请确认文件是微信导出的 CSV/JSON 格式。"

    # 规则分析
    try:
        from analyzer.rules import analyze_messages
        with open(messages_json, encoding="utf-8") as f:
            msgs = json.load(f)
        stats = analyze_messages(msgs)
    except Exception as e:
        import traceback
        return f"分析失败：{e}\n\n{traceback.format_exc()}"

    lines = []
    lines.append("=" * 50)
    lines.append("  你们的关系体检报告（基础版）")
    lines.append("=" * 50)
    lines.append("")

    overview = stats.get("overview", {})
    lines.append(f"总消息数：{overview.get('total_msgs', '?')}")
    lines.append(f"时间跨度：{overview.get('days', '?')} 天")
    lines.append(f"双方有效消息：{overview.get('valid_msgs', '?')} 条")
    lines.append("")

    initiator = stats.get("initiator", {})
    lines.append("── 谁更主动？")
    lines.append(f"  TA 主动开场：{initiator.get('her_ratio', 0)*100:.1f}%")
    lines.append(f"  你主动开场：{initiator.get('your_ratio', 0)*100:.1f}%")
    lines.append("")

    gottman = stats.get("gottman", {})
    lines.append("── Gottman 比率（积极÷消极）")
    lines.append(f"  总体：{gottman.get('overall', 0):.2f}（健康 > 5.0）")
    lines.append(f"  最近3个月：{gottman.get('recent', 0):.2f}")
    lines.append("")

    reply = stats.get("reply_speed", {})
    lines.append("── 回复速度（中位数）")
    lines.append(f"  TA：{reply.get('her_median', 0):.0f} 分钟")
    lines.append(f"  你：{reply.get('your_median', 0):.0f} 分钟")
    lines.append("")

    care = stats.get("care", {})
    lines.append("── 关心次数")
    lines.append(f"  TA 关心你：{care.get('her_cares', 0)} 次")
    lines.append(f"  你关心 TA：{care.get('your_cares', 0)} 次")
    lines.append("")

    horsemen = stats.get("four_horsemen", {})
    lines.append("── 四骑士")
    for k in ["criticism", "defensiveness", "contempt", "stonewalling"]:
        h = horsemen.get(k, {})
        lines.append(f"  {k}: TA {h.get('her', 0)} 次 / 你 {h.get('your', 0)} 次")
    lines.append("")

    silence = stats.get("silence", {})
    lines.append("── 断联检测")
    lines.append(f"  最长沉默：{silence.get('max_days', 0)} 天")
    lines.append(f"  断联次数：{silence.get('silent_periods', 0)} 次")
    lines.append("")

    nicknames = stats.get("nicknames", {})
    lines.append("── 称呼变化")
    for k, v in nicknames.items():
        lines.append(f"  {k}: {v}")
    lines.append("")

    lines.append("=" * 50)
    lines.append("  想要更详细报告？升级到详细版/终极版")
    lines.append("  详见 README.md")
    lines.append("=" * 50)

    return "\n".join(lines)


def main():
    with gr.Blocks(title="微信关系分析器", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 💬 微信关系分析器\n上传你导出的聊天记录文件，几秒钟出结果。")
        file_input = gr.File(label="上传聊天记录（CSV / JSON）", file_types=[".csv", ".json", ".jsonl"])
        btn = gr.Button("开始分析", variant="primary")
        output = gr.Textbox(label="分析结果", lines=25)
        btn.click(fn=analyze, inputs=file_input, outputs=output)

    port = 7860
    threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    demo.launch(server_name="127.0.0.1", server_port=port, share=False, inbrowser=False)


if __name__ == "__main__":
    main()
