#!/usr/bin/env python3
"""
Pattern Scanner + Backtest
Chay sau build_data.py:  python3 scan_patterns.py
Output: data/pattern_signals.json
"""
import json, os, sys, time
import numpy as np
from datetime import datetime, timedelta

ATR_MULT=2.5; ATR_PERIOD=14; MA_FAST=50; MA_SLOW=200; OUTPERFORM_DAYS=10; YEARS_BACK=5
SCRIPT_DIR=os.path.dirname(os.path.abspath(__file__))
DATA_DIR=os.path.join(SCRIPT_DIR,'data')
OUT_FILE=os.path.join(DATA_DIR,'pattern_signals.json')
SNAP_FILE=os.path.join(DATA_DIR,'snapshot.json')
TODAY=datetime.now().strftime('%Y-%m-%d')
START_BT=(datetime.now()-timedelta(days=365*YEARS_BACK+30)).strftime('%Y-%m-%d')
SLEEP_SEC=1.2 if os.environ.get('VNSTOCK_API_KEY') else 3.5

STOCKS=['VCB','BID','CTG','MBB','TCB','ACB','VPB','HDB','STB','LPB',
        'VHM','VIC','VRE','NVL','KDH','HPG','HSG','NKG',
        'MSN','MWG','VNM','SAB','PNJ','DBC',
        'FPT','CMG','GAS','PLX','PVS','PVD',
        'REE','PC1','POW','DGC','DCM','DPM',
        'GMD','HAH','VSC','VJC','HVN',
        'VHC','ANV','IDI','TCM','TNG','MSH',
        'SSI','VCI','HCM','MBS','VND','KBC','DXG','PDR']

def fetch_bt(sym):
    from vnstock import Vnstock
    for src in ['VCI','TCBS']:
        for _ in range(2):
            try:
                df=Vnstock().stock(symbol=sym,source=src).quote.history(start=START_BT,end=TODAY,interval='1D')
                if df is not None and len(df)>=MA_SLOW+10:
                    time.sleep(SLEEP_SEC); return df
                break
            except Exception as e:
                msg=str(e)
                if 'rate' in msg.lower() or 'limit' in msg.lower() or 'Wait' in msg:
                    print(f"\n  Rate limit cho 65s...",file=sys.stderr); time.sleep(65)
                else:
                    time.sleep(3); break
    return None

def add_ind(df):
    df=df.copy(); cl=df['close'].astype(float)
    df['ma50']=cl.rolling(MA_FAST).mean(); df['ma200']=cl.rolling(MA_SLOW).mean()
    hi=df['high'].astype(float); lo=df['low'].astype(float)
    df['tr']=np.maximum(hi-lo,np.maximum((hi-cl.shift(1)).abs(),(lo-cl.shift(1)).abs()))
    df['atr']=df['tr'].rolling(ATR_PERIOD).mean()
    df['vol_ma20']=df['volume'].astype(float).rolling(20).mean()
    df['atr_ratio']=df['atr']/df['atr'].shift(30)
    return df

def calc_opf(df,vni,i,n=OUTPERFORM_DAYS):
    si=max(0,i-n); cl=df['close'].astype(float); op=df['open'].astype(float)
    if i-si<2: return 0.0,0,0,False
    sret=(cl.iloc[i]-cl.iloc[si])/cl.iloc[si]*100
    dates=[str(df['time'].values[j])[:10] for j in range(si,i+1)]
    ic=[vni.get(d) for d in dates if vni.get(d)]
    if len(ic)<2: return round(sret,2),0,0,sret>0
    score=sret-(ic[-1]-ic[0])/ic[0]*100
    red=gor=0
    for j in range(si+1,i+1):
        d=str(df['time'].values[j])[:10]; dp=str(df['time'].values[j-1])[:10]
        ni=vni.get(d); pi=vni.get(dp)
        if ni is None or pi is None: continue
        if ni<pi:
            red+=1
            if cl.iloc[j]>op.iloc[j]: gor+=1
    return round(score,2),red,gor,(score>0 and gor>=1)

