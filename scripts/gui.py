# -*- coding: utf-8 -*-
"""
gui.py —— 聊天记录深度分析器 · 图形界面版

纯标准库（tkinter），零第三方依赖。功能：
  · 窗口常驻，一次拖入多个文件批量分析，不退出
  · 支持 .txt（标准格式）/ .csv / .json（其他工具导出，自动转换）
  · 实时日志 + 进度条，完成后一键打开报告 / 打开所在文件夹
  · 支持把文件拖进窗口（Windows 外壳拖放），也可直接把文件拖到 exe 图标上

打包：
    pyinstaller --onefile --windowed --icon app.ico \
        --add-data report_template.html;. --add-data echarts.min.js;. --add-data app.ico;. \
        gui.py
"""

import os
import re
import sys
import time
import queue
import threading
import traceback
import tempfile

import tkinter as tk
from tkinter import filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze          # noqa: E402
import convert          # noqa: E402

# ---------------------------------------------------------------- 主题（与报告同一套配色）
BG      = '#0e1318'
PANEL   = '#151d26'
PANEL2  = '#1b242e'
HOVER   = '#243040'
TEXT    = '#e9eef4'
MUTED   = '#8fa1b4'
DIM     = '#5f7285'
BLUE    = '#5b8def'
GREEN   = '#07c160'
GREEN_D = '#059a4c'
GOLD    = '#ffb648'
RED     = '#ff5c5c'

FONT = 'Microsoft YaHei UI'
FILETYPES = [('聊天记录 / 数据文件', '*.txt *.csv *.json *.log'), ('所有文件', '*.*')]
TXT_EXT = ('.txt', '.log')
LINE_RE = re.compile(r'^\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}).{0,60}?\|\s*[^|]+\|\s*\S')

_DND_STATE = {'cb': None, 'olds': {}, 'on_files': None}   # 拖放回调必须保活，否则被 GC 后窗口消息就崩了
WM_DROPFILES = 0x0233


def _dnd_proc(h, msg, wp, lp):
    """共享的窗口过程：任何被 hook 的窗口收到拖放都走这里。"""
    if msg == WM_DROPFILES:
        try:
            import ctypes
            shell32 = ctypes.windll.shell32
            n = shell32.DragQueryFileW(wp, 0xFFFFFFFF, None, 0)
            files = []
            buf = ctypes.create_unicode_buffer(2048)
            for i in range(n):
                shell32.DragQueryFileW(wp, i, buf, 2048)
                files.append(buf.value)
            shell32.DragFinish(wp)
            if _DND_STATE['on_files'] and files:
                _DND_STATE['on_files'](files)
        except Exception:
            pass
        return 0
    old = _DND_STATE['olds'].get(h)
    if old:
        import ctypes
        return ctypes.windll.user32.CallWindowProcW(old, h, msg, wp, lp)
    import ctypes
    return ctypes.windll.user32.DefWindowProcW(h, msg, wp, lp)


def enable_dnd_tree(root, on_files):
    """对顶层窗口 + 所有子控件开启外壳拖放。

    之前只 hook 顶层窗口：拖到按钮 / 文件列表等子控件上时消息发不到，表现
    就是「拖拽不正常，有时有反应有时没有」。现在递归 hook 全部子窗口；
    另外用 ChangeWindowMessageFilterEx 放行 WM_DROPFILES，exe 以管理员
    运行时（UIPI 拦截拖放）也能正常接收。失败则静默降级为「仅点击选择」。"""
    if sys.platform != 'win32':
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32

        proto = getattr(enable_dnd_tree, '_proto', None)
        if proto is None:
            proto = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, ctypes.c_uint,
                                       ctypes.c_size_t, ctypes.c_ssize_t)
            enable_dnd_tree._proto = proto      # 必须保活，局部变量会连同回调一起被 GC
        cb = proto(_dnd_proc)
        _DND_STATE['cb'] = cb
        _DND_STATE['on_files'] = on_files

        try:
            set_long = user32.SetWindowLongPtrW
        except AttributeError:
            set_long = user32.SetWindowLongW
        set_long.restype = ctypes.c_ssize_t
        set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]

        def hook(hwnd):
            if not hwnd:
                return
            shell32.DragAcceptFiles(wintypes.HWND(hwnd), True)
            try:                                # 管理员进程也能接收普通进程拖来的文件
                user32.ChangeWindowMessageFilterEx(wintypes.HWND(hwnd), WM_DROPFILES, 1, None)
            except Exception:
                pass
            if hwnd not in _DND_STATE['olds']:
                old = set_long(wintypes.HWND(hwnd), -4, cb)   # GWLP_WNDPROC
                _DND_STATE['olds'][hwnd] = old

        def walk(w):
            try:
                hook(w.winfo_id())
            except Exception:
                pass
            for ch in w.winfo_children():
                walk(ch)

        hook(user32.GetParent(root.winfo_id()))   # 真正的顶层窗口框
        walk(root)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- 小工具
