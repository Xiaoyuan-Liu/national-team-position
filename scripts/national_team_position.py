#!/usr/bin/env python3
"""
国家队持仓估计工具（全宽基版）

通过追踪上交所核心宽基 ETF 的份额变化，估计中央汇金（国家队）的持仓变动与结构轮动：
  上证50 / 沪深300 / 中证500 / 中证1000 / 中证A500 / 科创50

默认输出：
  1) 一张六合一总图（2x3，每格 = 该宽基份额 + 对应指数价格双轴）
  2) 6 张各指数单图（同样的份额 + 指数价格双轴）
  3) JSON：各宽基份额时间序列 + 全宽基合计

数据来源：上海证券交易所 ETF 份额接口（fund_etf_scale_sse，一次返回当日全部 ETF）
          + AKShare 指数日线。
注意：创业板等 ETF 全在深交所，本接口取不到，未纳入。
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    import akshare as ak
    import pandas as pd
except ImportError:
    print("请先安装依赖: pip install akshare pandas matplotlib")
    sys.exit(1)

# ---- 各宽基指数对应的上交所 ETF（A500 用名称匹配，代码太多）----
CODE_GROUPS = {
    "上证50":   ["510050", "510710", "510850", "510800"],
    "沪深300":  ["510300", "510310", "510330", "510350", "510360", "510380", "515330", "510390"],
    "中证500":  ["510500", "510510", "512500", "515550"],
    "中证1000": ["512100", "560010"],
    "科创50":   ["588000", "588080", "588090", "588050"],
}
A500_KEY = "中证A500"  # 基金简称含 "A500"
GROUP_ORDER = ["沪深300", "上证50", "中证500", "中证1000", "中证A500", "科创50"]

# 各指数价格的 AKShare symbol（带候选回退）
INDEX_SYMBOLS = {
    "沪深300":  ["sh000300"],
    "上证50":   ["sh000016"],
    "中证500":  ["sh000905"],
    "中证1000": ["sh000852"],
    "中证A500": ["sh000510", "csi000510"],
    "科创50":   ["sh000688"],
}
COLORS = {
    "沪深300": "#e74c3c", "上证50": "#e67e22", "中证500": "#27ae60",
    "中证1000": "#8e44ad", "中证A500": "#2980b9", "科创50": "#795548",
}
FNAME = {
    "沪深300": "hs300", "上证50": "sse50", "中证500": "csi500",
    "中证1000": "csi1000", "中证A500": "csiA500", "科创50": "star50",
}


# ============================ 取数 ============================
def sample_dates(start_date, end_date, freq):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    out = []
    if freq == "weekly":
        d = start
        while d.weekday() != 4:  # 周五
            d += timedelta(days=1)
        while d <= end:
            out.append(d)
            d += timedelta(days=7)
    else:
        d = start.replace(day=15)
        while d <= end:
            out.append(d)
            d = (d.replace(year=d.year + 1, month=1) if d.month == 12
                 else d.replace(month=d.month + 1))
    return out


def group_shares(df):
    """从单日 ETF 规模 df 计算各宽基份额（亿份）"""
    codes = df["基金代码"].astype(str)
    names = df["基金简称"].astype(str)
    shares = pd.to_numeric(df["基金份额"], errors="coerce").fillna(0)
    res = {}
    for idx, code_list in CODE_GROUPS.items():
        res[idx] = round(float(shares[codes.isin(code_list)].sum()) / 1e8, 2)
    res[A500_KEY] = round(float(shares[names.str.contains("A500", na=False)].sum()) / 1e8, 2)
    res["全宽基合计"] = round(sum(res[g] for g in GROUP_ORDER), 2)
    return res


def fetch_shares(start_date, end_date, freq):
    dates = sample_dates(start_date, end_date, freq)
    print(f"共 {len(dates)} 个采样点需要查询...")
    results, fail = [], 0
    for i, sd in enumerate(dates):
        found = False
        for offset in [0, -1, -2, -3, -4]:
            try_str = (sd + timedelta(days=offset)).strftime("%Y%m%d")
            try:
                df = ak.fund_etf_scale_sse(date=try_str)
                if df is not None and "基金代码" in df.columns and len(df) > 0:
                    gs = group_shares(df)
                    if gs["全宽基合计"] > 0:
                        results.append({"date": try_str, **gs})
                        found = True
                        if (i + 1) % 10 == 0 or i == 0:
                            print(f"  [{i+1}/{len(dates)}] {try_str}: 全宽基 {gs['全宽基合计']:.0f}亿 "
                                  f"(300={gs['沪深300']:.0f} A500={gs['中证A500']:.0f} 科创50={gs['科创50']:.0f})")
                        break
            except Exception:
                pass
            time.sleep(0.2)
        if not found:
            fail += 1
        time.sleep(0.3)
    print(f"完成！成功 {len(results)} 条，失败 {fail} 条")
    return results


def fetch_index_prices(start):
    print("=== 抓取各指数价格 ===")
    prices = {}
    for name, syms in INDEX_SYMBOLS.items():
        prices[name] = None
        for sym in syms:
            try:
                df = ak.stock_zh_index_daily(symbol=sym)
                if df is not None and len(df) > 0 and "close" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                    df = df[df["date"] >= start]
                    if len(df) > 0:
                        prices[name] = df
                        print(f"  {name}: {sym} ok ({len(df)} 行)")
                        break
            except Exception as ex:
                print(f"  {name}: {sym} 失败 {ex}")
        if prices[name] is None:
            print(f"  {name}: 无价格数据，仅画份额")
    return prices


# ============================ 画图 ============================
def _draw(ax, name, dates, shares, price_df, title_fs=13, label_fs=11, ann_fs=8):
    import matplotlib.dates as mdates
    c = COLORS[name]
    ax.plot(dates, shares, "o-", color=c, lw=2, ms=3, zorder=6,
            label=f"{name} ETF份额(亿份)")
    ax.fill_between(dates, shares, alpha=0.10, color=c)
    ax.set_ylabel("ETF 份额（亿份）", fontsize=label_fs, color=c)
    ax.tick_params(axis="y", labelcolor=c)
    lo, hi = min(shares), max(shares)
    m = (hi - lo) * 0.15 or hi * 0.1 or 1
    ax.set_ylim(max(0, lo - m), hi + m)

    pk = shares.index(max(shares))
    ax.annotate(f"峰值{shares[pk]:.0f}", xy=(dates[pk], shares[pk]),
                xytext=(-38, 14), textcoords="offset points", fontsize=ann_fs,
                fontweight="bold", arrowprops=dict(arrowstyle="->", color="#333"),
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#fff3cd", edgecolor="#ffc107"))
    ax.annotate(f"最新{shares[-1]:.0f}", xy=(dates[-1], shares[-1]),
                xytext=(8, 8), textcoords="offset points", fontsize=ann_fs,
                fontweight="bold", arrowprops=dict(arrowstyle="->", color="#333"),
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#fff3cd", edgecolor="#ffc107"))

    ax2 = ax.twinx()
    if price_df is not None:
        ax2.plot(price_df["date"], price_df["close"], "-", color="#34495e",
                 lw=1.1, alpha=0.6, label=f"{name}指数")
        ax2.set_ylabel("指数点位", fontsize=label_fs)
    ax.set_title(f"{name}：ETF份额 vs 指数走势", fontsize=title_fs, fontweight="bold")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.grid(True, alpha=0.2)
    l1, lb1 = ax.get_legend_handles_labels()
    l2, lb2 = ax2.get_legend_handles_labels()
    ax.legend(l1 + l2, lb1 + lb2, loc="upper left", fontsize=ann_fs, framealpha=0.9)


def _series_for(data, all_dates, g, prices):
    """取某宽基的份额序列（从首个非零值起，避免一长串0）和裁剪后的价格 df"""
    series = [d[g] for d in data]
    i0 = next((i for i, v in enumerate(series) if v > 0), 0)
    dts, sh = all_dates[i0:], series[i0:]
    pdf = prices.get(g)
    if pdf is not None:
        pdf = pdf[pdf["date"] >= dts[0]]
    return dts, sh, pdf


def make_charts(data, prices, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "PingFang SC", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False

    all_dates = [datetime.strptime(d["date"], "%Y%m%d") for d in data]

    # 1) 六合一总图
    print("\n=== 生成六合一总图 ===")
    fig, axes = plt.subplots(2, 3, figsize=(22, 11))
    for g, ax in zip(GROUP_ORDER, axes.flat):
        dts, sh, pdf = _series_for(data, all_dates, g, prices)
        _draw(ax, g, dts, sh, pdf)
    fig.suptitle("国家队各宽基 ETF 份额 vs 指数走势（估计中央汇金持仓）",
                 fontsize=17, fontweight="bold")
    # autofmt_xdate 会隐藏非底行子图的日期标签，逐轴设置确保六张图都显示
    for ax in axes.flat:
        ax.tick_params(axis="x", labelbottom=True, labelrotation=45)
        for label in ax.get_xticklabels():
            label.set_horizontalalignment("right")
    fig.tight_layout(rect=[0, 0, 1, 0.97], h_pad=3.0)
    p = os.path.join(out_dir, "national_team_overview.png")
    plt.savefig(p, dpi=140); plt.close(fig)
    print(f"  总图 -> {p}")

    # 2) 各指数单图
    print("\n=== 生成各指数单图 ===")
    for g in GROUP_ORDER:
        dts, sh, pdf = _series_for(data, all_dates, g, prices)
        fig, ax = plt.subplots(figsize=(12, 6))
        _draw(ax, g, dts, sh, pdf)
        fig.autofmt_xdate(rotation=45)
        plt.tight_layout()
        p = os.path.join(out_dir, f"national_team_{FNAME[g]}.png")
        plt.savefig(p, dpi=150); plt.close(fig)
        print(f"  {g} -> {p}")


# ============================ 汇总 ============================
def summarize(data):
    print("\n=== 各宽基份额（亿份）：起始 / 峰值 / 最新 / 变化 ===")
    first, last = data[0], data[-1]
    for g in GROUP_ORDER + ["全宽基合计"]:
        series = [d[g] for d in data]
        pk = max(series); pk_dt = data[series.index(pk)]["date"]
        print(f"{g:>8}: {first[g]:7.0f} → 峰值{pk:7.0f}({pk_dt}) → 最新{last[g]:7.0f}   净变 {last[g]-first[g]:+8.0f}")

    s300 = [d["沪深300"] for d in data]
    pi = max(range(len(s300)), key=lambda i: s300[i])
    print("\n=== 轮动 vs 撤离 ===")
    print(f"沪深300自峰值({data[pi]['date']}, {s300[pi]:.0f}亿)至今: {last['沪深300']-s300[pi]:+.0f} 亿份")
    others_pk = sum(data[pi][g] for g in GROUP_ORDER if g != "沪深300")
    others_now = sum(last[g] for g in GROUP_ORDER if g != "沪深300")
    print(f"同期其他宽基合计: {others_pk:.0f} → {others_now:.0f} ({others_now-others_pk:+.0f})")
    print(f"全宽基合计同期: {data[pi]['全宽基合计']:.0f} → {last['全宽基合计']:.0f} "
          f"({last['全宽基合计']-data[pi]['全宽基合计']:+.0f})")


# ============================ main ============================
def main():
    ap = argparse.ArgumentParser(description="国家队持仓估计工具（全宽基版）")
    ap.add_argument("--start", default="2024-01-01", help="起始日期 YYYY-MM-DD")
    ap.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"), help="结束日期 YYYY-MM-DD")
    ap.add_argument("--output-dir", default=".", help="输出目录")
    ap.add_argument("--freq", default="weekly", choices=["weekly", "monthly"], help="采样频率")
    ap.add_argument("--data-only", action="store_true", help="仅输出数据，不画图")
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"=== 获取全宽基 ETF 份额 ({args.start} ~ {args.end}, {args.freq}) ===")
    data = fetch_shares(args.start, args.end, args.freq)
    if not data:
        print("未获取到任何数据"); sys.exit(1)

    json_path = os.path.join(args.output_dir, "national_team_position.json")
    with open(json_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"数据已保存: {json_path}")
    summarize(data)

    if args.data_only:
        return

    prices = fetch_index_prices(args.start)
    make_charts(data, prices, args.output_dir)
    print("\n完成")


if __name__ == "__main__":
    main()
