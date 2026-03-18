#!/usr/bin/env python3
"""
VN Market Dashboard — Data Builder
Chay: python3 scripts/build_data.py
Output: data/snapshot.json

Rate limit vnstock:
  Guest     : 20 req/phut  → SLEEP_SEC = 3.5 (an toan)
  Community : 60 req/phut  → SLEEP_SEC = 1.2
  Sponsor   : 180+ req/phut → SLEEP_SEC = 0.4

Dang ky API key mien phi tai: https://vnstocks.com/login
Sau khi co key, set bien moi truong:
  export VNSTOCK_API_KEY="your_key_here"
Hoac sua truc tiep VNSTOCK_API_KEY duoi day.
"""
import json, os, sys, numpy as np, time
from datetime import datetime, timedelta

# ── API key (tuy chon) ───────────────────────────────────────────────────────
VNSTOCK_API_KEY = os.environ.get('VNSTOCK_API_KEY', '')
if VNSTOCK_API_KEY:
    os.environ['VNSTOCK_API_KEY'] = VNSTOCK_API_KEY
    SLEEP_SEC = 1.2   # Community: 60 req/phut
    print(f"API key: ***{VNSTOCK_API_KEY[-4:]}  (60 req/phut)")
else:
    SLEEP_SEC = 3.5   # Guest: 20 req/phut → an toan
    print("Guest mode (20 req/phut) — se chay cham ~4 phut. Dang ky key mien phi tai vnstocks.com/login")

TODAY    = datetime.now().strftime('%Y-%m-%d')
START_1Y = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
START_3M = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
OUT_DIR  = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(OUT_DIR, exist_ok=True)

STOCKS = [
    'VCB','BID','CTG','MBB','TCB','ACB','VPB','HDB','STB','LPB',
    'VHM','VIC','VRE','NVL','KDH','HPG','HSG','NKG',
    'MSN','MWG','VNM','SAB','PNJ','DBC',
    'FPT','CMG','GAS','PLX','PVS','PVD',
    'REE','PC1','POW','DGC','DCM','DPM',
    'GMD','HAH','VSC','VJC','HVN',
    'VHC','ANV','IDI','TCM','TNG','MSH',
    'SSI','VCI','HCM','MBS','VND','KBC','DXG','PDR',
]
IDXS = ['VNINDEX','VN30','HNXINDEX','UPCOMINDEX']
SECTOR_MAP = {
    'VCB':'Ngan hang','BID':'Ngan hang','CTG':'Ngan hang','MBB':'Ngan hang','TCB':'Ngan hang',
    'ACB':'Ngan hang','VPB':'Ngan hang','HDB':'Ngan hang','STB':'Ngan hang','LPB':'Ngan hang',
    'SSI':'Chung khoan','VCI':'Chung khoan','HCM':'Chung khoan','MBS':'Chung khoan','VND':'Chung khoan',
    'VHM':'BDS','VIC':'BDS','VRE':'BDS','NVL':'BDS','KDH':'BDS','PDR':'BDS','DXG':'BDS','KBC':'BDS',
    'HPG':'Thep','HSG':'Thep','NKG':'Thep',
    'MSN':'Tieu dung','MWG':'Tieu dung','VNM':'Tieu dung','SAB':'Tieu dung','PNJ':'Tieu dung','DBC':'Tieu dung',
    'FPT':'Cong nghe','CMG':'Cong nghe',
    'GAS':'Dau khi','PLX':'Dau khi','PVS':'Dau khi','PVD':'Dau khi',
    'REE':'Dien','PC1':'Dien','POW':'Dien',
    'DGC':'Hoa chat','DCM':'Hoa chat','DPM':'Hoa chat',
    'GMD':'Logistics','HAH':'Logistics','VSC':'Logistics',
    'VJC':'Hang khong','HVN':'Hang khong',
    'VHC':'Thuy san','ANV':'Thuy san','IDI':'Thuy san',
    'TCM':'Det may','TNG':'Det may','MSH':'Det may',
}
VN30 = ['VCB','BID','CTG','MBB','TCB','ACB','VPB','HDB','STB','LPB',
        'VHM','VIC','VRE','NVL','KDH','HPG','MSN','MWG','VNM','SAB',
        'PNJ','FPT','CMG','GAS','PLX','VJC','HVN','SSI','VCI','REE']


