from __future__ import annotations

import calendar
import json
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from app.storage import gsheets_append, gsheets_fetch_recent_results, utc_now_iso
from app.compatibility import compute_compatibility

APP_VERSION = "1.1.0"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@dataclass
class Option:
    yazi: str
    etki: Dict[str, int]
    mini_sahne: str


@dataclass
class Question:
    soru: str
    options: List[Option]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_questions_for_lang(lang: str) -> List[Question]:
    lang = (lang or "TR").upper()
    candidates = {
        "TR": [DATA_DIR / "questions_tr.json", DATA_DIR / "questions.json"],
        "EN": [DATA_DIR / "questions_en.json"],
    }.get(lang, [DATA_DIR / "questions_tr.json", DATA_DIR / "questions.json"])

    file_path = None
    for p in candidates:
        if p.exists():
            file_path = p
            break
    if not file_path:
        raise FileNotFoundError("data/ altında questions_tr.json ve/veya questions_en.json olmalı.")

    raw = _read_json(file_path)
    if not isinstance(raw, list):
        raise ValueError("Soru JSON formatı list olmalı.")

    out: List[Question] = []
    for item in raw:
        if not isinstance(item, dict):
            continue

        soru = item.get("soru") or item.get("question") or item.get("q")
        secenekler = item.get("secenekler") or item.get("options") or item.get("a")

        if not isinstance(soru, str) or not isinstance(secenekler, list):
            continue

        opts: List[Option] = []
        for opt in secenekler:
            if not isinstance(opt, dict):
                continue
            yazi = opt.get("yazi") or opt.get("text") or opt.get("label")
            etki = opt.get("etki") or opt.get("impact") or {}
            mini = opt.get("mini_sahne") or opt.get("mini_scene") or opt.get("scene") or ""
            if not isinstance(yazi, str):
                continue
            if not isinstance(etki, dict):
                etki = {}
            safe_etki: Dict[str, int] = {}
            for k, v in etki.items():
                try:
                    safe_etki[str(k)] = int(v)
                except Exception:
                    continue
            opts.append(Option(yazi=yazi, etki=safe_etki, mini_sahne=str(mini)))

        if opts:
            out.append(Question(soru=soru, options=opts))

    if not out:
        raise ValueError("Sorular parse edilemedi.")
    return out


def ensure_session() -> None:
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    if "profile_id" not in st.session_state:
        st.session_state["profile_id"] = str(uuid.uuid4())

    if "lang" not in st.session_state:
        st.session_state["lang"] = "TR"
    if "debug" not in st.session_state:
        st.session_state["debug"] = False

    if "step" not in st.session_state:
        st.session_state["step"] = "intro"
    if "q_index" not in st.session_state:
        st.session_state["q_index"] = 0
    if "answers" not in st.session_state:
        st.session_state["answers"] = {}

    if "name" not in st.session_state:
        st.session_state["name"] = ""
    if "dob" not in st.session_state:
        st.session_state["dob"] = {"year": 1990, "month": 1, "day": 1}

    if "last_sheets_status" not in st.session_state:
        st.session_state["last_sheets_status"] = ""

    if "_app_opened_logged" not in st.session_state:
        st.session_state["_app_opened_logged"] = False


def show_sheets_status(ok: bool, msg: str) -> None:
    if st.session_state.get("debug"):
        if ok:
            st.success(msg)
        else:
            st.error(f"Sheets ERROR: {msg}")
        return
    if not ok:
        st.error(f"Sheets ERROR: {msg}")


def log_event(event_name: str, payload: Optional[Dict[str, Any]] = None) -> None:
    row = {
        "ts_utc": utc_now_iso(),
        "session_id": st.session_state["session_id"],
        "profile_id": st.session_state["profile_id"],
        "event_name": event_name,
        "event_json": payload or {},
        "app_version": APP_VERSION,
        "source": "cloud_or_local",
    }
    ok, msg = gsheets_append("events", row)
    st.session_state["last_sheets_status"] = msg
    show_sheets_status(ok, msg)


