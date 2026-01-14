# app/main.py
import streamlit as st
import random
from pathlib import Path
from datetime import datetime, date
import uuid

from app.compatibility import compute_compatibility_score
from app.ui_components import render_match_card
from app.utils import load_json
from app.storage import (
    append_unique_by_profile_id,
    ensure_unique_profile_id,
    find_by_profile_id,
    read_jsonl,
    log_event,  # TEK KAYNAK
)

# ------------------------------------------------------------
# Streamlit kuralı: set_page_config dosyanın EN ÜSTÜNDE olmalı
# ------------------------------------------------------------
st.set_page_config(
    page_title="IZ",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items={"Get help": None, "Report a bug": None, "About": None},
)

# Repo root
REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_LOG_PATH = REPO_ROOT / "results_log.jsonl"
EVENTS_LOG_PATH = REPO_ROOT / "events_log.jsonl"
DATA_DIR = REPO_ROOT / "data"


# -------------------------
# I18N
# -------------------------
TEXT = {
    "tr": {
        "page_title": "IZ",
        "title": "🔮 IZ",
        "subtitle": "Seçim yap. Hikaye ilerlesin. En sonda ‘izini’ okuyayım.",
        "sidebar_title": "Ayarlar",
        "language": "Dil",
        "debug": "Debug modu",
        "reset": "🔁 Sıfırla / Yeniden Başla",
        "progress": "İlerleme",
        "name_optional": "Adın ne? (opsiyonel)",
        "show_name_in_matches": "Eşleşme listesinde ismim görünsün",
        "astro_mode": "Astro modu (burç atmosferi ekle)",
        "day": "Gün",
        "month": "Ay",
        "year": "Yıl",
        "atmosphere": "🔭 Atmosfer",
        "astro_off": "Astro modu kapalı: Açarsan burç atmosferini de eklerim.",
        "share_title": "🔗 Paylaş",
        "share_button": "Link oluştur",
        # NOT: URL'yi artık otomatik değiştirmiyoruz. Linki aşağıdan kopyalatıyoruz.
        "share_hint": "Linki aşağıdan kopyalayıp paylaş. (URL otomatik güncellenmez.)",
        "shared_caption": "Paylaşılan sonuç görüntüleniyor.",
        "shared_not_found": "Bu id ile kayıt bulunamadı. Yeni test başlatılıyor.",
        "take_test_too": "✅ Testi ben de çözmek istiyorum",
        "score_summary": "📊 Puan Özeti",
        "no_log": "Günlük yok.",
        "log_title": "🎬 Seçim Günlüğü",
        "your_profile": "🧍 Senin Profilin",
        "you_label": "Sen",
        "sign": "Burç",
        "travelers_like_you": "🧩 Benim gibi yolcular",
        "best_matches": "💘 En iyi eşleşmelerin",
        "other_matches": "🎯 Diğer eşleşmeler",
        "not_enough_data": "Henüz yeterli veri yok.",
        "anonymous": "Anonim Yolcu",
        "primary": "Baskın",
        "secondary": "Destek",
        "report_copy": "📋 Raporu Kopyala",
        "copy_hint": "Kopyala (Cmd/Ctrl + C):",
        "journal_scene": "🎬 Seçim Günlüğün (sahne sahne)",
        "life_path_for": "📌 {name} için İz Okuması",
    },
    "en": {
        "page_title": "IZ",
        "title": "🔮 IZ",
        "subtitle": "Make choices. Let the story unfold. At the end, I’ll read your trace.",
        "sidebar_title": "Settings",
        "language": "Language",
        "debug": "Debug mode",
        "reset": "🔁 Reset / Start Over",
        "progress": "Progress",
        "name_optional": "What’s your name? (optional)",
        "show_name_in_matches": "Show my name in match list",
        "astro_mode": "Astro mode (add zodiac flavor)",
        "day": "Day",
        "month": "Month",
        "year": "Year",
        "atmosphere": "🔭 Atmosphere",
        "astro_off": "Astro mode is off. Turn it on to add zodiac flavor.",
        "share_title": "🔗 Share",
        "share_button": "Create link",
        "share_hint": "Copy the link below and share it. (URL won’t auto-update.)",
        "shared_caption": "Showing a shared result.",
        "shared_not_found": "No record found for this id. Starting a new test.",
        "take_test_too": "✅ I want to take the test too",
        "score_summary": "📊 Score Summary",
        "no_log": "No log yet.",
        "log_title": "🎬 Choice Log",
        "your_profile": "🧍 Your Profile",
        "you_label": "You",
        "sign": "Sign",
        "travelers_like_you": "🧩 Travelers like you",
        "best_matches": "💘 Your best matches",
        "other_matches": "🎯 Other matches",
        "not_enough_data": "Not enough data yet.",
        "anonymous": "Anonymous Traveler",
        "primary": "Primary",
        "secondary": "Secondary",
        "report_copy": "📋 Copy Report",
        "copy_hint": "Copy (Cmd/Ctrl + C):",
        "journal_scene": "🎬 Your choice log (scene by scene)",
        "life_path_for": "📌 {name}'s Trace Reading",
    },
}