def fetch(sym, start, source='VCI'):
    """Fetch OHLCV từ vnstock, fallback TCBS nếu VCI lỗi
    Free tier: 20 req/min → cần delay >= 3s giữa mỗi request
    Đăng ký API key miễn phí tại vnstocks.com/login để tăng lên 60/min
    """
    from vnstock import Vnstock
    for src in [source, 'TCBS']:
        for attempt in range(3):   # retry 3 lần
            try:
                df = Vnstock().stock(symbol=sym, source=src).quote.history(
                    start=start, end=TODAY, interval='1D')
                if df is not None and len(df) >= 5:
                    time.sleep(SLEEP_SEC)
                    return df
                break
            except Exception as e:
                msg = str(e)
                if 'rate' in msg.lower() or 'limit' in msg.lower() or 'Wait' in msg:
                    wait = 65
                    print(f"\n    ⏳ Rate limit — chờ {wait}s rồi retry...", file=sys.stderr)
                    time.sleep(wait)
                else:
                    print(f"    [{src}] {e}", file=sys.stderr)
                    time.sleep(3)
                    break
    return None


def calc_stock(sym, df):
    cl   = df['close'].astype(float).values
    vl   = df['volume'].astype(float).values if 'volume' in df.columns else None
    last = float(cl[-1])
    prev = float(cl[-2])
    chg  = round((last - prev) / abs(prev) * 100, 2) if prev else 0

    e10  = float(df['close'].astype(float).ewm(span=10, adjust=False).mean().iloc[-1])
    e20  = float(df['close'].astype(float).ewm(span=20, adjust=False).mean().iloc[-1])
    s50  = float(cl[-50:].mean())  if len(cl) >= 50  else None
    s200 = float(cl[-200:].mean()) if len(cl) >= 200 else None
    grade = 'A' if (s50 and e10 > e20 > s50) else ('B' if e10 > e20 else 'C')

    atr_x = None
    if s50 and len(cl) >= 15 and 'high' in df.columns:
        hi  = df['high'].astype(float).values
        lo  = df['low'].astype(float).values
        tr  = np.maximum(hi - lo, np.maximum(abs(hi - np.roll(cl, 1)), abs(lo - np.roll(cl, 1))))
        a14 = float(tr[-14:].mean())
        atr_x = round((last - s50) / a14, 2) if a14 > 0 else None

    def pct(n):
        return round((last - float(cl[-n])) / abs(float(cl[-n])) * 100, 2) if len(cl) >= n else None

    c1w  = pct(6)
    c1m  = pct(22)
    c3m  = pct(63)
    c12m = pct(252)

    # MarketSmith RS weighted score (raw — percentile rank tính sau)
    rs_ms = round(0.4 * (c12m or 0) + 0.2 * (c3m or 0) +
                  0.2 * (c1m  or 0) + 0.2 * (c1w or 0), 2)

    # VARS — volatility-adjusted RS
    r21    = (last - float(cl[-22])) / abs(float(cl[-22])) if len(cl) >= 22 else 0
    vars_v = round(min(100, max(0, 50 + 40 * (r21 / max(abs(r21), 0.001)) / 0.015)), 1)

    hi52 = float(cl[-252:].max()) if len(cl) >= 252 else float(cl.max())
    f52  = round((last - hi52) / hi52 * 100, 2)

    vr = None
    if vl is not None and len(vl) >= 20:
        a20 = float(vl[-20:].mean())
        vr  = round(float(vl[-1]) / a20, 2) if a20 > 0 else None

    return {
        'symbol':   sym,
        'sector':   SECTOR_MAP.get(sym, 'Khac'),
        'in_vn30':  sym in VN30,
        'last':     round(last, 2),
        'vol':      int(vl[-1]) if vl is not None else None,
        'chg_pct':  chg,
        'chg_1w':   c1w,
        'chg_1m':   c1m,
        'chg_3m':   c3m,
        'chg_12m':  c12m,
        'grade':    grade,
        'atr_x':    atr_x,
        'vars':     vars_v,
        'from_52h': f52,
        'vol_ratio':vr,
        'sma50':    round(s50, 2)  if s50  else None,
        'sma200':   round(s200, 2) if s200 else None,
        'rs_ms':    rs_ms,
        'closes':   [round(float(x), 1) for x in cl[-90:]],  # sparkline
    }


