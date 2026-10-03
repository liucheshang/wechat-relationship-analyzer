# -*- coding: utf-8 -*-
"""
微信聊天记录深度分析 - 本地版
用法: python analyze.py 聊天记录.txt [输出.html]
输出完整HTML报告，所有数据本地处理，隐私零泄露。
"""
import sys, json, os
from datetime import datetime
from collections import defaultdict

# ===== 词典 =====
POSITIVE = ['喜欢','爱','想你','开心','哈哈','谢谢','好的','嗯呢','宝贝','宝宝','亲爱的','么么哒','晚安','早安','辛苦','好吃','好看','漂亮','可爱','加油','棒棒','爱你','亲亲','抱抱','嘿嘿','嘻嘻','太好啦','真好','幸福','温暖','感动','心疼','乖','乖乖','么么','爱死','超爱','最爱','爱你哦','想你了']
NEGATIVE = ['分手','算了','随便','烦','累','生气','讨厌','滚','再见','不想','难过','哭','失望','伤心','委屈','不理','为什么','怎么办','无所谓','哦','嗯','呵呵','心累','绝望','崩溃','窒息','压抑','痛苦','煎熬','折磨','冷战','沉默','无语','扯淡','离谱','过分','气死','讨厌你','不爱了','没感觉','不合适']
ANXIOUS = ['为什么不回','你在哪','你是不是不爱我','你不在乎我','我不重要','你到底','你根本不','我害怕','我担心','我好怕','你别离开','我怕失去','你是不是有别人']
AVOID = ['算了','不说了','随便','我没事','还好','还行','忙','嗯','哦','哦嗯','无所谓','不想说','你忙吧']
THREAT = ['分手','拉黑','不理你了','再也不','我走了','我消失','删了','永远不要']
SECURE = ['对不起','我错了','别生气','我理解','我知道','抱歉','我改','原谅我','我在乎','我担心你']
CRITICISM = ['你总是','你从来','你怎么又','为什么你不能','你每次','你就知道','你从来不','你总是这样']
DEFENSIVE = ['我没有','不是我','是你先','凭什么','我怎么了','又不是我','我以为','我只是']
CONTEMPT = ['呵呵','切','可笑','你真行','有病','幼稚','无聊','神经病','服了你']
STONEWALL = ['嗯','哦','不说了','随便','忙','呵呵','哦嗯','无所谓','算了','嗯呢']
CARE = ['吃饭','睡了吗','早点','身体','累不累','冷不冷','吃药','多喝热水','注意安全','到家了','吃了吗','喝水','休息','别熬夜','照顾好','心疼','难受','好点了吗','记得吃','多穿点']
NICKNAMES = ['宝宝','宝贝','老婆','老公','亲爱的','猪猪','乖乖','媳妇','哈尼','宝','老婆大人','小宝贝','乖乖女']
RATIONAL = ['所以','因为','但是','逻辑','道理','其实','应该','合理','分析','总结','计划','考虑','客观']
TONE_WORDS = ['哈','嗯','吧','哦','呀','呢','啊','嘛']
LOVE_WORDS = ['爱你','喜欢你','我爱你','好想你']
MISS_WORDS = ['想你','好想你','想念','惦记']

def cw(arr, words):
    c = 0
    for m in arr:
        for w in words:
            if w in m['content']: c += 1; break
    return c

def median(arr):
    if not arr: return 0
    s = sorted(arr); mid = len(s)//2
    return s[mid] if len(s)%2 else (s[mid-1]+s[mid])/2