def det_dgw(df):
    sigs=[]; cl=df['close'].astype(float); op=df['open'].astype(float); vol=df['volume'].astype(float)
    for i in range(MA_SLOW+1,len(df)):
        r=df.iloc[i]
        if np.isnan(r['ma200']) or np.isnan(r['atr']): continue
        hi60=cl.iloc[max(0,i-60):i].max()
        if(cl.iloc[i]<r['ma200'] and cl.iloc[i]<r['ma50'] and (hi60-cl.iloc[i])/hi60>0.20
           and vol.iloc[i]<r['vol_ma20'] and cl.iloc[i]>op.iloc[i]
           and (r['ma200']-cl.iloc[i])/r['ma200']<0.15): sigs.append(i)
    return sigs

def det_vcg(df):
    sigs=[]; cl=df['close'].astype(float); vol=df['volume'].astype(float)
    for i in range(MA_SLOW+30,len(df)):
        r=df.iloc[i]
        if np.isnan(r.get('atr_ratio',float('nan'))) or np.isnan(r['vol_ma20']): continue
        win=cl.iloc[i-20:i]; pr=(win.max()-win.min())/win.min()
        vl5=vol.iloc[i-5:i].mean(); vl15=vol.iloc[i-20:i-5].mean(); vtrd=vl5/vl15 if vl15>0 else 0
        if(pr<0.15 and r['atr_ratio']<0.70 and vtrd>1.2
           and cl.iloc[i]>cl.iloc[i-20:i-1].max() and vol.iloc[i]>1.5*r['vol_ma20']): sigs.append(i)
    return sigs

def det_hdg(df):
    sigs=[]; cl=df['close'].astype(float); op=df['open'].astype(float); vol=df['volume'].astype(float)
    for i in range(MA_SLOW+10,len(df)):
        r=df.iloc[i]
        if np.isnan(r['ma200']) or np.isnan(r['atr']): continue
        slope=(r['ma200']-df['ma200'].iloc[i-10])/df['ma200'].iloc[i-10]
        hi120=cl.iloc[max(0,i-120):i].max(); win15=cl.iloc[i-15:i]; lo60=cl.iloc[max(0,i-60):i].min()
        if(slope<-0.01 and (hi120-cl.iloc[i])/hi120>0.30
           and (win15.max()-win15.min())/win15.min()<0.12
           and abs(cl.iloc[i]-lo60)/lo60<0.05
           and vol.iloc[i-5:i].mean()<0.70*r['vol_ma20'] and cl.iloc[i]>op.iloc[i]): sigs.append(i)
    return sigs

def do_bt(df,ei,opf,score,gor,rd):
    if ei+1>=len(df): return None
    cl=df['close'].astype(float); lo=df['low'].astype(float)
    ep=float(cl.iloc[ei+1]); ed=str(df['time'].values[ei+1])[:10]
    hi=ep; stp=ep-ATR_MULT*float(df['atr'].iloc[ei+1]); xp=xd=xr=None
    for j in range(ei+2,len(df)):
        aj=df['atr'].iloc[j]
        if np.isnan(aj): continue
        if cl.iloc[j]>hi: hi=cl.iloc[j]
        stp=hi-ATR_MULT*float(aj)
        if cl.iloc[j]<stp or lo.iloc[j]<stp:
            xp=float(min(cl.iloc[j],stp)); xd=str(df['time'].values[j])[:10]; xr='trailing_stop'; break
    if xp is None: xp=float(cl.iloc[-1]); xd=str(df['time'].values[-1])[:10]; xr='end_of_data'
    days=(datetime.strptime(xd,'%Y-%m-%d')-datetime.strptime(ed,'%Y-%m-%d')).days
    return {'entry_date':ed,'entry_price':round(ep,2),'exit_date':xd,'exit_price':round(xp,2),
            'return_pct':round((xp-ep)/ep*100,2),'days_held':days,'exit_reason':xr,
            'max_price':round(hi,2),'max_ret_pct':round((hi-ep)/ep*100,2),
            'outperforms':opf,'outperform_score':score,'green_on_red':gor,'red_days':rd}

def stats(rets):
    if not rets: return {}
    a=np.array(rets); w=a[a>0]; l=a[a<=0]
    return {'total_trades':int(len(a)),'win_rate':round(len(w)/len(a)*100,1),
            'avg_return':round(float(a.mean()),2),'median_ret':round(float(np.median(a)),2),
            'avg_win':round(float(w.mean()),2) if len(w) else 0,
            'avg_loss':round(float(l.mean()),2) if len(l) else 0,
            'best':round(float(a.max()),2),'worst':round(float(a.min()),2)}