def rs_percentile(stocks):
    """Chuyển rs_ms raw score thành MarketSmith RS 1-99 percentile rank"""
    scores  = [s['rs_ms'] if s['rs_ms'] is not None else -9999 for s in stocks]
    sorted_ = sorted(scores)
    n       = len(sorted_)
    for i, s in enumerate(stocks):
        sc = scores[i]
        if sc == -9999:
            s['rs'] = None
            continue
        rank  = sum(1 for x in sorted_ if x < sc)
        s['rs'] = max(1, min(99, round(rank / (n - 1) * 98) + 1))
    return stocks


def build():
    print(f"=== VN Market Builder — {TODAY} ===")
    R = {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'stocks':  [],
        'indices': {},
        'breadth': {},
        'macro':   {},
        'etf':     [],
    }

    # Stocks
    for sym in STOCKS:
        print(f"  {sym}...", end=' ', flush=True)
        df = fetch(sym, START_1Y)
        if df is None:
            print("SKIP"); continue
        try:
            d = calc_stock(sym, df)
            R['stocks'].append(d)
            print(f"OK  {d['last']}  {d['grade']}  RS_raw={d['rs_ms']}")
        except Exception as e:
            print(f"ERR: {e}", file=sys.stderr)

    R['stocks'] = rs_percentile(R['stocks'])

    # Indices
    for sym in IDXS:
        print(f"  {sym}...", end=' ', flush=True)
        df = fetch(sym, START_3M)
        if df is None:
            print("SKIP"); continue
        cl   = df['close'].astype(float).values
        last = float(cl[-1]); prev = float(cl[-2])
        R['indices'][sym] = {
            'last':    round(last, 2),
            'chg_pct': round((last - prev) / abs(prev) * 100, 2),
            'chg':     round(last - prev, 2),
            'closes':  [round(float(x), 1) for x in cl[-90:]],
        }
        print(f"OK  {round(last,2)}")

    # Breadth
    n   = len(R['stocks'])
    adv = sum(1 for s in R['stocks'] if (s.get('chg_pct') or 0) > 0)
    dec = sum(1 for s in R['stocks'] if (s.get('chg_pct') or 0) < 0)
    R['breadth'] = {
        'advance':         adv,
        'decline':         dec,
        'unchanged':       n - adv - dec,
        'pct_above_ma50':  round(sum(1 for s in R['stocks'] if s.get('sma50')  and s['last'] > s['sma50'])  / max(n, 1) * 100, 1),
        'pct_above_ma200': round(sum(1 for s in R['stocks'] if s.get('sma200') and s['last'] > s['sma200']) / max(n, 1) * 100, 1),
        'grade_a': sum(1 for s in R['stocks'] if s.get('grade') == 'A'),
        'grade_b': sum(1 for s in R['stocks'] if s.get('grade') == 'B'),
        'grade_c': sum(1 for s in R['stocks'] if s.get('grade') == 'C'),
    }

    # Macro
    try:
        from vnstock.explorer.misc import vcb_exchange_rate, sjc_gold_price
        fx = vcb_exchange_rate()
        if hasattr(fx, 'iterrows'):
            for _, row in fx.iterrows():
                if 'USD' in str(row.get('currency_code', '')):
                    R['macro']['usd_buy']  = float(row.get('buy', 0))
                    R['macro']['usd_sell'] = float(row.get('sell', 0))
                    break
        gd = sjc_gold_price()
        if hasattr(gd, 'iloc'):
            R['macro']['gold_buy']  = float(gd.iloc[0].get('buy', 0))
            R['macro']['gold_sell'] = float(gd.iloc[0].get('sell', 0))
        print("  Macro OK")
    except Exception as e:
        print(f"  Macro skip: {e}", file=sys.stderr)

    # Write
    out = os.path.join(OUT_DIR, 'snapshot.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(R, f, ensure_ascii=False, separators=(',', ':'))

    kb = os.path.getsize(out) // 1024
    print(f"\n✅  {out}  ({kb} KB)  —  {n} stocks")


if __name__ == '__main__':
    build()