MONTHS = {
    "tr": ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
}


def t(lang: str, key: str) -> str:
    lang = lang if lang in TEXT else "tr"
    return TEXT[lang].get(key, TEXT["tr"].get(key, key))


# -------------------------
# Questions
# -------------------------
def parse_questions(raw):
    questions = []
    for item in raw:
        question = item.get("soru") or item.get("question")
        opts = []
        for s in item.get("secenekler", item.get("options", [])):
            text = s.get("yazi") or s.get("text")
            effect = s.get("etki") or s.get("effect") or {}
            mini = s.get("mini_sahne") or s.get("mini_scene") or ""
            opts.append((text, effect, mini))
        questions.append((question, opts))
    return questions


@st.cache_data(show_spinner=False)
def get_questions(lang: str):
    lang = lang if lang in ("tr", "en") else "tr"
    primary = DATA_DIR / ("questions_en.json" if lang == "en" else "questions_tr.json")
    fallback = DATA_DIR / "questions.json"
    path = primary if primary.exists() else fallback
    raw = load_json(str(path))
    return parse_questions(raw)


# -------------------------
# Content
# -------------------------
ARSHETIPLER = {
    "merak": {
        "icon": "🧭",
        "tr": {"name": "Kaşif", "motto": "Cevap değil, doğru soru güç verir.", "desc": "Yeni fikirlere hızlı açılırsın. Bilmediğin yere gitmek seni korkutmaz; merakın seni taşır."},
        "en": {"name": "Explorer", "motto": "Not answers, the right questions give power.", "desc": "You open fast to new ideas. The unknown doesn’t scare you; curiosity carries you."},
        "strengths_tr": ["Öğrenme hızı", "Yaratıcı problem çözme", "Fırsatları görme"],
        "risks_tr": ["Dağılma", "Yarım bırakma", "Sürekli seçenek arama"],
        "strengths_en": ["Fast learning", "Creative problem solving", "Spotting opportunities"],
        "risks_en": ["Scattering", "Not finishing", "Endless options"],
    },
    "cesaret": {
        "icon": "⚔️",
        "tr": {"name": "Savaşçı", "motto": "Korku var diye durmam.", "desc": "Risk alabilirsin. Karar anında beklemek yerine hamle yapmayı seçersin."},
        "en": {"name": "Warrior", "motto": "I don’t stop just because fear exists.", "desc": "You can take risks. In decision moments, you prefer action over waiting."},
        "strengths_tr": ["Hızlı aksiyon", "Liderlik", "Zor anlarda soğukkanlılık"],
        "risks_tr": ["Acelecilik", "Gereksiz çatışma", "Sabırsızlık"],
        "strengths_en": ["Fast action", "Leadership", "Calm under pressure"],
        "risks_en": ["Rushing", "Unnecessary conflict", "Impatience"],
    },
    "kontrol": {
        "icon": "🧠",
        "tr": {"name": "Stratejist", "motto": "Plan yapan kazanır.", "desc": "Sistem kurar, işi ölçer, kontrol edersin. Kaosu azaltırsın, düzen kurarsın."},
        "en": {"name": "Strategist", "motto": "Those who plan, win.", "desc": "You build systems, measure, and control. You reduce chaos and create order."},
        "strengths_tr": ["Disiplin", "Planlama", "Süreç yönetimi"],
        "risks_tr": ["Aşırı kontrol", "Esneklik kaybı", "Kendini yıpratma"],
        "strengths_en": ["Discipline", "Planning", "Process management"],
        "risks_en": ["Over-control", "Loss of flexibility", "Self-wear"],
    },
    "empati": {
        "icon": "🌿",
        "tr": {"name": "Şifacı", "motto": "İnsanı anlamadan hayat anlaşılmaz.", "desc": "İlişki yönetimi güçlüdür. Ortamı okur, insanları hissedersin."},
        "en": {"name": "Healer", "motto": "Without understanding people, life stays unread.", "desc": "You manage relationships well. You read the room and feel people."},
        "strengths_tr": ["İletişim", "Güven inşası", "Duygusal zekâ"],
        "risks_tr": ["Fazla yük alma", "Sınır koyamama", "Herkesi memnun etmeye çalışma"],
        "strengths_en": ["Communication", "Building trust", "Emotional intelligence"],
        "risks_en": ["Carrying too much", "Weak boundaries", "People-pleasing"],
    },
}

