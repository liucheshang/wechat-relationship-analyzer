# -*- coding: utf-8 -*-
"""
make_icon.py —— 生成 app.ico（纯标准库，不依赖 Pillow）。

图标设计：圆角深色底 + 两根对话条（蓝/粉，代表「我 / TA」）+ 右侧攀升的数据条。
4x4 超采样做抗锯齿，输出 16/32/48/64/128/256 六个尺寸，打包进 exe。

用法：
    python make_icon.py [输出路径.ico]
"""

import os
import struct
import sys

# 与报告同一个配色，保持整体一致
BG_TOP = (0x18, 0x22, 0x2E)     # 圆角底 · 上
BG_BOT = (0x0E, 0x13, 0x18)     # 圆角底 · 下
BLUE = (0x5B, 0x8D, 0xEF)       # 我
PINK = (0xF0, 0x62, 0x92)       # TA
GREEN = (0x07, 0xC1, 0x60)      # 数据条
WHITE = (0xE9, 0xEE, 0xF4)

SIZES = (16, 32, 48, 64, 128, 256)
SS = 4                          # 每个像素 4x4 子采样


def _rrect(x, y, x0, y0, x1, y1, r):
    """点 (x,y) 是否落在圆角矩形内。"""
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    dx, dy = x - cx, y - cy
    return dx * dx + dy * dy <= r * r


def _rrect_soft(x, y, x0, y0, x1, y1, r, feather):
    """带羽化的圆角矩形覆盖度（0~1），让边缘更柔和。"""
    if _rrect(x, y, x0, y0, x1, y1, r):
        return 1.0
    # 往外扩一圈再判，用作羽化过渡
    if _rrect(x, y, x0 - feather, y0 - feather, x1 + feather, y1 + feather, r + feather):
        return 0.45
    return 0.0


def _mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def render(S):
    """渲染一张 S x S 的 RGBA 图，返回 bytes（逐像素 RGBA）。"""
    px = bytearray(S * S * 4)
    # 各元素的归一化几何（用 0~1 表示，方便按尺寸缩放）
    pad = 0.04
    rad = 0.22
    # 对话条：左上两条圆角横条
    bar1 = (0.20, 0.24, 0.66, 0.38)      # 蓝
    bar2 = (0.20, 0.44, 0.52, 0.58)      # 粉
    # 数据条：右下三根
    bars = [(0.62, 0.68, 0.71, 0.82),
            (0.74, 0.55, 0.83, 0.82),
            (0.86, 0.44, 0.95, 0.82)]

    for py in range(S):
        for pxi in range(S):
            r = g = b = 0
            a = 0
            for sy in range(SS):
                for sx in range(SS):
                    x = (pxi + (sx + 0.5) / SS) / S
                    y = (py + (sy + 0.5) / SS) / S
                    cov = _rrect_soft(x, y, pad, pad, 1 - pad, 1 - pad, rad, 0.02)
                    if cov <= 0:
                        continue
                    # 底色：竖向渐变
                    col = _mix(BG_TOP, BG_BOT, min(1.0, max(0.0, (y - pad) / (1 - 2 * pad))))
                    # 对话条
                    if _rrect(x, y, bar1[0], bar1[1], bar1[2], bar1[3], 0.07):
                        col = BLUE
                    elif _rrect(x, y, bar2[0], bar2[1], bar2[2], bar2[3], 0.07):
                        col = PINK
                    else:
                        for (bx0, by0, bx1, by1) in bars:
                            if _rrect(x, y, bx0, by0, bx1, by1, 0.035):
                                col = GREEN
                                break
                    r += col[0] * cov
                    g += col[1] * cov
                    b += col[2] * cov
                    a += cov
            n = SS * SS
            o = (py * S + pxi) * 4
            if a <= 0.0001:
                px[o:o + 4] = b'\x00\x00\x00\x00'
            else:
                # 颜色按覆盖度归一化，alpha 为平均覆盖度
                px[o] = min(255, int(r / a))
                px[o + 1] = min(255, int(g / a))
                px[o + 2] = min(255, int(b / a))
                px[o + 3] = min(255, int(255 * a / n))
    return bytes(px)


def bmp_entry(S, rgba):
    """把 RGBA 数据包成 ICO 里的 BMP（BITMAPINFOHEADER + BGRA 倒序 + AND 掩码）。"""
    hdr = struct.pack('<IiiHHIIiiII', 40, S, S * 2, 1, 32, 0, S * S * 4, 0, 0, 0, 0)
    body = bytearray()
    for y in range(S - 1, -1, -1):
        row = rgba[y * S * 4:(y + 1) * S * 4]
        for x in range(S):
            o = x * 4
            body += bytes((row[o + 2], row[o + 1], row[o], row[o + 3]))  # BGRA
    mask_row = ((S + 31) // 32) * 4
    body += b'\x00' * (mask_row * S)
    return hdr + bytes(body)


def build(path):
    imgs = [(S, bmp_entry(S, render(S))) for S in SIZES]
    out = bytearray(struct.pack('<HHH', 0, 1, len(imgs)))
    offset = 6 + 16 * len(imgs)
    for S, data in imgs:
        dim = 0 if S >= 256 else S
        out += struct.pack('<BBBBHHII', dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    for _, data in imgs:
        out += data
    with open(path, 'wb') as f:
        f.write(out)
    return path, len(out)


if __name__ == '__main__':
    dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'app.ico')
    p, n = build(dst)
    print('已生成 %s（%d 字节，含 %s 尺寸）' % (p, n, '/'.join(str(s) for s in SIZES)))
