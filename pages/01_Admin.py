import json
from pathlib import Path
from collections import Counter
from datetime import datetime

import streamlit as st

# Optional: pandas varsa güzel tablo/graph; yoksa yine çalışır
try:
    import pandas as pd
except Exception:
    pd = None


def _parse_dt(s: str):
    if not s:
        return None
    try:
        # "2026-01-13T06:38:00" gibi
        return datetime.fromisoformat(s.replace("Z", ""))
    except Exception:
        return None


def find_log_path() -> Path | None:
    """
    Log dosyası bazen repo root'ta, bazen app/ içinde.
    İkisini de dene.
    """
    root = Path(__file__).resolve().parents[1]
    candidates = [
        root / "results_log.jsonl",
        root / "app" / "results_log.jsonl",
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def read_jsonl(path: Path):
    records = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                # bozuk satır varsa geç
                continue
    return records


st.set_page_config(page_title="Admin – Life Path Test", layout="wide")
st.title("🛠️ Admin / Analytics (v0)")

# Basit koruma (opsiyonel):
# Streamlit Cloud'da Settings > Secrets kısmına ADMIN_PASSWORD koyarsan çalışır.
need_pw = "ADMIN_PASSWORD" in st.secrets
if need_pw:
    pw = st.text_input("Admin password", type="password")
    if pw != st.secrets["ADMIN_PASSWORD"]:
        st.info("Password required.")
        st.stop()
else:
    st.caption("No admin password set (optional). Add ADMIN_PASSWORD to Streamlit secrets to lock this page.")

log_path = find_log_path()
if not log_path:
    st.error("No results_log.jsonl found. Tried: repo root and app/ folder.")
    st.stop()

records = read_jsonl(log_path)
st.caption(f"Log file: `{log_path}` | records: **{len(records)}**")

if not records:
    st.warning("No records yet. Run the test a few times to generate data.")
    st.stop()

# --- Basic metrics ---
total = len(records)

langs = []
baskin = []
ikincil = []
dates = []

for r in records:
    langs.append(r.get("lang") or r.get("language") or "tr")  # bazı eski kayıtlar lang içermeyebilir
    baskin.append(r.get("baskin") or "—")
    ikincil.append(r.get("ikincil") or "—")
    dt = _parse_dt(r.get("timestamp"))
    if dt:
        dates.append(dt.date())

lang_counts = Counter(langs)
baskin_counts = Counter(baskin)
ikincil_counts = Counter(ikincil)
daily_counts = Counter(dates) if dates else Counter()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Completed sessions", total)
c2.metric("TR", lang_counts.get("tr", 0))
c3.metric("EN", lang_counts.get("en", 0))
c4.metric("Other/Unknown", total - lang_counts.get("tr", 0) - lang_counts.get("en", 0))

st.divider()

# --- Charts / tables ---
left, right = st.columns(2)

with left:
    st.subheader("Primary archetype distribution")
    items = sorted(baskin_counts.items(), key=lambda x: x[1], reverse=True)
    if pd:
        df = pd.DataFrame(items, columns=["primary", "count"])
        st.bar_chart(df.set_index("primary"))
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.write(items)

with right:
    st.subheader("Secondary archetype distribution")
    items2 = sorted(ikincil_counts.items(), key=lambda x: x[1], reverse=True)
    if pd:
        df2 = pd.DataFrame(items2, columns=["secondary", "count"])
        st.bar_chart(df2.set_index("secondary"))
        st.dataframe(df2, use_container_width=True, hide_index=True)
    else:
        st.write(items2)

st.divider()

st.subheader("Daily completions")
if daily_counts:
    daily_items = sorted(daily_counts.items(), key=lambda x: x[0])
    if pd:
        dfd = pd.DataFrame(daily_items, columns=["date", "count"])
        dfd["date"] = pd.to_datetime(dfd["date"])
        st.line_chart(dfd.set_index("date"))
        st.dataframe(dfd, use_container_width=True, hide_index=True)
    else:
        st.write(daily_items)
else:
    st.caption("No timestamps parsed.")

st.divider()

st.subheader("Latest records (last 20)")
latest = records[-20:]
latest_view = []
for r in reversed(latest):
    latest_view.append({
        "timestamp": r.get("timestamp"),
        "lang": r.get("lang") or r.get("language") or "tr",
        "isim": r.get("isim"),
        "baskin": r.get("baskin"),
        "ikincil": r.get("ikincil"),
        "paylas": r.get("paylas"),
        "profile_id": r.get("profile_id"),
    })

if pd:
    st.dataframe(pd.DataFrame(latest_view), use_container_width=True, hide_index=True)
else:
    st.write(latest_view)