ARCHETYPE_MAP = {"merak": "kasif", "cesaret": "savasci", "kontrol": "stratejist", "empati": "sifaci"}

UYUM_PROFILI = {
    "merak": {"iyi": ["empati", "kontrol"], "zor": ["cesaret"]},
    "cesaret": {"iyi": ["kontrol", "merak"], "zor": ["empati"]},
    "kontrol": {"iyi": ["cesaret", "empati"], "zor": ["merak"]},
    "empati": {"iyi": ["merak", "kontrol"], "zor": ["cesaret"]},
}

SIGNS_TR = ["Koç","Boğa","İkizler","Yengeç","Aslan","Başak","Terazi","Akrep","Yay","Oğlak","Kova","Balık"]
SIGNS_EN = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
SIGN_MAP_TR_EN = dict(zip(SIGNS_TR, SIGNS_EN))

BURC_TEMALARI_TR = {
    "Koç": "Hız ve hamle haftası: cesaret tetikte, sabırsızlığa dikkat.",
    "Boğa": "İstikrar ve güven arayışı: yavaş ama sağlam ilerle.",
    "İkizler": "Zihin açılıyor: merak artar, dağılmaya dikkat.",
    "Yengeç": "Duygu dalgaları yükselir: bağ kur, sınırlarını koru.",
    "Aslan": "Sahne senin: görünür ol, ego tuzağına düşme.",
    "Başak": "Düzen ve verim: sistemi iyileştir, mükemmeliyetçiliği bırak.",
    "Terazi": "Denge sınavı: karar gecikmesin, netlik kazan.",
    "Akrep": "Derinleşme haftası: sezgi güçlü, kontrol takıntısına dikkat.",
    "Yay": "Ufuk genişler: yeni yol çağırır, yarım bırakma risk.",
    "Oğlak": "Hedef ve disiplin: plan kazanır, katılaşma riski var.",
    "Kova": "Farklı düşün: kalıpları kır, kopukluk yaratma.",
    "Balık": "Sezgi ve hayal: ilham yüksek, gerçeklikten kaçma.",
}
BURC_TEMALARI_EN = {
    "Aries": "Speed and action week: courage is up, watch impatience.",
    "Taurus": "Stability and safety: slow, steady progress wins.",
    "Gemini": "Mind opens: curiosity rises, avoid scattering.",
    "Cancer": "Emotional tides: connect, but keep boundaries.",
    "Leo": "Spotlight time: be visible, avoid ego traps.",
    "Virgo": "Order and efficiency: improve the system, drop perfectionism.",
    "Libra": "Balance test: don’t delay decisions, get clarity.",
    "Scorpio": "Depth week: intuition strong, avoid control obsession.",
    "Sagittarius": "Horizons expand: new paths call, beware abandoning.",
    "Capricorn": "Goals and discipline: plans win, avoid rigidity.",
    "Aquarius": "Think different: break patterns, avoid detachment.",
    "Pisces": "Intuition and imagination: inspiration high, don’t escape reality.",
}


def burc_hesapla(d: date, lang: str) -> str:
    m, g = d.month, d.day
    if (m == 3 and g >= 21) or (m == 4 and g <= 19): s = "Koç"
    elif (m == 4 and g >= 20) or (m == 5 and g <= 20): s = "Boğa"
    elif (m == 5 and g >= 21) or (m == 6 and g <= 20): s = "İkizler"
    elif (m == 6 and g >= 21) or (m == 7 and g <= 22): s = "Yengeç"
    elif (m == 7 and g >= 23) or (m == 8 and g <= 22): s = "Aslan"
    elif (m == 8 and g >= 23) or (m == 9 and g <= 22): s = "Başak"
    elif (m == 9 and g >= 23) or (m == 10 and g <= 22): s = "Terazi"
    elif (m == 10 and g >= 23) or (m == 11 and g <= 21): s = "Akrep"
    elif (m == 11 and g >= 22) or (m == 12 and g <= 21): s = "Yay"
    elif (m == 12 and g >= 22) or (m == 1 and g <= 19): s = "Oğlak"
    elif (m == 1 and g >= 20) or (m == 2 and g <= 18): s = "Kova"
    else: s = "Balık"
    return SIGN_MAP_TR_EN[s] if lang == "en" else s