def res_dir():
    """资源目录：打包后在 _MEIPASS，源码运行时在本文件目录。"""
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def ensure_dpi_awareness():
    """必须在创建 Tk 窗口【之前】调用。

    不声明 DPI 感知时，Windows 会把整个窗口按位图拉伸：字体模糊、显小、
    界面发虚——这是「字体太小、不够美观」的最大单一原因。"""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)   # per-monitor v1
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ---------------------------------------------------------------- 控件
class HoverButton(tk.Label):
    """用 Label 实现的按钮：配色和悬停效果完全可控。"""

    def __init__(self, master, text, cmd, bg=PANEL2, fg=TEXT, hover=HOVER,
                 font=None, padx=16, pady=8, **kw):
        super().__init__(master, text=text, bg=bg, fg=fg, font=font or (FONT, 11),
                         padx=padx, pady=pady, cursor='hand2', **kw)
        self._bg, self._hover, self._fg = bg, hover, fg
        self._cmd = cmd
        self.bind('<Enter>', self._enter)
        self.bind('<Leave>', self._leave)
        self.bind('<Button-1>', self._click)

    def _enter(self, e):
        if self._cmd:
            self.configure(bg=self._hover)

    def _leave(self, e):
        if self._cmd:
            self.configure(bg=self._bg)

    def _click(self, e):
        if self._cmd:
            self._cmd()

    def set_enabled(self, on):
        if on:
            if self._cmd is None and getattr(self, '_origin', None):
                self._cmd = self._origin
                self.configure(bg=self._bg, fg=self._fg, cursor='hand2')
        else:
            if self._cmd is not None:
                self._origin = self._cmd
                self._cmd = None
                self.configure(bg=PANEL, fg=DIM, cursor='arrow')


class ScrollBox(tk.Frame):
    """深色滚动容器（滚轮翻页）。"""

    def __init__(self, master, height=140, bg=PANEL):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, height=height)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')
        self.inner.bind('<Configure>', lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(
            self.win, width=e.width))
        self.canvas.pack(side='left', fill='both', expand=True)
        for seq in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            self.canvas.bind_all(seq, self._wheel)

    def _wheel(self, e):
        # 只在鼠标位于文件列表上方时滚动，别的控件（如日志）保持原生滚动
        w = self.winfo_containing(e.x_root, e.y_root)
        while w is not None and w is not self.canvas:
            w = getattr(w, 'master', None)
        if w is not self.canvas:
            return
        step = -1 if (getattr(e, 'delta', 0) > 0 or getattr(e, 'num', 0) == 4) else 1
        self.canvas.yview_scroll(step, 'units')