def main():
    if not os.path.exists(SNAP_FILE):
        print(f"ERROR: {SNAP_FILE} chua co — chay build_data.py truoc"); return
    with open(SNAP_FILE) as f: snap=json.load(f)
    vni_d=snap.get('indices',{}).get('VNINDEX',{})
    vni=dict(zip(vni_d.get('dates',[]),vni_d.get('closes',[])))
    print(f"=== Pattern Scan === VNINDEX {len(vni)} days | {len(STOCKS)} stocks | {YEARS_BACK}yr backtest")

    all_bt=[]; all_scan=[]; buckets={p:{'with':[],'without':[]} for p in ['DGW','VCG','HDG']}
    dets=[('DGW',det_dgw),('VCG',det_vcg),('HDG',det_hdg)]

    for idx,sym in enumerate(STOCKS):
        print(f"  [{idx+1}/{len(STOCKS)}] {sym}",end=' ',flush=True)
        df=fetch_bt(sym)
        if df is None: print("skip"); continue
        df=df.rename(columns=str.lower)
        if 'time' not in df.columns and 'date' in df.columns: df=df.rename(columns={'date':'time'})
        df['time']=df['time'].astype(str); df=df.sort_values('time').reset_index(drop=True)
        if len(df)<MA_SLOW+30: print("short"); continue
        df=add_ind(df)
        last_i=len(df)-1; cl=df['close'].astype(float); sig_n=0; today_s=[]

        for pat,det in dets:
            sigs=det(df)
            for si in sigs:
                score,rd,gor,opf=calc_opf(df,vni,si)
                res=do_bt(df,si,opf,score,gor,rd)
                if res:
                    res['symbol']=sym; res['pattern']=pat
                    all_bt.append(res); sig_n+=1
                    buckets[pat]['with' if opf else 'without'].append(res['return_pct'])
            if sigs and sigs[-1]==last_i:
                score,rd,gor,opf=calc_opf(df,vni,last_i)
                if opf:
                    r=df.iloc[last_i]
                    today_s.append({'symbol':sym,'pattern':pat,'date':str(df['time'].values[last_i])[:10],
                        'close':round(float(cl.iloc[last_i]),2),'atr':round(float(r['atr']),2),
                        'stop':round(float(cl.iloc[last_i])-ATR_MULT*float(r['atr']),2),
                        'vol_ratio':round(float(df['volume'].astype(float).iloc[last_i])/float(r['vol_ma20']),2) if r['vol_ma20']>0 else 0,
                        'outperform_score':score,'red_days':rd,'green_on_red':gor})
        all_scan.extend(today_s)
        print(f"bt={sig_n} today={len(today_s)}")

    print("\n── Backtest Split ──")
    summary={}
    for pat,bk in buckets.items():
        w=stats(bk['with']); wo=stats(bk['without'])
        summary[pat]={'with_outperform':w,'without_outperform':wo}
        if w:  print(f"  {pat} WITH:    WR={w['win_rate']}%  Avg={w['avg_return']}%  n={w['total_trades']}")
        if wo: print(f"  {pat} WITHOUT: WR={wo['win_rate']}%  Avg={wo['avg_return']}%  n={wo['total_trades']}")

    os.makedirs(DATA_DIR,exist_ok=True)
    out={'generated_at':datetime.now().strftime('%Y-%m-%d %H:%M'),
         'config':{'atr_mult':ATR_MULT,'outperform_days':OUTPERFORM_DAYS,'years_back':YEARS_BACK},
         'summary':summary,'today_signals':all_scan,
         'recent_trades':sorted(all_bt,key=lambda x:x['entry_date'],reverse=True)[:200]}
    with open(OUT_FILE,'w',encoding='utf-8') as f:
        json.dump(out,f,ensure_ascii=False,separators=(',',':'))
    print(f"\nDone: {OUT_FILE}  ({os.path.getsize(OUT_FILE)//1024} KB)  {len(all_bt)} trades  {len(all_scan)} signals today")

if __name__=='__main__':
    main()