# -------------------------
# Session helpers
# -------------------------
def ensure_session_defaults():
    if "lang" not in st.session_state:
        st.session_state.lang = "tr"
    if "debug_mode" not in st.session_state:
        st.session_state.debug_mode = False
    if "puan" not in st.session_state:
        st.session_state.puan = {k: 0 for k in ARSHETIPLER.keys()}
    if "adim" not in st.session_state:
        st.session_state.adim = 0
    if "gunluk" not in st.session_state:
        st.session_state.gunluk = []
    if "logged" not in st.session_state:
        st.session_state.logged = False
    if "isim" not in st.session_state:
        st.session_state.isim = ""
    if "paylas" not in st.session_state:
        st.session_state.paylas = False
    if "dogum_tarihi" not in st.session_state:
        st.session_state.dogum_tarihi = None
    if "burc" not in st.session_state:
        st.session_state.burc = None
    if "astro" not in st.session_state:
        st.session_state.astro = False
    if "profile_id" not in st.session_state:
        st.session_state.profile_id = str(uuid.uuid4())
    if "compat_cache" not in st.session_state:
        st.session_state.compat_cache = {}
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "event_started" not in st.session_state:
        st.session_state.event_started = False
    if "debug_pinged" not in st.session_state:
        st.session_state.debug_pinged = False
    if "tunnel_base" not in st.session_state:
        st.session_state.tunnel_base = ""


def reset_game():
    st.session_state.puan = {k: 0 for k in ARSHETIPLER.keys()}
    st.session_state.adim = 0
    st.session_state.gunluk = []
    st.session_state.logged = False
    st.session_state.isim = ""
    st.session_state.paylas = False
    st.session_state.dogum_tarihi = None
    st.session_state.burc = None
    st.session_state.astro = False
    st.session_state.profile_id = str(uuid.uuid4())
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.event_started = False
    st.session_state.debug_pinged = False
    st.session_state.compat_cache = {}
    if "final_profile" in st.session_state:
        del st.session_state["final_profile"]


# -------------------------
# UI helpers
# -------------------------
def dogum_tarihi_secici(varsayilan: date, lang: str) -> date:
    months = MONTHS.get(lang, MONTHS["tr"])
    c1, c2, c3 = st.columns(3)
    with c1:
        gun = st.selectbox(t(lang, "day"), list(range(1, 32)), index=varsayilan.day - 1)
    with c2:
        ay_index = st.selectbox(
            t(lang, "month"),
            list(range(12)),
            format_func=lambda x: months[x],
            index=varsayilan.month - 1,
        )
    with c3:
        yil = st.selectbox(
            t(lang, "year"),
            list(range(1900, date.today().year + 1)),
            index=varsayilan.year - 1900,
        )
    return date(yil, ay_index + 1, gun)


def paylasim_sayfasi_goster(profil: dict, lang: str):
    st.title(t(lang, "title"))
    st.caption(t(lang, "shared_caption"))

    name = (profil.get("isim") or "").strip() or ("Traveler" if lang == "en" else "Yolcu")
    primary = profil.get("baskin")
    secondary = profil.get("ikincil")

    a = ARSHETIPLER.get(primary, {})
    b = ARSHETIPLER.get(secondary, {})

    st.subheader(t(lang, "life_path_for").format(name=name))
    st.success(
        f"{t(lang,'primary')}: **{a.get(lang,{}).get('name', primary)} {a.get('icon','')}**  |  "
        f"{t(lang,'secondary')}: **{b.get(lang,{}).get('name', secondary)} {b.get('icon','')}**"
    )

    st.markdown(kehanet_metni(primary, secondary, lang))

    with st.expander(t(lang, "score_summary"), expanded=False):
        puan = profil.get("puan") or {}
        table = []
        for k in ["merak", "cesaret", "kontrol", "empati"]:
            ar = ARSHETIPLER[k]
            table.append({
                "Archetype" if lang == "en" else "Arketip": f"{ar[lang]['name']} {ar.get('icon','')}",
                "Score" if lang == "en" else "Puan": puan.get(k, 0)
            })
        st.table(table)

    with st.expander(t(lang, "log_title"), expanded=False):
        gunluk = profil.get("gunluk") or []
        if not gunluk:
            st.caption(t(lang, "no_log"))
        else:
            for i, satir in enumerate(gunluk, 1):
                st.write(f"{i}. {satir}")

    st.divider()
    if st.button(t(lang, "take_test_too"), key="btn_take_test_too"):
        st.query_params.clear()
        st.rerun()