class Bar(tk.Canvas):
    """细进度条。"""

    def __init__(self, master, height=7):
        super().__init__(master, bg=BG, highlightthickness=0, height=height)
        self._h = height
        self._p = 0.0
        self.bind('<Configure>', lambda e: self._draw())
        self._draw()

    def set(self, p):
        self._p = max(0.0, min(1.0, p))
        self._draw()

    def _rr(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.create_polygon(pts, smooth=True, **kw)

    def _draw(self):
        self.delete('all')
        w = self.winfo_width()
        if w < 10:
            return
        self._rr(1, 1, w - 1, self._h, self._h / 2, fill=PANEL2, outline='')
        if self._p > 0.001:
            x1 = max(1 + self._h, 1 + (w - 2) * self._p)
            self._rr(1, 1, x1, self._h, self._h / 2, fill=GREEN, outline='')


# ---------------------------------------------------------------- 主窗口
class App(tk.Tk):

    def __init__(self, argv_files=None):
        super().__init__()
        self.title('聊天记录深度分析器')
        self.configure(bg=BG)
        self.minsize(760, 640)

        ico = os.path.join(res_dir(), 'app.ico')
        if os.path.isfile(ico):
            try:
                self.iconbitmap(ico)
            except Exception:
                pass

        self.q = queue.Queue()
        self.items = []
        self.running = False
        self.stop_flag = False
        self.outdir = None
        self.last_report = None
        self.auto_open = True

        try:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        except Exception:
            sw, sh = 1440, 900
        w, h = 960, min(860, sh - 60)
        self.geometry('%dx%d+%d+%d' % (w, h, max(0, (sw - w) // 2),
                                       max(0, (sh - h) // 2 - 10)))

        self._build()
        self.after(60, self._poll)
        self._setup_dnd()
        for f in (argv_files or []):
            self.add_files([f])

    # ---------------- 布局 ----------------
    def _build(self):
        pad = {'padx': 26}

        head = tk.Frame(self, bg=BG)
        head.pack(fill='x', pady=(18, 2), **pad)
        tk.Label(head, text='聊天记录深度分析器', bg=BG, fg=TEXT,
                 font=(FONT, 20, 'bold')).pack(anchor='w')
        sub = tk.Frame(head, bg=BG)
        sub.pack(fill='x', pady=(2, 0))
        tk.Label(sub, text='纯本地统计 · 不联网 · 不上传任何数据 · 报告可直接分享',
                 bg=BG, fg=MUTED, font=(FONT, 10)).pack(side='left')
        tk.Label(sub, text='v2.1 GUI', bg=PANEL, fg=GOLD, font=(FONT, 10, 'bold'),
                 padx=7, pady=2).pack(side='right')

        # ---- 拖放区 ----
        self.zone = tk.Canvas(self, bg=PANEL, highlightthickness=0, height=110,
                              cursor='hand2')
        self.zone.pack(fill='x', pady=(14, 0), **pad)
        self.zone.bind('<Button-1>', lambda e: self.pick_files())
        self.zone.bind('<Configure>', lambda e: self._draw_zone(False))
        self.zone.bind('<Enter>', lambda e: self._draw_zone(True))
        self.zone.bind('<Leave>', lambda e: self._draw_zone(False))

        # ---- 文件列表 ----
        lf = tk.Frame(self, bg=BG)
        lf.pack(fill='x', pady=(14, 4), **pad)
        tk.Label(lf, text='待分析', bg=BG, fg=MUTED,
                 font=(FONT, 10, 'bold')).pack(side='left')
        self.count_lbl = tk.Label(lf, text='', bg=BG, fg=DIM, font=(FONT, 10))
        self.count_lbl.pack(side='left', padx=8)
        HoverButton(lf, '清空列表', self.clear_all, bg=BG, fg=DIM, hover=BG,
                    font=(FONT, 10), pady=2).pack(side='right')

        self.box = ScrollBox(self, height=120, bg=PANEL)
        self.box.pack(fill='both', padx=26, expand=False)
        self.empty_hint = tk.Label(self.box.inner,
                                   text='   还没有文件 —— 把聊天记录拖到上面，或点上面选择',
                                   bg=PANEL, fg=DIM, font=(FONT, 10), pady=14)
        self.empty_hint.pack(fill='x')

        # ---- 输出目录 / 选项 ----
        of = tk.Frame(self, bg=BG)
        of.pack(fill='x', pady=(10, 0), **pad)
        tk.Label(of, text='输出到', bg=BG, fg=DIM,
                 font=(FONT, 10)).pack(side='left')
        self.out_lbl = tk.Label(of, text='与聊天记录相同的文件夹', bg=BG, fg=MUTED,
                                font=(FONT, 10))
        self.out_lbl.pack(side='left', padx=8)
        HoverButton(of, '更改', self.pick_outdir, bg=BG, fg=BLUE, hover=BG,
                    font=(FONT, 10), pady=2).pack(side='right')
        self.auto_lbl = None
        self.btn_auto = HoverButton(of, '完成后自动打开报告：开', self.toggle_auto,
                                    bg=BG, fg=MUTED, hover=BG, font=(FONT, 10), pady=2)
        self.btn_auto.pack(side='right', padx=(0, 16))

        # ---- 进度 ----
        pf = tk.Frame(self, bg=BG)
        pf.pack(fill='x', pady=(12, 0), **pad)
        self.bar = Bar(pf)
        self.bar.pack(fill='x')
        self.status_lbl = tk.Label(pf, text='把聊天记录拖进来就能开始', anchor='w',
                                   bg=BG, fg=MUTED, font=(FONT, 10))
        self.status_lbl.pack(fill='x', pady=(6, 0))

        # ---- 日志 ----
        self.log_box = tk.Text(self, bg=PANEL, fg=MUTED, relief='flat', height=8,
                               font=('Consolas', 10), state='disabled', wrap='word',
                               padx=12, pady=9, selectbackground=HOVER,
                               selectforeground=TEXT)
        self.log_box.pack(fill='both', expand=True, pady=(10, 0), **pad)
        for tag, col in (('err', RED), ('ok', GREEN), ('warn', GOLD), ('hi', BLUE)):
            self.log_box.tag_configure(tag, foreground=col)
        self.log_box.tag_configure('dim', foreground=DIM)

        # ---- 按钮行 ----
        bf = tk.Frame(self, bg=BG)
        bf.pack(fill='x', pady=(14, 4), **pad)
        self.btn_run = HoverButton(bf, '开 始 分 析', self.run, bg=GREEN, fg='#04240f',
                                   hover=GREEN_D, font=(FONT, 12, 'bold'),
                                   padx=30, pady=10)
        self.btn_run.pack(side='left')
        self.btn_report = HoverButton(bf, '打开报告', self.open_report, padx=18)
        self.btn_report.pack(side='left', padx=(14, 0))
        self.btn_folder = HoverButton(bf, '打开文件夹', self.open_folder, padx=18)
        self.btn_folder.pack(side='left', padx=(10, 0))
        self.btn_report.set_enabled(False)
        self.btn_folder.set_enabled(False)

        tk.Label(self, text='分析在本机完成 · 生成的 HTML 报告用浏览器打开，断网也能看图',
                 bg=BG, fg=DIM, font=(FONT, 9)).pack(side='bottom', pady=(0, 8))

        self.bind('<Control-o>', lambda e: self.pick_files())

    # ---------------- 拖放区 ----------------
    def _draw_zone(self, hot):
        c = self.zone
        c.delete('all')
        w = c.winfo_width()
        h = int(float(c['height']))
        if w < 10:
            w = 800
        c.create_rectangle(2, 2, w - 3, h - 3, outline=BLUE if hot else DIM,
                           dash=(5, 4), fill=PANEL if hot else PANEL2)
        c.create_text(w / 2, h / 2 - 10, text='＋  把聊天记录拖到这里，或点击选择文件',
                      fill=TEXT if hot else MUTED, font=(FONT, 13, 'bold'))
        c.create_text(w / 2, h / 2 + 16,
                      text='支持 .txt 标准格式；.csv / .json 自动识别转换 · 可一次选多个',
                      fill=DIM, font=(FONT, 10))

    def _setup_dnd(self):
        try:
            ok = enable_dnd_tree(self, self._on_drop)
            self.log('拖放已启用：窗口任意位置都能拖进来' if ok
                     else '（拖放不可用，用点击选择也一样）', 'dim')
        except Exception:
            self.log('（拖放不可用，用点击选择也一样）', 'dim')

    def _on_drop(self, files):
        self.add_files(files)

    # ---------------- 文件列表 ----------------
    def _card(self, path):
        f = tk.Frame(self.box.inner, bg=PANEL2)
        f.pack(fill='x', padx=8, pady=4)
        left = tk.Frame(f, bg=PANEL2)
        left.pack(side='left', fill='x', expand=True)
        name = tk.Label(left, text=os.path.basename(path), bg=PANEL2, fg=TEXT,
                        font=(FONT, 11), anchor='w')
        name.pack(fill='x', padx=12, pady=(6, 0))
        meta = tk.Label(left, text='正在读取…', bg=PANEL2, fg=DIM, font=(FONT, 9),
                        anchor='w')
        meta.pack(fill='x', padx=12, pady=(0, 6))
        st = tk.Label(f, text='待分析', bg=PANEL2, fg=MUTED, font=(FONT, 10))
        st.pack(side='left', padx=12)
        x = HoverButton(f, '✕', lambda: self.remove(path), bg=PANEL2, fg=DIM,
                        hover=PANEL2, font=(FONT, 10), pady=2)
        x.pack(side='right', padx=12)
        return {'path': path, 'frame': f, 'name': name, 'meta': meta,
                'status': st, 'report': None}

    def add_files(self, paths):
        added = 0
        for p in paths:
            p = os.path.abspath(p.strip().strip('"'))
            if not os.path.isfile(p):
                self.log('跳过（不是文件）：%s' % p, 'warn')
                continue
            if any(it['path'] == p for it in self.items):
                continue
            if not p.lower().endswith(TXT_EXT + ('.csv', '.json')):
                self.log('跳过（只认 .txt / .csv / .json）：%s' % os.path.basename(p), 'warn')
                continue
            self.items.append(self._card(p))
            added += 1
            threading.Thread(target=self._peek, args=(p,), daemon=True).start()
        if added:
            self.empty_hint.pack_forget()
            self._refresh_count()
            self.log('已添加 %d 个文件' % added, 'dim')

    def _peek(self, path):
        """后台读一遍文件头尾，给卡片补上「条数 · 时间范围」。"""
        info = None
        try:
            if not path.lower().endswith(TXT_EXT):
                info = '%.1f MB · 将自动转换为标准格式' % (os.path.getsize(path) / 1048576)
            else:
                n = first = last = 0
                cnt, lo, hi = 0, None, None
                f = None
                for enc in ('utf-8-sig', 'utf-8', 'gbk'):
                    try:
                        f = open(path, 'r', encoding=enc)
                        break
                    except UnicodeDecodeError:
                        continue
                if f:
                    with f:
                        for line in f:
                            m = LINE_RE.match(line)
                            if m:
                                cnt += 1
                                d = m.group(1).replace('/', '-')
                                if lo is None:
                                    lo = d
                                hi = d
                if cnt:
                    info = '{:,} 条 · {} ~ {}'.format(cnt, lo, hi)
                else:
                    info = '⚠ 没认出标准格式，将尝试按 CSV/JSON 转换'
        except Exception:
            info = ''
        self.q.put(('meta', path, info))

    def remove(self, path):
        if self.running:
            return
        for it in list(self.items):
            if it['path'] == path:
                it['frame'].destroy()
                self.items.remove(it)
        if not self.items:
            self.empty_hint.pack(fill='x')
        self._refresh_count()

    def clear_all(self):
        if self.running:
            return
        for it in self.items:
            it['frame'].destroy()
        self.items = []
        self.empty_hint.pack(fill='x')
        self._refresh_count()

    def _refresh_count(self):
        n = len(self.items)
        self.count_lbl.configure(text='%d 个文件' % n if n else '')
        self.bar.set(0)

    def pick_files(self):
        if self.running:
            return
        fs = filedialog.askopenfilenames(title='选择聊天记录（可多选）',
                                         filetypes=FILETYPES)
        if fs:
            self.add_files(list(fs))

    def pick_outdir(self):
        d = filedialog.askdirectory(title='选择报告输出目录')
        if d:
            self.outdir = d
            self.out_lbl.configure(text=d)

    def toggle_auto(self):
        self.auto_open = not self.auto_open
        self.btn_auto.configure(
            text='完成后自动打开报告：%s' % ('开' if self.auto_open else '关'),
            fg=MUTED if self.auto_open else DIM)

    # ---------------- 日志 / 队列 ----------------
    def log(self, text, tag=''):
        self.log_box.configure(state='normal')
        self.log_box.insert('end', text + '\n', tag or 'dim')
        if int(self.log_box.index('end-1c').split('.')[0]) > 3000:
            self.log_box.delete('1.0', '1000.0')
        self.log_box.configure(state='disabled')
        self.log_box.see('end')

    def _poll(self):
        try:
            while True:
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == 'line':
                    _, line = msg
                    t = ('err' if ('错误' in line or 'Error' in line or 'Traceback' in line)
                         else 'ok' if ('报告已生成' in line or '✓' in line or '完成' in line)
                         else 'warn' if '警告' in line else '')
                    self.log(line, t)
                    if '读取: ' in line:
                        self._step(1)
                    elif '清洗: ' in line:
                        self._step(2)
                    elif '会话段: ' in line:
                        self._step(3)
                    elif '冲突段: ' in line:
                        self._step(4)
                elif kind == 'meta':
                    _, path, info = msg
                    for it in self.items:
                        if it['path'] == path:
                            it['meta'].configure(text=info)
                elif kind == 'status':
                    _, text, tag = msg
                    self.status_lbl.configure(text=text,
                                              fg={'err': RED, 'ok': GREEN}.get(tag, MUTED))
                elif kind == 'card':
                    _, path, text, col = msg
                    for it in self.items:
                        if it['path'] == path:
                            it['status'].configure(text=text, fg=col)
                elif kind == 'done':
                    self.running = False
                    self._set_buttons(True)
                    self.bar.set(1.0)
                    self.status_lbl.configure(text='全部完成', fg=GREEN)
                elif kind == 'report':
                    self.last_report = msg[1]
                    self.btn_report.set_enabled(True)
                    self.btn_folder.set_enabled(True)
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _step(self, k):
        """单文件分析走到第 k 步（共 5 步），刷新进度条。"""
        done = self._done_count
        total = max(1, self._total_count)
        self.bar.set((done + k / 5.0) / total)

    # ---------------- 分析 ----------------
    def run(self):
        if self.running:
            self.stop_flag = True
            self.status_lbl.configure(text='将在当前文件结束后停止…', fg=GOLD)
            return
        if not self.items:
            messagebox.showinfo('提示', '先把聊天记录拖进来（或点上面选择文件）')
            return
        self.running = True
        self.stop_flag = False
        self._set_buttons(False)
        threading.Thread(target=self._worker, daemon=True).start()

    def _set_buttons(self, idle):
        self.btn_run.configure(text='停 止' if not idle else '开 始 分 析')
        on = self.last_report is not None
        self.btn_report.set_enabled(on)
        self.btn_folder.set_enabled(on)

    def _out_path(self, src):
        stem = os.path.splitext(os.path.basename(src))[0]
        name = '%s_深度分析报告.html' % stem
        if self.outdir:
            return os.path.join(self.outdir, name)
        return os.path.join(os.path.dirname(src), name)

    def _worker(self):
        old_out, old_err = sys.stdout, sys.stderr

        class W:
            def __init__(s, q):
                s.q, s.buf = q, ''

            def write(s, t):
                s.buf += t
                while '\n' in s.buf:
                    line, s.buf = s.buf.split('\n', 1)
                    if line.strip():
                        s.q.put(('line', line.rstrip()))

            def flush(s):
                pass

        sys.stdout = sys.stderr = W(self.q)
        analyze._pause = lambda: None           # GUI 模式不需要「按回车退出」

        self._total_count = len(self.items)
        self._done_count = 0
        reports = []
        try:
            for it in list(self.items):
                if self.stop_flag:
                    self.q.put(('status', '已停止', ''))
                    break
                path = it['path']
                self.q.put(('card', path, '分析中…', BLUE))
                self.q.put(('status', '正在分析：%s' % os.path.basename(path), ''))
                out = self._out_path(path)
                try:
                    real = self._prepare(path)
                    old_argv = sys.argv
                    sys.argv = ['analyzer', real, out]
                    try:
                        analyze.main()
                    finally:
                        sys.argv = old_argv
                    if os.path.isfile(out):
                        reports.append(out)
                        self.q.put(('report', out))
                        self.q.put(('card', path, '✓ 已完成', GREEN))
                        it['report'] = out
                        if self.auto_open:
                            self._open(out)
                    else:
                        self.q.put(('card', path, '✗ 失败', RED))
                except SystemExit:
                    self.q.put(('card', path, '✗ 失败', RED))
                except Exception:
                    self.q.put(('line', traceback.format_exc()))
                    self.q.put(('card', path, '✗ 失败', RED))
                self._done_count += 1
                self.bar.set(self._done_count / self._total_count)
        finally:
            sys.stdout, sys.stderr = old_out, old_err
            self.q.put(('line', '— 本轮结束 —'))
            self.q.put(('done',))

    def _prepare(self, path):
        """非标准格式（csv/json）先转换成标准 txt，返回可分析文件路径。"""
        if path.lower().endswith(TXT_EXT):
            return path
        tmpdir = os.path.join(tempfile.gettempdir(), 'wx_analyzer')
        os.makedirs(tmpdir, exist_ok=True)
        dst = os.path.join(tmpdir, os.path.splitext(os.path.basename(path))[0] + '.txt')
        convert.convert_file(path, dst)
        return dst

    # ---------------- 打开 ----------------
    def _open(self, path):
        try:
            os.startfile(path)
        except Exception:
            self.log('无法自动打开：%s' % path, 'warn')

    def open_report(self):
        if self.last_report and os.path.isfile(self.last_report):
            self._open(self.last_report)

    def open_folder(self):
        p = self.last_report
        if p and os.path.isfile(p):
            os.startfile(os.path.dirname(p))


# ---------------------------------------------------------------- 入口
def main():
    ensure_dpi_awareness()          # 必须在第一个窗口创建前
    files = []
    no_open = False
    for a in sys.argv[1:]:
        if a in ('--selftest', '-s'):
            app = App()
            app.after(1500, app.destroy)
            app.mainloop()
            # 打包成 exe 后没有控制台，把结果落到文件里供自动化验证
            try:
                base = (os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)
                        else os.path.dirname(os.path.abspath(__file__)))
                with open(os.path.join(base, '_selftest_ok.tmp'), 'w') as f:
                    f.write('ok %s' % time.strftime('%Y-%m-%d %H:%M:%S'))
            except Exception:
                pass
            return
        if a in ('--no-open',):
            no_open = True
        elif os.path.isfile(a):
            files.append(a)

    app = App(argv_files=files)
    if no_open:
        app.auto_open = False
        app.btn_auto.configure(text='完成后自动打开报告：关', fg=DIM)

    def hook(tp, val, tb):
        try:
            messagebox.showerror('程序出错',
                                 ''.join(traceback.format_exception(tp, val, tb))[-1800:])
        except Exception:
            pass

    sys.excepthook = hook
    if files:
        # 文件是拖到 exe 图标上进来的：载入后自动开始，省一次点击
        app.log('已从参数载入 %d 个文件，自动开始分析' % len(files), 'ok')
        app.after(600, app.run)
    app.mainloop()


if __name__ == '__main__':
    main()
