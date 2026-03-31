import json,os,sqlite3,numpy as np
from datetime import datetime
SCRIPT_DIR=os.path.dirname(os.path.abspath(__file__))
DATA_DIR=os.path.join(SCRIPT_DIR,'data')
DB_FILE=os.path.join(DATA_DIR,'ohlcv.db')
OUT_FILE=os.path.join(DATA_DIR,'snapshot.json')
TODAY=datetime.now().strftime('%Y-%m-%d')
CANDLES=252
print('build_data_new.py loaded OK')
print('DB exists:', os.path.exists(DB_FILE))

STOCKS=['VCB','BID','CTG','MBB','TCB','ACB','VPB','HDB','STB','LPB','VHM','VIC','VRE','NVL','KDH','HPG','HSG','NKG','MSN','MWG','VNM','SAB','PNJ','DBC','FPT','CMG','GAS','PLX','PVS','PVD','REE','PC1','POW','DGC','DCM','DPM','GMD','HAH','VSC','VJC','HVN','VHC','ANV','IDI','TCM','TNG','MSH','SSI','VCI','HCM','MBS','VND','KBC','DXG','PDR']
IDXS=['VNINDEX','VN30','HNXINDEX','UPCOMINDEX']
SECTOR_MAP={'VCB':'Ngan hang','BID':'Ngan hang','CTG':'Ngan hang','MBB':'Ngan hang','TCB':'Ngan hang','ACB':'Ngan hang','VPB':'Ngan hang','HDB':'Ngan hang','STB':'Ngan hang','LPB':'Ngan hang','SSI':'Chung khoan','VCI':'Chung khoan','HCM':'Chung khoan','MBS':'Chung khoan','VND':'Chung khoan','VHM':'BDS','VIC':'BDS','VRE':'BDS','NVL':'BDS','KDH':'BDS','PDR':'BDS','DXG':'BDS','KBC':'BDS','HPG':'Thep','HSG':'Thep','NKG':'Thep','MSN':'Tieu dung','MWG':'Tieu dung','VNM':'Tieu dung','SAB':'Tieu dung','PNJ':'Tieu dung','DBC':'Tieu dung','FPT':'Cong nghe','CMG':'Cong nghe','GAS':'Dau khi','PLX':'Dau khi','PVS':'Dau khi','PVD':'Dau khi','REE':'Dien','PC1':'Dien','POW':'Dien','DGC':'Hoa chat','DCM':'Hoa chat','DPM':'Hoa chat','GMD':'Logistics','HAH':'Logistics','VSC':'Logistics','VJC':'Hang khong','HVN':'Hang khong','VHC':'Thuy san','ANV':'Thuy san','IDI':'Thuy san','TCM':'Det may','TNG':'Det may','MSH':'Det may'}
VN30=['VCB','BID','CTG','MBB','TCB','ACB','VPB','HDB','STB','LPB','VHM','VIC','VRE','NVL','KDH','HPG','MSN','MWG','VNM','SAB','PNJ','FPT','CMG','GAS','PLX','VJC','HVN','SSI','VCI','REE']

def load(conn,sym,n=600):
    cur=conn.execute('SELECT date,open,high,low,close,volume FROM ohlcv WHERE symbol=? ORDER BY date DESC LIMIT ?',(sym,n))
    rows=cur.fetchall()
    if not rows: return None
    rows.reverse()
    return [r[0] for r in rows],[r[1] for r in rows],[r[2] for r in rows],[r[3] for r in rows],[r[4] for r in rows],[r[5] for r in rows]