# -------------------------
# Game logic
# -------------------------
def uygula(etki, mini_sahne):
    for k, v in etki.items():
        st.session_state.puan[k] += v
    st.session_state.gunluk.append(mini_sahne)
    st.session_state.adim += 1


def baskin_ve_ikincil(puan_dict):
    sirali = sorted(puan_dict.items(), key=lambda x: x[1], reverse=True)
    baskin = sirali[0][0]
    ikincil = sirali[1][0] if len(sirali) > 1 else sirali[0][0]
    return baskin, ikincil


def kehanet_metni(baskin, ikincil, lang: str):
    a = ARSHETIPLER[baskin]
    b = ARSHETIPLER[ikincil]

    if lang == "en":
        intros = [
            "What you chose today becomes tomorrow’s habit blueprint.",
            "Your path shows itself in decision moments.",
            "This isn’t ‘right/wrong’. It’s a directional map.",
        ]
        outros = [
            "In short: your direction is clear. Now you walk.",
            "A path isn’t fixed. You redraw it daily.",
            "Turn it into a signal: pick one small step and do it today.",
        ]
        action = {
            "merak": "Pick 1 new topic and build a 30-minute micro-learning routine this week.",
            "cesaret": "48-hour rule: choose 1 thing you keep postponing and start within 48 hours.",
            "kontrol": "One-page plan: goal, metric, first step, risk, and plan B.",
            "empati": "Relationship investment: message 3 people ‘how are you?’ and offer concrete help.",
        }[baskin]

        strengths = ", ".join(a["strengths_en"])
        risks = ", ".join(a["risks_en"])
        return f"""
**Primary Archetype:** **{a['en']['name']} {a.get('icon','')}**  
**Secondary Support:** **{b['en']['name']} {b.get('icon','')}**

**Motto:** _{a['en']['motto']}_

{random.choice(intros)}

### How your path operates
- Strengths: {strengths}
- Shadows to watch: {risks}

### This week’s clear action
**{action}**

{random.choice(outros)}
"""
    else:
        girisler = [
            "Bugün seçtiklerin, yarınki alışkanlıklarının taslağı.",
            "Senin izlerin, karar anlarında belirginleşiyor.",
            "Bu test bir ‘doğru/yanlış’ değil; bir yön haritası.",
        ]
        kapanislar = [
            "Özetle: Yönün belli. Şimdi sadece yürümek kaldı.",
            "İz sabit değil. Sen her gün yeniden çiziyorsun.",
            "Bunu bir işarete çevir: küçük bir adım seç, bugün uygula.",
        ]
        aksiyon = {
            "merak": "Bu hafta 1 yeni konu seç, 30 dakikalık mikro-öğrenme rutini kur.",
            "cesaret": "48 saat kuralı: Ertelediğin 1 şeyi seç ve 48 saat içinde başlat.",
            "kontrol": "Tek sayfalık plan: Hedef, metrik, ilk adım, risk, B planı yaz.",
            "empati": "İlişki yatırımı: 3 kişiye ‘nasılsın’ mesajı at, somut destek teklif et.",
        }[baskin]
        return f"""
**Baskın Arketip:** **{a["tr"]["name"]} {a.get("icon","")}**  
**İkincil Destek:** **{b["tr"]["name"]} {b.get("icon","")}**

**Motto:** _{a["tr"]["motto"]}_

{random.choice(girisler)}

### Senin yolun nasıl çalışıyor?
- Güçlerin: {", ".join(a["strengths_tr"])}
- Dikkat etmen gereken gölgeler: {", ".join(a["risks_tr"])}

### Bu haftanın net aksiyonu
**{aksiyon}**

{random.choice(kapanislar)}
"""


def sonuc_profili_uret(baskin, ikincil):
    isim = (st.session_state.get("isim") or "").strip() or ("Traveler" if st.session_state.lang == "en" else "Yolcu")
    return {
        "profile_id": st.session_state.get("profile_id"),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "isim": isim,
        "burc": st.session_state.get("burc"),
        "baskin": baskin,
        "ikincil": ikincil,
        "puan": st.session_state.puan,
        "paylas": st.session_state.get("paylas", False),
        "gunluk": st.session_state.gunluk,
        "uyum": UYUM_PROFILI.get(baskin, {"iyi": [], "zor": []}),
    }


@st.cache_data(show_spinner=False)
def cached_read_jsonl(path_str: str):
    report = read_jsonl(Path(path_str))
    return report.records


def jsonl_oku(limit=80):
    records = cached_read_jsonl(str(RESULTS_LOG_PATH))
    if not records:
        return []
    return records if limit is None else records[-limit:]