def write_result(result: Dict[str, Any]) -> None:
    row = {
        "ts_utc": utc_now_iso(),
        "session_id": st.session_state["session_id"],
        "profile_id": st.session_state["profile_id"],
        "name": result.get("name", ""),
        "zodiac": result.get("zodiac", ""),
        "dominant": result.get("dominant", ""),
        "score": result.get("score", 0),
        "result_json": result,
        "app_version": APP_VERSION,
        "source": "cloud_or_local",
    }
    ok, msg = gsheets_append("results", row)
    st.session_state["last_sheets_status"] = msg
    show_sheets_status(ok, msg)


def zodiac_from_date(d: date) -> str:
    md = (d.month, d.day)
    if (md >= (3, 21)) and (md <= (4, 19)):
        return "Koç"
    if (md >= (4, 20)) and (md <= (5, 20)):
        return "Boğa"
    if (md >= (5, 21)) and (md <= (6, 20)):
        return "İkizler"
    if (md >= (6, 21)) and (md <= (7, 22)):
        return "Yengeç"
    if (md >= (7, 23)) and (md <= (8, 22)):
        return "Aslan"
    if (md >= (8, 23)) and (md <= (9, 22)):
        return "Başak"
    if (md >= (9, 23)) and (md <= (10, 22)):
        return "Terazi"
    if (md >= (10, 23)) and (md <= (11, 21)):
        return "Akrep"
    if (md >= (11, 22)) and (md <= (12, 21)):
        return "Yay"
    if (md >= (12, 22)) or (md <= (1, 19)):
        return "Oğlak"
    if (md >= (1, 20)) and (md <= (2, 18)):
        return "Kova"
    return "Balık"


def compute_scores(answers: Dict[int, Dict[str, Any]]) -> Dict[str, int]:
    totals: Dict[str, int] = {}
    for _, opt in answers.items():
        etki = opt.get("etki", {})
        if isinstance(etki, dict):
            for k, v in etki.items():
                try:
                    totals[k] = totals.get(k, 0) + int(v)
                except Exception:
                    continue
    return totals


def dominant_trait(totals: Dict[str, int]) -> Tuple[str, int]:
    if not totals:
        return ("", 0)
    k, v = max(totals.items(), key=lambda x: x[1])
    return (k, int(v))