def main():
    if len(sys.argv) < 2:
        print("用法: python analyze.py 聊天记录.txt [输出.html]")
        print("聊天记录格式: 2024-01-01 12:00 | 我 | 你好")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "chat_report.html"
    
    print(f"读取: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    messages = []
    for line in lines:
        line = line.strip()
        if not line: continue
        parts = line.split('|')
        if len(parts) < 3: continue
        try:
            dt = datetime.strptime(parts[0].strip(), '%Y-%m-%d %H:%M')
        except: continue
        sender = 'me' if parts[1].strip() in ('我','me','自己') else 'her'
        messages.append({'time': dt.timestamp()*1000, 'sender': sender, 'content': '|'.join(parts[2:]).strip(), 'dt': dt})
    
    messages.sort(key=lambda x: x['time'])
    total = len(messages)
    if total < 10:
        print("错误: 至少需要10条消息")
        sys.exit(1)
    
    print(f"解析成功: {total} 条消息")
    me = [m for m in messages if m['sender']=='me']
    her = [m for m in messages if m['sender']=='her']
    meCount, herCount = len(me), len(her)
    mePct, herPct = meCount/total*100, herCount/total*100
    times = sorted([m['time'] for m in messages])
    days = max(1, round((times[-1]-times[0])/86400000))
    
    mePos, herPos = cw(me,POSITIVE), cw(her,POSITIVE)
    meNeg, herNeg = cw(me,NEGATIVE), cw(her,NEGATIVE)
    gottman = (mePos+herPos)/max(1, meNeg+herNeg)
    
    sessions, cur = [], []
    for i, m in enumerate(messages):
        if i==0: cur=[m]
        else:
            if m['time']-messages[i-1]['time'] > 21600000: sessions.append(cur); cur=[m]
            else: cur.append(m)
    if cur: sessions.append(cur)
    sessionCount = len(sessions)
    openMe = sum(1 for s in sessions if s[0]['sender']=='me')
    openHer = sum(1 for s in sessions if s[0]['sender']=='her')
    
    meDelays, herDelays, meFast, herFast = [], [], 0, 0
    for i in range(1,len(messages)):
        diff = messages[i]['time']-messages[i-1]['time']
        if 60000<diff<3600000 and messages[i]['sender']!=messages[i-1]['sender']:
            if messages[i]['sender']=='me': meDelays.append(diff/60000); meFast += diff<60000
            else: herDelays.append(diff/60000); herFast += diff<60000
    meMed, herMed = median(meDelays), median(herDelays)
    
    maxBM=maxBH=b3M=b3H=b5M=b5H=0; cs=None; cb=0
    for m in messages:
        if m['sender']==cs:
            cb+=1
            if cb==3: b3M+=m['sender']=='me'; b3H+=m['sender']=='her'
            if cb==5: b5M+=m['sender']=='me'; b5H+=m['sender']=='her'
            if cb>maxBM and m['sender']=='me': maxBM=cb
            if cb>maxBH and m['sender']=='her': maxBH=cb
        else: cs=m['sender']; cb=1
    
    byDay = defaultdict(lambda: {'me':0,'her':0,'mePos':0,'meNeg':0,'herPos':0,'herNeg':0})
    byMonth = defaultdict(lambda: {'me':0,'her':0,'mePos':0,'meNeg':0,'herPos':0,'herNeg':0,'rMe':0,'rHe':0,'cMe':0,'cHe':0})
    byHour = [0]*24
    for m in messages:
        dk = m['dt'].strftime('%Y-%m-%d'); mk = m['dt'].strftime('%Y-%m')
        byHour[m['dt'].hour] += 1
        byDay[dk][m['sender']] += 1; byMonth[mk][m['sender']] += 1
        c = m['content']; s = m['sender']
        for w in POSITIVE:
            if w in c: byDay[dk][s+'Pos']+=1; byMonth[mk][s+'Pos']+=1; break
        for w in NEGATIVE:
            if w in c: byDay[dk][s+'Neg']+=1; byMonth[mk][s+'Neg']+=1; break
        for w in RATIONAL:
            if w in c: byMonth[mk]['r'+'Me' if s=='me' else 'rHe']+=1; break
        for w in CRITICISM:
            if w in c: byMonth[mk]['c'+'Me' if s=='me' else 'cHe']+=1; break
    
    daysArr = sorted(byDay.keys()); months = sorted(byMonth.keys())
    herStartDays = sum(1 for d in daysArr if byDay[d]['her']>0)
    maxGap = max(times[i]-times[i-1] for i in range(1,len(times)))
    maxGapDays = round(maxGap/86400000)
    
    conflictCount=repairMe=repairHer=tsM=tsH=0; cl=0; cli=-1
    for i,m in enumerate(messages):
        isNeg = any(w in m['content'] for w in NEGATIVE)
        if isNeg:
            if cl==0: cli=i
            cl+=1
        else:
            if cl>=2:
                conflictCount+=1
                sil = (messages[i]['time']-messages[cli]['time'])/3600000
                if messages[i]['sender']=='me': repairMe+=1; tsM+=sil
                else: repairHer+=1; tsH+=sil
            cl=0
    if cl>=2: conflictCount+=1
    
    anxM,anxH=cw(me,ANXIOUS),cw(her,ANXIOUS)
    avM,avH=cw(me,AVOID),cw(her,AVOID)
    thM,thH=cw(me,THREAT),cw(her,THREAT)
    seM,seH=cw(me,SECURE),cw(her,SECURE)
    crM,crH=cw(me,CRITICISM),cw(her,CRITICISM)
    dfM,dfH=cw(me,DEFENSIVE),cw(her,DEFENSIVE)
    ctM,ctH=cw(me,CONTEMPT),cw(her,CONTEMPT)
    stM,stH=cw(me,STONEWALL),cw(her,STONEWALL)
    caM,caH=cw(me,CARE),cw(her,CARE)
    nkM,nkH=cw(me,NICKNAMES),cw(her,NICKNAMES)
    lvM,lvH=cw(me,LOVE_WORDS),cw(her,LOVE_WORDS)
    msM,msH=cw(me,MISS_WORDS),cw(her,MISS_WORDS)
    fsM=sum(1 for m in me if '分手' in m['content'])
    fsH=sum(1 for m in her if '分手' in m['content'])
    pnM=sum(1 for m in me if '我' in m['content'])
    pnH=sum(1 for m in her if '我' in m['content'])
    pyM=sum(1 for m in me if '你' in m['content'])
    pyH=sum(1 for m in her if '你' in m['content'])
    qM=sum(1 for m in me if '？' in m['content'] or '?' in m['content'])
    qH=sum(1 for m in her if '？' in m['content'] or '?' in m['content'])
    toneM=[sum(1 for m in me if w in m['content']) for w in TONE_WORDS]
    toneH=[sum(1 for m in her if w in m['content']) for w in TONE_WORDS]
    
    daySent = [(d, (byDay[d]['mePos']+byDay[d]['herPos']-byDay[d]['meNeg']-byDay[d]['herNeg'])/max(1,byDay[d]['me']+byDay[d]['her'])) for d in daysArr]
    low5 = sorted(daySent, key=lambda x:x[1])[:5]
    high5 = sorted(daySent, key=lambda x:-x[1])[:5]
    
    gottmanM = [round((byMonth[mk]['mePos']+byMonth[mk]['herPos'])/max(1,byMonth[mk]['meNeg']+byMonth[mk]['herNeg']),1) for mk in months]
    rM = [round(byMonth[mk]['rMe']/max(1,byMonth[mk]['me']),2) for mk in months]
    rH = [round(byMonth[mk]['rHe']/max(1,byMonth[mk]['her']),2) for mk in months]
    cMv = [round(byMonth[mk]['cMe']/max(1,byMonth[mk]['me'])*1000,1) for mk in months]
    cHv = [round(byMonth[mk]['cHe']/max(1,byMonth[mk]['her'])*1000,1) for mk in months]
    mM = [round((byMonth[mk]['mePos']-byMonth[mk]['meNeg'])/max(1,byMonth[mk]['me'])*100,1) for mk in months]
    mH = [round((byMonth[mk]['herPos']-byMonth[mk]['herNeg'])/max(1,byMonth[mk]['her'])*100,1) for mk in months]
    dMe = [byDay[d]['me'] for d in daysArr]
    dHe = [byDay[d]['her'] for d in daysArr]
    
    nH, nW, nB = [], [], []
    for mk in months:
        ms = [m for m in messages if m['dt'].strftime('%Y-%m')==mk]
        nH.append(sum(1 for m in ms if '老公' in m['content']))
        nW.append(sum(1 for m in ms if '老婆' in m['content']))
        nB.append(sum(1 for m in ms if '宝宝' in m['content']))
    
    print("计算完成，生成报告...")
    relType = '单向投入型' if mePct>55 else ('分分合合型' if maxGapDays>30 else ('健康甜蜜型' if gottman>=5 else ('高风险型' if gottman<1.5 else '波动型')))
    
    # 读模板
    tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'report_template.html')
    with open(tpl_path, 'r', encoding='utf-8') as f:
        tpl = f.read()
    
    repl = {
        'TOTAL': f"{total:,}", 'DAYS': str(days),
        'HER_START_PCT': f"{herStartDays/days*100:.1f}",
        'GOTTMAN': f"{gottman:.1f}",
        'GOTTMAN_CLASS': 'hl-green' if gottman>=5 else ('hl-gold' if gottman>=2 else 'hl-red'),
        'MAX_GAP': str(maxGapDays),
        'GAP_CLASS': 'hl-green' if maxGapDays<=3 else ('hl-gold' if maxGapDays<=7 else 'hl-red'),
        'ME_MED': f"{meMed:.0f}", 'HER_MED': f"{herMed:.0f}",
        'CARE_HER': str(caH),
        'ME_PCT': f"{mePct:.1f}", 'HER_PCT': f"{herPct:.1f}",
        'REL_TYPE': relType,
        'HER_TYPE': '情绪明牌者' if anxH>anxM else '温和内敛者',
        'ME_TYPE': '情绪缓冲者' if avM>avH else '热情主动者',
        'MAX_BURST_HER': str(maxBH), 'THREAT_HER': str(thH), 'ANX_HER': str(anxH),
        'MAX_BURST_ME': str(maxBM), 'AVOID_ME': str(avM), 'Q_ME': str(qM),
        'PN_ME': f"{pnM:,}", 'PN_HER': f"{pnH:,}",
        'PY_ME': f"{pyM:,}", 'PY_HER': f"{pyH:,}",
        'Q_ME2': str(qM), 'Q_HER2': str(qH),
        'OPEN_ME': str(openMe), 'OPEN_HER': str(openHer),
        'OPEN_PCT': f"{openHer/sessionCount*100:.1f}",
        'ME_FAST': f"{meFast/max(1,len(meDelays))*100:.1f}",
        'HER_FAST': f"{herFast/max(1,len(herDelays))*100:.1f}",
        'BURST3_ME': str(b3M), 'BURST3_HER': str(b3H),
        'BURST5_ME': str(b5M), 'BURST5_HER': str(b5H),
        'CONFLICT': str(conflictCount),
        'REPAIR_ME': str(repairMe), 'REPAIR_HER': str(repairHer),
        'SIL_ME': f"{tsM/max(1,repairMe):.1f}", 'SIL_HER': f"{tsH/max(1,repairHer):.1f}",
        'FS_ME': str(fsM), 'FS_HER': str(fsH),
        'ME_COUNT': f"{meCount:,}", 'HER_COUNT': f"{herCount:,}",
        'NICK_ME': str(nkM), 'NICK_HER': str(nkH),
        'LOVE_ME': str(lvM), 'LOVE_HER': str(lvH),
        'MISS_ME': str(msM), 'MISS_HER': str(msH),
        'LOW_ROWS': ''.join(f'<tr><td>{d}</td><td class="num hl-red">{v*100:.1f}</td></tr>' for d,v in low5),
        'HIGH_ROWS': ''.join(f'<tr><td>{d}</td><td class="num hl-green">{v*100:.1f}</td></tr>' for d,v in high5),
        'START_DATE': datetime.fromtimestamp(messages[0]['time']/1000).strftime('%Y-%m-%d'),
        'END_DATE': datetime.fromtimestamp(messages[-1]['time']/1000).strftime('%Y-%m-%d'),
        'J_MONTHS': json.dumps(months, ensure_ascii=False),
        'J_GOTTMAN': json.dumps(gottmanM),
        'J_RME': json.dumps(rM), 'J_RHE': json.dumps(rH),
        'J_CME': json.dumps(cMv), 'J_CHE': json.dumps(cHv),
        'J_MME': json.dumps(mM), 'J_MHE': json.dumps(mH),
        'J_HOUR': json.dumps(byHour),
        'J_NH': json.dumps(nH), 'J_NW': json.dumps(nW), 'J_NB': json.dumps(nB),
        'J_DME': json.dumps(dMe), 'J_DHE': json.dumps(dHe),
        'J_TONE_M': json.dumps(toneM), 'J_TONE_H': json.dumps(toneH),
        'J_ANX_M': str(anxM), 'J_ANX_H': str(anxH),
        'J_AV_M': str(avM), 'J_AV_H': str(avH),
        'J_TH_M': str(thM), 'J_TH_H': str(thH),
        'J_SE_M': str(seM), 'J_SE_H': str(seH),
        'J_CR_M': str(crM), 'J_CR_H': str(crH),
        'J_DF_M': str(dfM), 'J_DF_H': str(dfH),
        'J_CT_M': str(ctM), 'J_CT_H': str(ctH),
        'J_ST_M': str(stM), 'J_ST_H': str(stH),
        'J_CA_M': str(caM), 'J_CA_H': str(caH),
        'J_NK_M': str(nkM), 'J_NK_H': str(nkH),
        'J_MP': str(mePos), 'J_HP': str(herPos),
    }
    
    for k, v in repl.items():
        tpl = tpl.replace('{{'+k+'}}', v)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(tpl)
    print(f"报告已生成: {output_file}")

if __name__ == '__main__':
    main()