def uyum_breakdown(me, other):
    cache = st.session_state.get("compat_cache", {})
    id_a = str(me.get("profile_id", "A"))
    id_b = str(other.get("profile_id", "B"))
    pair_key = tuple(sorted([id_a, id_b]))

    if pair_key in cache:
        return cache[pair_key]

    puan_me = me.get("puan", {}) or {}
    puan_other = other.get("puan", {}) or {}

    profile_a = {ARCHETYPE_MAP[k]: float(v) for k, v in puan_me.items() if k in ARCHETYPE_MAP}
    profile_b = {ARCHETYPE_MAP[k]: float(v) for k, v in puan_other.items() if k in ARCHETYPE_MAP}

    pair_seed = ":".join(pair_key)

    br = compute_compatibility_score(
        profile_a=profile_a,
        profile_b=profile_b,
        tags_a=None,
        tags_b=None,
        seed=pair_seed,
    )

    x = float(br.final01)
    gamma = 2.6
    shaped = x ** gamma
    base = 10 + 86 * shaped

    me_b = me.get("baskin")
    other_b = other.get("baskin")
    iyi = (UYUM_PROFILI.get(me_b, {}) or {}).get("iyi", [])
    zor = (UYUM_PROFILI.get(me_b, {}) or {}).get("zor", [])

    adj = 0
    if other_b in iyi:
        adj += 10
    if other_b in zor:
        adj -= 18
    if me.get("baskin") == other.get("baskin"):
        adj += 6
    if me.get("ikincil") == other.get("ikincil"):
        adj += 3
    if me.get("baskin") == other.get("baskin") == "kontrol":
        adj -= 6

    scale = 0.25 + 0.75 * (1.0 - x)
    skor = base + adj * scale
    skor = max(3, min(97, skor))

    result = (int(round(skor)), br)
    if len(cache) > 500:
        cache.clear()
    cache[pair_key] = result
    st.session_state.compat_cache = cache
    return result