ARCHETYPE = {
    "kontrol": {
        "title": "Planlı Stratejist",
        "icon": "🧭",
        "strength": "Belirsizlikte bile yapı kurup ilerlersin.",
        "shadow": "Aşırı kontrol, fırsatları geciktirebilir.",
        "micro": "Bugün bir işi %80’de bırak ve gönder.",
    },
    "merak": {
        "title": "Keskin Kaşif",
        "icon": "🔎",
        "strength": "İpucu kovalarsın. Yeni bağlantılar kurarsın.",
        "shadow": "Fazla seçenek kararı geciktirebilir.",
        "micro": "10 dk araştır, sonra tek hamle seç ve uygula.",
    },
    "cesaret": {
        "title": "Atılgan Öncü",
        "icon": "⚡",
        "strength": "Aksiyon alıp momentum yaratırsın.",
        "shadow": "Plansız risk maliyet çıkarabilir.",
        "micro": "En kötü senaryoyu 1 cümlede yaz. Katlanıyorsan devam.",
    },
    "empati": {
        "title": "Sakin Şifacı",
        "icon": "🤝",
        "strength": "Bağ kurar, güven üretirsin.",
        "shadow": "Sınır koymazsan tükenirsin.",
        "micro": "Yardım edeceksen süre koy: 15 dk.",
    },
}


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .iz-hero {
            border-radius: 18px;
            padding: 18px 18px;
            background: linear-gradient(90deg, rgba(176,196,255,.22), rgba(140,255,219,.18));
            border: 1px solid rgba(0,0,0,.06);
        }
        .iz-muted { color: rgba(0,0,0,.60); }
        .iz-q {
            border: 1px solid rgba(0,0,0,.08);
            border-radius: 16px;
            padding: 16px 16px;
            background: rgba(255,255,255,.72);
        }
        .iz-card {
            border: 1px solid rgba(0,0,0,.10);
            border-radius: 14px;
            padding: 12px 14px;
            background: rgba(255,255,255,.9);
            margin: 10px 0;
        }
        div[role="radiogroup"] label {
            border: 1px solid rgba(0,0,0,.10);
            padding: 14px 14px;
            border-radius: 14px;
            margin: 10px 0px;
            background: rgba(255,255,255,.90);
            cursor: pointer;
        }
        div[role="radiogroup"] label:hover {
            border-color: rgba(30,144,255,.55);
            background: rgba(30,144,255,.06);
        }
        div[role="radiogroup"] input[type="radio"] { display: none !important; }
        div[role="radiogroup"] label:has(input:checked) {
            border-color: rgba(30,144,255,.95);
            box-shadow: 0 6px 16px rgba(30,144,255,.12);
            background: rgba(30,144,255,.08);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def dob_picker() -> date:
    years = list(range(1950, date.today().year + 1))
    years.reverse()

    y = st.session_state["dob"]["year"]
    m = st.session_state["dob"]["month"]
    d = st.session_state["dob"]["day"]

    coly, colm, cold = st.columns([1, 1, 1])
    with coly:
        year = st.selectbox("Yıl", years, index=years.index(y) if y in years else 0, key="dob_year")
    with colm:
        month = st.selectbox("Ay", list(range(1, 13)), index=m - 1, key="dob_month")

    max_day = calendar.monthrange(int(year), int(month))[1]
    days = list(range(1, max_day + 1))
    safe_day = d if (1 <= int(d) <= max_day) else 1

    with cold:
        day = st.selectbox("Gün", days, index=days.index(int(safe_day)), key="dob_day")

    st.session_state["dob"] = {"year": int(year), "month": int(month), "day": int(day)}
    return date(int(year), int(month), int(day))


def run_app() -> None:
    st.set_page_config(page_title="IZ", layout="wide")
    ensure_session()
    inject_css()

    with st.sidebar:
        st.markdown("### IZ")
        st.session_state["lang"] = st.selectbox(
            "Dil", ["TR", "EN"], index=0 if st.session_state["lang"] == "TR" else 1
        )
        st.session_state["debug"] = st.toggle("DEBUG", value=st.session_state.get("debug", False))
        if st.session_state.get("debug") and st.session_state.get("last_sheets_status"):
            st.caption(st.session_state["last_sheets_status"])

    if not st.session_state["_app_opened_logged"]:
        log_event("app_opened", {"path": "main"})
        st.session_state["_app_opened_logged"] = True

    questions = load_questions_for_lang(st.session_state["lang"])

    st.markdown(
        """
        <div class="iz-hero">
          <div style="font-size:28px;font-weight:800;">🧭 IZ</div>
          <div class="iz-muted">Test bittiğinde sana benzer insanlarla uyumu gösterir.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    if st.session_state["step"] == "intro":
        c1, c2 = st.columns([1, 1])
        with c1:
            st.session_state["name"] = st.text_input("İsim", value=st.session_state.get("name", ""))
        with c2:
            st.markdown("**Doğum tarihi**")
            dob = dob_picker()

        z = zodiac_from_date(dob)
        st.caption(f"Burcun: **{z}**")

        if st.button("Başla", type="primary"):
            st.session_state["step"] = "quiz"
            st.session_state["q_index"] = 0
            st.session_state["answers"] = {}
            log_event("intro_completed", {"name": st.session_state["name"], "dob": dob.isoformat(), "zodiac": z})
            st.rerun()
        return

    if st.session_state["step"] == "quiz":
        total = len(questions)
        qi = int(st.session_state["q_index"])
        qi = max(0, min(qi, total - 1))

        st.write(f"Soru **{qi + 1} / {total}**")
        st.progress((qi + 1) / total)

        q = questions[qi]
        st.markdown('<div class="iz-q">', unsafe_allow_html=True)
        st.markdown(f"### {q.soru}")

        labels = [o.yazi for o in q.options]
        prev = st.session_state["answers"].get(qi, {}).get("yazi")
        index = labels.index(prev) if prev in labels else None

        picked = st.radio(
            label="",
            options=labels,
            index=index,
            key=f"pick_{qi}",
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if picked is not None and picked != prev:
            opt = next(o for o in q.options if o.yazi == picked)
            st.session_state["answers"][qi] = {"yazi": opt.yazi, "etki": opt.etki, "mini_sahne": opt.mini_sahne}
            log_event("question_answered", {"qi": qi, "text": opt.yazi, "mini_sahne": opt.mini_sahne})

            if qi < total - 1:
                st.session_state["q_index"] = qi + 1
                st.rerun()
            st.session_state["step"] = "result"
            st.rerun()

        if st.button("Geri", disabled=(qi == 0)):
            st.session_state["q_index"] = max(0, qi - 1)
            st.rerun()
        return

    if st.session_state["step"] == "result":
        dob_state = st.session_state.get("dob", {"year": 1990, "month": 1, "day": 1})
        dob = date(int(dob_state["year"]), int(dob_state["month"]), int(dob_state["day"]))
        z = zodiac_from_date(dob)

        answers = st.session_state.get("answers", {})
        totals = compute_scores(answers)
        dom_key, dom_score = dominant_trait(totals)
        profile = ARCHETYPE.get(dom_key, ARCHETYPE["merak"])

        result_payload = {
            "name": st.session_state.get("name", ""),
            "dob": dob.isoformat(),
            "zodiac": z,
            "dominant": dom_key,
            "score": dom_score,
            "totals": totals,
            "answers": answers,
        }

        log_event("result_shown", {"dominant": dom_key, "score": dom_score, "zodiac": z})
        write_result(result_payload)

        st.markdown("## Sonuç")
        st.markdown(f"### {profile['icon']} {profile['title']}")
        st.caption(f"Burcun: **{z}**")
        st.markdown("**Güçlü yan:**")
        st.write(profile["strength"])
        st.markdown("**Kör nokta:**")
        st.write(profile["shadow"])
        st.markdown("**Bugünlük mikro hamle:**")
        st.info(profile["micro"])

        st.divider()
        st.markdown("## 🤝 Seninle en uyumlu kişiler")

        ok, recent, msg = gsheets_fetch_recent_results(limit=60, max_rows_scan=1500)
        if not ok:
            st.error(f"Uyum listesi çekilemedi: {msg}")
        else:
            me_id = st.session_state["profile_id"]
            candidates = []
            for r in recent:
                pid = r.get("profile_id", "")
                if not pid or pid == me_id:
                    continue
                payload = r.get("_result", {}) or {}
                name = payload.get("name") or r.get("name") or "Anonim"
                zodiac_b = payload.get("zodiac") or r.get("zodiac") or ""
                totals_b = payload.get("totals") or {}
                if not isinstance(totals_b, dict):
                    continue

                score, label, br = compute_compatibility(totals, totals_b, z, zodiac_b)
                candidates.append(
                    {
                        "profile_id": pid,
                        "name": name,
                        "zodiac": zodiac_b,
                        "score": score,
                        "label": label,
                        "sim_pct": br["sim_pct"],
                        "element_bonus": br["element_bonus"],
                        "variety_bonus": br["variety_bonus"],
                        "dominant": payload.get("dominant") or r.get("dominant") or "",
                    }
                )

            candidates.sort(key=lambda x: x["score"], reverse=True)
            top = candidates[:5]

            if not top:
                st.info("Henüz yeterli kişi yok. 2-3 kişi daha test çözünce liste dolacak.")
            else:
                for m in top:
                    note = (
                        f"Benzerlik %{m['sim_pct']} • "
                        f"Element bonusu +{m['element_bonus']} • "
                        f"Çeşitlilik +{m['variety_bonus']}"
                    )
                    st.markdown(
                        f"""
                        <div class="iz-card">
                          <div style="font-size:18px;font-weight:800;">
                            {m['name']} <span style="font-weight:600;opacity:.7;">({m['zodiac']})</span>
                          </div>
                          <div style="margin-top:6px;">
                            <b>{m['score']}/100</b> · {m['label']}
                          </div>
                          <div style="margin-top:6px;opacity:.75;">
                            {note}
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                log_event("compatibility_list_shown", {"shown": len(top)})

        if st.session_state.get("debug"):
            st.json(result_payload)

        if st.button("Başa dön"):
            log_event("reset_clicked", {})
            keep_lang = st.session_state.get("lang", "TR")
            keep_debug = st.session_state.get("debug", False)
            st.session_state.clear()
            ensure_session()
            st.session_state["lang"] = keep_lang
            st.session_state["debug"] = keep_debug
            st.session_state["step"] = "intro"
            st.rerun()
        return


if __name__ == "__main__":
    run_app()
