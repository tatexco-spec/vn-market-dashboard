# VN Market Dashboard

Clone của [traderwillhu/market_dashboard](https://github.com/traderwillhu/market_dashboard) cho thị trường Việt Nam.

## Kiến trúc

```
scripts/build_data.py   ← chạy vnstock thật, xuất JSON
data/snapshot.json      ← data tĩnh (git commit)
index.html              ← đọc snapshot.json, render dashboard
.github/workflows/      ← CI/CD tự động 15:30 ICT mỗi ngày
```

**Không cần server, không cần API key** — hoàn toàn static.

---

## Cài đặt local

```bash
# 1. Clone repo
git clone https://github.com/YOUR_USERNAME/vn-market-dashboard
cd vn-market-dashboard

# 2. Cài dependencies
pip install vnstock numpy

# 3. Chạy build lần đầu
python3 scripts/build_data.py

# 4. Mở dashboard
open index.html
# hoặc dùng local server (nếu cần fetch JSON):
python3 -m http.server 8080
# → http://localhost:8080
```

---

## Deploy GitHub Pages

### Lần đầu

1. Tạo repo public trên GitHub (vd: `vn-market-dashboard`)
2. Push code lên:
   ```bash
   git init
   git add .
   git commit -m "init"
   git remote add origin https://github.com/YOUR_USERNAME/vn-market-dashboard.git
   git push -u origin main
   ```
3. Vào **Settings → Pages → Source: GitHub Actions**
4. Chạy workflow thủ công lần đầu: **Actions → Refresh Market Data → Run workflow**

Dashboard sẽ live tại: `https://YOUR_USERNAME.github.io/vn-market-dashboard`

### Sau đó

- CI/CD tự chạy **08:30 UTC (15:30 ICT) thứ 2–6** sau giờ đóng cửa
- Muốn chạy thủ công: **Actions → Run workflow**
- Muốn chạy local: `python3 scripts/build_data.py` rồi commit `data/snapshot.json`

---

## Cấu trúc data/snapshot.json

```json
{
  "updated": "2025-03-18 15:25",
  "stocks": [
    {
      "symbol": "VCB",
      "sector": "Ngan hang",
      "in_vn30": true,
      "last": 98.5,
      "chg_pct": 1.23,
      "chg_1w": 2.1,
      "chg_1m": 5.4,
      "chg_3m": 12.3,
      "chg_12m": 18.5,
      "grade": "A",
      "atr_x": 1.2,
      "vars": 72,
      "from_52h": -3.2,
      "vol_ratio": 1.8,
      "rs_ms": 14.5,
      "rs": 85,
      "closes": [95.1, 96.2, ...]
    }
  ],
  "indices": { "VNINDEX": {"last": 1387.24, "chg_pct": 0.65} },
  "breadth":  { "advance": 35, "decline": 18, "grade_a": 22 },
  "macro":    { "usd_buy": 25450, "gold_buy": 92 },
  "etf":      [{ "symbol": "E1VFVN30", "nav": 18.25, "chg_pct": 0.72 }]
}
```

---

## Tính năng

| Feature | Mô tả |
|---|---|
| **Grade A/B/C** | EMA10 > EMA20 > SMA50 trend filter |
| **ATRx** | (Price - SMA50) / ATR14 — khoảng cách từ SMA50 |
| **VARS** | Volatility-Adjusted RS vs VN-Index (0-100) |
| **RS 1-99** | MarketSmith style: 40%×12T + 20%×3T + 20%×1T + 20%×1W, percentile rank |
| **Breakout row** | Nền vàng: Vol≥1.5× + ≤5% từ đỉnh 52T + ngày xanh |
| **RS leader** | Viền xanh: RS ≥ 80 |
| **Heatmap** | Sector performance map, click để filter |
| **TV Chart** | TradingView Advanced Chart, D/W/M/1Y/5Y |
| **Sparkline** | 90 ngày close price |

---

## Thêm cổ phiếu

Sửa list `STOCKS` trong `scripts/build_data.py`, thêm sector vào `SECTOR_MAP`.

## Nguồn data

- Giá cổ phiếu: **vnstock** (VCI source, fallback TCBS)
- Tỷ giá USD/VND: VCB
- Giá vàng: SJC
- Chart: TradingView widget (free)