def eslesme_vitrini(me, tum_profiller, top_n=2, mid_n=2, low_n=1):
    me_id = me.get("profile_id")
    adaylar = [p for p in tum_profiller if p.get("profile_id") != me_id]

    skorlu = []
    for p in adaylar:
        sk, br = uyum_breakdown(me, p)
        skorlu.append((sk, br, p))

    if not skorlu:
        return []

    skorlu.sort(key=lambda x: x[0], reverse=True)

    top = skorlu[:top_n]
    mid = []
    if mid_n > 0:
        start = max(0, len(skorlu) // 2 - mid_n)
        mid = skorlu[start:start + mid_n]
    low = skorlu[-low_n:] if low_n > 0 else []

    seen = set()
    vitrin = []
    for sk, br, p in top + mid + low:
        pid = p.get("profile_id")
        if pid in seen:
            continue
        seen.add(pid)
        vitrin.append((sk, br, p))
    return vitrin


def run():
    ensure_session_defaults()

    # Sidebar
    st.sidebar.title(t(st.session_state.lang, "sidebar_title"))
    lang = st.sidebar.radio(
        t(st.session_state.lang, "language"),
        options=["tr", "en"],
        format_func=lambda x: "Türkçe" if x == "tr" else "English",
        index=0 if st.session_state.lang == "tr" else 1,
    )
    st.session_state.lang = lang
    st.sidebar.checkbox(t(lang, "debug"), value=st.session_state.debug_mode, key="debug_mode")
    debug_mode = st.session_state.debug_mode

    # DEBUG ping (sadece debug açıkken, 1 kere)
    if debug_mode and (not st.session_state.debug_pinged):
        log_event(EVENTS_LOG_PATH, {
            "event": "debug_ping",
            "profile_id": st.session_state.get("profile_id"),
            "session_id": st.session_state.get("session_id"),
            "lang": st.session_state.get("lang", "tr"),
        })
        st.session_state.debug_pinged = True

    # EVENT: app_opened (once per session)
    if not st.session_state.event_started:
        log_event(EVENTS_LOG_PATH, {
            "event": "app_opened",
            "profile_id": st.session_state.get("profile_id"),
            "session_id": st.session_state.get("session_id"),
            "lang": st.session_state.get("lang", "tr"),
            "has_share_id": bool(st.query_params.get("id", None)),
        })
        st.session_state.event_started = True

    # Questions
    SORULAR = get_questions(lang)

    # Shared link handling
    qid = st.query_params.get("id", None)
    if qid:
        paylasilan = find_by_profile_id(RESULTS_LOG_PATH, str(qid))
        if paylasilan:
            paylasim_sayfasi_goster(paylasilan, lang)
            st.stop()
        else:
            st.warning(t(lang, "shared_not_found"))
            st.query_params.clear()

    # Header
    st.title(t(lang, "title"))
    st.caption(t(lang, "subtitle"))

    # Name + share checkbox
    if st.session_state.adim == 0:
        st.session_state.isim = st.text_input(
            t(lang, "name_optional"),
            value=st.session_state.get("isim", ""),
            key="name_input",
        ).strip()

        st.session_state.paylas = st.checkbox(
            t(lang, "show_name_in_matches"),
            value=st.session_state.get("paylas", False),
            key="show_name_checkbox",
        )

    # Astro mode
    if st.session_state.adim == 0:
        st.session_state.astro = st.checkbox(
            t(lang, "astro_mode"),
            value=st.session_state.get("astro", False),
            key="astro_checkbox",
        )

        if st.session_state.astro:
            dt0 = st.session_state.get("dogum_tarihi") or date.today()
            dt = dogum_tarihi_secici(dt0, lang)
            st.session_state.dogum_tarihi = dt
            st.session_state.burc = burc_hesapla(dt, lang)
        else:
            st.session_state.dogum_tarihi = None
            st.session_state.burc = None

        if st.session_state.get("burc"):
            sign = st.session_state.burc
            theme = (BURC_TEMALARI_EN.get(sign, "") if lang == "en" else BURC_TEMALARI_TR.get(sign, ""))
            st.info(f"{t(lang,'atmosphere')} ({sign}): {theme}")
        else:
            st.info(t(lang, "astro_off"))

    # Reset
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button(t(lang, "reset"), key="reset"):
            log_event(EVENTS_LOG_PATH, {
                "event": "reset_clicked",
                "profile_id": st.session_state.get("profile_id"),
                "session_id": st.session_state.get("session_id"),
                "lang": st.session_state.get("lang", "tr"),
            })
            reset_game()
            st.rerun()
    with c2:
        st.write("")

    # Progress
    st.progress(min(st.session_state.adim / max(len(SORULAR), 1), 1.0))
    st.write(f"{t(lang,'progress')}: **{st.session_state.adim}/{len(SORULAR)}**")
    st.divider()

    # Q flow
    if st.session_state.adim < len(SORULAR):
        soru, secenekler = SORULAR[st.session_state.adim]
        st.subheader(soru)

        for yazi, etki, mini_sahne in secenekler:
            if st.button(yazi, key=f"btn_{st.session_state.adim}_{yazi}"):

                log_event(EVENTS_LOG_PATH, {
                    "event": "question_answered",
                    "profile_id": st.session_state.get("profile_id"),
                    "session_id": st.session_state.get("session_id"),
                    "lang": st.session_state.get("lang", "tr"),
                    "step": int(st.session_state.adim),
                    "question": str(soru),
                    "choice": str(yazi),
                    "effect": etki,
                })

                uygula(etki, mini_sahne)
                st.rerun()

    # Result
    else:
        isim = (st.session_state.get("isim") or "").strip() or ("Traveler" if lang == "en" else "Yolcu")
        st.subheader(t(lang, "life_path_for").format(name=isim))

        baskin, ikincil = baskin_ve_ikincil(st.session_state.puan)
        a = ARSHETIPLER[baskin]
        b = ARSHETIPLER[ikincil]

        if "final_profile" not in st.session_state:
            st.session_state.final_profile = sonuc_profili_uret(baskin, ikincil)

            log_event(EVENTS_LOG_PATH, {
                "event": "result_shown",
                "profile_id": st.session_state.get("profile_id"),
                "session_id": st.session_state.get("session_id"),
                "lang": st.session_state.get("lang", "tr"),
                "primary": baskin,
                "secondary": ikincil,
                "scores": dict(st.session_state.puan),
            })

        profil = st.session_state.final_profile

        # Persist to results_log.jsonl only once
        if not st.session_state.get("logged", False):
            record = dict(profil)
            record["profile_id"] = ensure_unique_profile_id(RESULTS_LOG_PATH, record.get("profile_id"))
            written, pid = append_unique_by_profile_id(RESULTS_LOG_PATH, record)
            profil["profile_id"] = pid
            st.session_state.logged = True
            cached_read_jsonl.clear()

        st.success(
            f"{t(lang,'primary')}: **{a[lang]['name']} {a.get('icon','')}**  |  "
            f"{t(lang,'secondary')}: **{b[lang]['name']} {b.get('icon','')}**"
        )
        st.markdown(kehanet_metni(baskin, ikincil, lang))

        # -------------------------------------------------
        # Share link (BURASI SHARE KISMI)  ✅ DOĞRU GİRİNTİ
        # -------------------------------------------------
        st.divider()
        st.subheader(t(lang, "share_title"))

        share_id = profil.get("profile_id")

        # Lokal link (senin bilgisayarın)
        local_url = f"http://localhost:8501/?id={share_id}"

        # Cloudflare/Deploy base adresi (opsiyonel)
        st.session_state.tunnel_base = st.text_input(
            "Cloudflare / Deploy adresin (opsiyonel)",
            value=(st.session_state.get("tunnel_base") or ""),
            placeholder="https://xxxxx.trycloudflare.com",
            key="tunnel_base_input",
        ).strip()

        tunnel_url = (
            f"{st.session_state.tunnel_base.rstrip('/')}/?id={share_id}"
            if st.session_state.tunnel_base
            else ""
        )

        colA, colB = st.columns([1, 2])
        with colA:
            if st.button(t(lang, "share_button"), key="btn_share_link"):
                log_event(EVENTS_LOG_PATH, {
                    "event": "share_link_created",
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "profile_id": st.session_state.get("profile_id"),
                    "session_id": st.session_state.get("session_id"),
                    "lang": st.session_state.get("lang", "tr"),
                    "share_id": share_id,
                })
                st.session_state["last_share_id"] = share_id

        with colB:
            st.caption(t(lang, "share_hint"))

        st.write("✅ Lokal link:")
        st.text_input("Local URL", value=local_url, label_visibility="visible", key="local_url_output")

        if tunnel_url:
            st.write("✅ Paylaşılabilir link (Cloudflare/Deploy):")
            st.text_input("Share URL", value=tunnel_url, label_visibility="visible", key="share_url_output")
        else:
            st.info("Cloudflare/Deploy adresini girersen burada tam paylaşım linkini üretirim.")

        # Score summary
        with st.expander(t(lang, "score_summary"), expanded=False):
            table = []
            for k in ["merak", "cesaret", "kontrol", "empati"]:
                ar = ARSHETIPLER[k]
                table.append({
                    "Archetype" if lang == "en" else "Arketip": f"{ar[lang]['name']} {ar.get('icon','')}",
                    "Score" if lang == "en" else "Puan": st.session_state.puan.get(k, 0),
                })
            st.table(table)

        # Profile card
        st.subheader(t(lang, "your_profile"))
        with st.container(border=True):
            st.markdown(f"### {isim} ({t(lang,'you_label')})")
            st.write(
                f"**{t(lang,'primary')}:** {a[lang]['name']} {a.get('icon','')}  |  "
                f"**{t(lang,'secondary')}:** {b[lang]['name']} {b.get('icon','')}"
            )
            st.write(f"**{t(lang,'sign')}:** {st.session_state.get('burc') or '—'}")

        # Matches
        st.divider()
        st.subheader(t(lang, "travelers_like_you"))

        tum = jsonl_oku(limit=80)
        yakinlar = eslesme_vitrini(profil, tum, top_n=2, mid_n=2, low_n=1)

        st.subheader(t(lang, "best_matches"))
        top2 = yakinlar[:2]
        if not top2:
            st.caption(t(lang, "not_enough_data"))
        else:
            for rank, (sk, br, p) in enumerate(top2, 1):
                isim2 = (p.get("isim") or "").strip()
                etiket2 = isim2 if (p.get("paylas") and isim2) else t(lang, "anonymous")

                bsk2 = p.get("baskin")
                ik2 = p.get("ikincil")
                a1_2 = ARSHETIPLER.get(bsk2, {})
                a2_2 = ARSHETIPLER.get(ik2, {})

                baskin_text2 = f"{t(lang,'primary')}: {a1_2.get(lang,{}).get('name', bsk2)} {a1_2.get('icon','')}"
                ikincil_text2 = f"{t(lang,'secondary')}: {a2_2.get(lang,{}).get('name', ik2)} {a2_2.get('icon','')}"
                burc2 = p.get("burc") or "—"

                debug_text2 = None
                if debug_mode:
                    debug_text2 = f"final01={br.final01:.3f} | raw={br.raw:.2f} shaped={br.shaped:.2f}"

                render_match_card(
                    idx=rank,
                    ad=etiket2,
                    sk=sk,
                    baskin_text=baskin_text2,
                    ikincil_text=ikincil_text2,
                    burc=burc2,
                    neden_maddeler=[],
                    debug_mode=debug_mode,
                    debug_text=debug_text2,
                )


if __name__ == "__main__":
    run()