def calc(sym,conn):
    data=load(conn,sym)
    if not data: return None
    dates,op,hi,lo,cl,vl=data
    cl=np.array([x if x else 0 for x in cl],dtype=float)
    op=np.array([x if x else cl[i] for i,x in enumerate(op)],dtype=float)
    hi=np.array([x if x else cl[i] for i,x in enumerate(hi)],dtype=float)
    lo=np.array([x if x else cl[i] for i,x in enumerate(lo)],dtype=float)
    vl=np.array([x if x else 0 for x in vl],dtype=float)
    if len(cl)<5: return None
    last=float(cl[-1]); prev=float(cl[-2]) if len(cl)>=2 else last
    chg=round((last-prev)/abs(prev)*100,2) if prev else 0
    def ema(a,s):
        k=2/(s+1);e=a[0]
        for v in a[1:]: e=v*k+e*(1-k)
        return e
    e10=ema(cl,10);e20=ema(cl,20)
    s50=float(cl[-50:].mean()) if len(cl)>=50 else None
    s200=float(cl[-200:].mean()) if len(cl)>=200 else None
    grade='A' if (s50 and e10>e20>s50) else ('B' if e10>e20 else 'C')
    a14=atr_x=None
    if s50 and len(cl)>=15:
        tr=np.maximum(hi-lo,np.maximum(abs(hi-np.roll(cl,1)),abs(lo-np.roll(cl,1))))
        a14=float(tr[-14:].mean())
        atr_x=round((last-s50)/a14,2) if a14>0 else None
    def pct(n): return round((last-float(cl[-n]))/abs(float(cl[-n]))*100,2) if len(cl)>=n else None
    c1w=pct(6);c1m=pct(22);c3m=pct(63);c12m=pct(252)
    rs_ms=round(0.4*(c12m or 0)+0.2*(c3m or 0)+0.2*(c1m or 0)+0.2*(c1w or 0),2)
    r21=(last-float(cl[-22]))/abs(float(cl[-22])) if len(cl)>=22 else 0
    vars_v=round(min(100,max(0,50+40*(r21/max(abs(r21),0.001))/0.015)),1)
    hi52=float(cl[-252:].max()) if len(cl)>=252 else float(cl.max())
    f52=round((last-hi52)/hi52*100,2)
    vr=None
    if len(vl)>=20:
        a20=float(vl[-20:].mean());vr=round(float(vl[-1])/a20,2) if a20>0 else None
    n=CANDLES
    return {'symbol':sym,'sector':SECTOR_MAP.get(sym,'Khac'),'in_vn30':sym in VN30,'last':round(last,2),'vol':int(vl[-1]) if len(vl) else None,'chg_pct':chg,'chg_1w':c1w,'chg_1m':c1m,'chg_3m':c3m,'chg_12m':c12m,'grade':grade,'atr_x':atr_x,'atr14':round(a14,2) if a14 else None,'vars':vars_v,'from_52h':f52,'vol_ratio':vr,'sma50':round(s50,2) if s50 else None,'sma200':round(s200,2) if s200 else None,'ema10':round(e10,2),'ema20':round(e20,2),'rs_ms':rs_ms,'dates':dates[-n:],'closes':[round(float(x),1) for x in cl[-n:]],'opens':[round(float(x),1) for x in op[-n:]],'highs':[round(float(x),1) for x in hi[-n:]],'lows':[round(float(x),1) for x in lo[-n:]],'volumes':[int(x) for x in vl[-n:]]}

def rs_pct(stocks):
    sc=[s['rs_ms'] if s['rs_ms'] is not None else -9999 for s in stocks]
    sd=sorted(sc);n=len(sd)
    for i,s in enumerate(stocks):
        v=sc[i]
        if v==-9999: s['rs']=None; continue
        r=sum(1 for x in sd if x<v)
        s['rs']=max(1,min(99,round(r/(n-1)*98)+1))
    return stocks

def main():
    print(f'=== build_data.py (DB) === {TODAY}')
    conn=sqlite3.connect(DB_FILE)
    R={'updated':datetime.now().strftime('%Y-%m-%d %H:%M'),'stocks':[],'indices':{},'breadth':{},'macro':{},'etf':[]}
    for sym in STOCKS:
        print(f'  {sym}...',end=' ',flush=True)
        d=calc(sym,conn)
        if d: R['stocks'].append(d); print(f"OK {d['last']} {d['grade']}")
        else: print('no data')
    R['stocks']=rs_pct(R['stocks'])
    for sym in IDXS:
        print(f'  {sym}...',end=' ',flush=True)
        data=load(conn,sym,600)
        if not data: print('no data'); continue
        dates,_,_,_,closes,_=data
        cl=[c for c in closes if c]
        last=float(cl[-1]);prev=float(cl[-2])
        R['indices'][sym]={'last':round(last,2),'chg_pct':round((last-prev)/abs(prev)*100,2),'chg':round(last-prev,2),'dates':dates[-CANDLES:],'closes':[round(float(x),1) for x in cl[-CANDLES:]]}
        print(f'OK {round(last,2)}')
    conn.close()
    n=len(R['stocks']);adv=sum(1 for s in R['stocks'] if (s.get('chg_pct') or 0)>0);dec=sum(1 for s in R['stocks'] if (s.get('chg_pct') or 0)<0)
    R['breadth']={'advance':adv,'decline':dec,'unchanged':n-adv-dec,'pct_above_ma50':round(sum(1 for s in R['stocks'] if s.get('sma50') and s['last']>s['sma50'])/max(n,1)*100,1),'pct_above_ma200':round(sum(1 for s in R['stocks'] if s.get('sma200') and s['last']>s['sma200'])/max(n,1)*100,1),'grade_a':sum(1 for s in R['stocks'] if s.get('grade')=='A'),'grade_b':sum(1 for s in R['stocks'] if s.get('grade')=='B'),'grade_c':sum(1 for s in R['stocks'] if s.get('grade')=='C')}
    os.makedirs(DATA_DIR,exist_ok=True)
    with open(OUT_FILE,'w',encoding='utf-8') as f: json.dump(R,f,ensure_ascii=False,separators=(',',':'))
    print(f'\nDone: {OUT_FILE} ({os.path.getsize(OUT_FILE)//1024}KB) {n} stocks')

main()
