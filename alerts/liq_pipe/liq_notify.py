"""美元水管流動性：推播訊息組裝與派發（v2 兩階推播）。

liq_eval.py 偵測到行動級／解除事件後呼叫這裡：
- format_action()、format_recovery()：組繁體中文訊息
- dispatch()：live 模式才真的發。有 TELEGRAM_BOT_TOKEN 與 TELEGRAM_CHAT_ID 就直接呼叫 Telegram Bot API；
  沒有（或發送失敗）就把訊息原樣退回，由 liq_eval 放進 cron 的 result.json message，讓排程器代發，
  所以不會因為缺金鑰而吞掉警報。

資訊級事件不走這裡，只進 alerts.jsonl 與每日摘要。
"""
import json
import os
import urllib.parse
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
STATS_PATH = os.path.join(ROOT, "analysis", "美元水管流動性", "backtest", "utility_stats.json")
LIGHT_ZH = {0: ("🟢", "綠燈 / Green"), 1: ("🟡", "黃燈 / Yellow"), 2: ("🟠", "橘燈 / Orange"), 3: ("🔴", "紅燈 / Red")}
SEP = "-" * 41

GUIDE = {
    "FUNDING_LIQUIDATION_TYPE1": ["立即暫停加開多頭槓桿與新倉", "檢查融資保證金維護率與衍生品抵押品折價",
                                  "嚴防後續流動性螺旋下殺"],
    "FUNDING_CRISIS_TYPE2": ["國債同遭拋售：連避險資產都在被賣來換現金，優先確保現金與保證金", "暫停新倉，降低槓桿",
                             "留意 Fed 流動性工具（SRF、回購、換匯額度）是否啟動"],
    "UPSTREAM_FUNDING_ONLY": ["融資利差已達嚴重等級，但股金尚未同跌", "檢查槓桿與保證金緩衝，暫緩加碼",
                              "觀察是否擴散到股金同跌"],
}


def _fmt(v, unit="", sign=False, nd=1):
    if v is None or v != v:
        return "n/a"
    return f"{v:+.{nd}f}{unit}" if sign else f"{v:.{nd}f}{unit}"


def _time_line(ts):
    t = pd.Timestamp(ts) if ts is not None else pd.Timestamp.now(tz="America/New_York")
    if t.tzinfo is None:
        t = t.tz_localize("America/New_York")
    return f"時間：{t.tz_convert('America/New_York'):%Y-%m-%d %H:%M %Z}"


def load_utility_stats(path=STATS_PATH):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def format_action(ev, vals, ts=None):
    """行動級警報。ev：rules.replay_episodes 的事件；vals：事件當日的指標值 dict。"""
    emoji, name = LIGHT_ZH[ev["light"]]
    up = "升級通知" if ev["kind"] == "escalation" else "行動級警報"
    lines = [f"🚨【美元水管流動性 ‧ {up}】(燈號：{name})", SEP,
             f"• 分類判定：{ev['label']} ({ev['category']})",
             "• 核心指標：",
             f"  - SOFR−IORB: {_fmt(vals.get('s_iorb'), ' bp', True)}（燈號已連續 {ev.get('consecutive_days', '?')} 日橘燈以上）",
             f"  - SOFR−TGCR: {_fmt(vals.get('s_tgcr'), ' bp', True)}",
             f"  - SRF 用量: {_fmt(vals.get('srf_bn'), ' B', nd=2)}｜ON RRP: {_fmt(vals.get('rrp_bn'), ' B')}",
             f"  - 跨資產: z_SPY {_fmt(vals.get('z_spy'), '', True, 2)}、z_GLD {_fmt(vals.get('z_gld'), '', True, 2)}、"
             f"10Y 日變動 {_fmt(vals.get('d10'), ' bp', True, 0)}",
             "• 投資應對指引："]
    lines += [f"  {i}. {g}" for i, g in enumerate(GUIDE.get(ev["category"], GUIDE["UPSTREAM_FUNDING_ONLY"]), 1)]
    lines += [SEP, f"訊號日：{ev['date']}（episode 起於 {ev['episode_start']}）", _time_line(ts)]
    return "\n".join(lines)


def format_recovery(ev, vals, stats=None, ts=None):
    """解除通知。stats：backtest/utility_stats.json（缺檔就省略歷史統計）。"""
    prior = LIGHT_ZH[ev["prior_max_light"]][1].split(" / ")[0]
    lines = [f"🟢【美元水管流動性 ‧ 危機解除通知】(燈號：{LIGHT_ZH[0][1]})", SEP,
             f"• 狀態變更：最高【{prior}】的警戒共 {ev['episode_days']} 個交易日，"
             f"自 {ev['recovery_date']} 降回【綠燈】並連續維持，正式確認解除",
             f"• 解除指標：SOFR−IORB {_fmt(vals.get('s_iorb'), ' bp', True)}｜SRF {_fmt(vals.get('srf_bn'), ' B', nd=2)}"]
    g = (stats or {}).get("groups", {}).get("recovery_action", {}).get("assets", {})
    if g.get("SPY") and g.get("GLD") and g["SPY"].get("n_T+20"):
        lines.append(f"• 歷史統計（{stats['period']}，{g['SPY']['n']} 次發過行動級的 episode 解除後 20 個交易日）：")
        lines.append(f"  - SPY 平均 {g['SPY']['T+20']:+.1%}，GLD 平均 {g['GLD']['T+20']:+.1%}"
                     "（樣本少、離散大，只當參考）")
    lines += ["• 投資應對指引：", "  - 流動性最緊迫階段已過，避免在低點恐慌拋售持股，留意流動性修復行情",
              SEP, f"確認日：{ev['date']}", _time_line(ts)]
    return "\n".join(lines)


def send_telegram(text):
    """成功回 True。沒設金鑰回 False（呼叫端要退回給 cron 代發）。"""
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode()).get("ok", False)


def dispatch(messages, live):
    """messages：[{"key", "text"}]。回傳 {"sent": [key], "deferred": [msg], "errors": {key: 原因}}。
    dry-run（live=False）全部不發、不退回，只列在 "dry" 裡讓呼叫端記 log。"""
    out = {"sent": [], "deferred": [], "dry": [], "errors": {}}
    for m in messages:
        if not live:
            out["dry"].append(m["key"])
            continue
        try:
            if send_telegram(m["text"]):
                out["sent"].append(m["key"])
                continue
        except Exception as e:  # noqa: BLE001 — 發送失敗不能讓整個判定中斷
            out["errors"][m["key"]] = f"{type(e).__name__}: {str(e)[:120]}"
        out["deferred"].append(m)
    return out
