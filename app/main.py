import streamlit as st
import random
import json
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
)

# Tek kaynak: log dosyası app/ klasörü içinde (senin eski düzeninle uyumlu)
RESULTS_LOG_PATH = Path(__file__).parent / "results_log.jsonl"


# -------------------------
# Sorular: JSON -> internal format
# -------------------------
def parse_questions(raw):
    """
    JSON içeriğini şu formata çevirir:
    [
      (soru, [(yazi, etki, mini_sahne), ...]),
      ...
    ]
    """
    sorular = []
    for item in raw:
        soru = item["soru"]
        secenekler = []
        for s in item["secenekler"]:
            secenekler.append((s["yazi"], s["etki"], s.get("mini_sahne", "")))
        sorular.append((soru, secenekler))
    return sorular


SORULAR_RAW = load_json("questions.json")
SORULAR = parse_questions(SORULAR_RAW)


# -------------------------
# Konfig / İçerik
# -------------------------
ARSHETIPLER = {
    "merak": {
        "ikon": "🧭",
        "ad": "Kaşif",
        "motto": "Cevap değil, doğru soru güç verir.",
        "aciklama": "Yeni fikirlere hızlı açılırsın. Bilmediğin yere gitmek seni korkutmaz; merakın seni taşır.",
        "guc": ["Öğrenme hızı", "Yaratıcı problem çözme", "Fırsatları görme"],
        "risk": ["Dağılma", "Yarım bırakma", "Sürekli seçenek arama"],
    },
    "cesaret": {
        "ikon": "⚔️",
        "ad": "Savaşçı",
        "motto": "Korku var diye durmam.",
        "aciklama": "Risk alabilirsin. Karar anında beklemek yerine hamle yapmayı seçersin.",
        "guc": ["Hızlı aksiyon", "Liderlik", "Zor anlarda soğukkanlılık"],
        "risk": ["Acelecilik", "Gereksiz çatışma", "Sabırsızlık"],
    },
    "kontrol": {
        "ikon": "🧠",
        "ad": "Stratejist",
        "motto": "Plan yapan kazanır.",
        "aciklama": "Sistem kurar, işi ölçer, kontrol edersin. Kaosu azaltırsın, düzen kurarsın.",
        "guc": ["Disiplin", "Planlama", "Süreç yönetimi"],
        "risk": ["Aşırı kontrol", "Esneklik kaybı", "Kendini yıpratma"],
    },
    "empati": {
        "ikon": "🌿",
        "ad": "Şifacı",
        "motto": "İnsanı anlamadan hayat anlaşılmaz.",
        "aciklama": "İlişki yönetimi güçlüdür. Ortamı okur, insanları hissedersin.",
        "guc": ["İletişim", "Güven inşası", "Duygusal zekâ"],
        "risk": ["Fazla yük alma", "Sınır koyamama", "Herkesi memnun etmeye çalışma"],
    },
}

# Compatibility motorunun beklediği anahtarlar
ARCHETYPE_MAP = {
    "merak": "kasif",
    "cesaret": "savasci",
    "kontrol": "stratejist",
    "empati": "sifaci",
}

# Uyum profili (match motorunun çekirdeği)
UYUM_PROFILI = {
    "merak":  {"iyi": ["empati", "kontrol"], "zor": ["cesaret"]},
    "cesaret":{"iyi": ["kontrol", "merak"],  "zor": ["empati"]},
    "kontrol":{"iyi": ["cesaret", "empati"], "zor": ["merak"]},
    "empati": {"iyi": ["merak", "kontrol"], "zor": ["cesaret"]},
}


# -------------------------
# Astro atmosferi
# -------------------------
BURC_TEMALARI = {
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


def burc_hesapla(d: date) -> str:
    m, g = d.month, d.day
    if (m == 3 and g >= 21) or (m == 4 and g <= 19): return "Koç"
    if (m == 4 and g >= 20) or (m == 5 and g <= 20): return "Boğa"
    if (m == 5 and g >= 21) or (m == 6 and g <= 20): return "İkizler"
    if (m == 6 and g >= 21) or (m == 7 and g <= 22): return "Yengeç"
    if (m == 7 and g >= 23) or (m == 8 and g <= 22): return "Aslan"
    if (m == 8 and g >= 23) or (m == 9 and g <= 22): return "Başak"
    if (m == 9 and g >= 23) or (m == 10 and g <= 22): return "Terazi"
    if (m == 10 and g >= 23) or (m == 11 and g <= 21): return "Akrep"
    if (m == 11 and g >= 22) or (m == 12 and g <= 21): return "Yay"
    if (m == 12 and g >= 22) or (m == 1 and g <= 19): return "Oğlak"
    if (m == 1 and g >= 20) or (m == 2 and g <= 18): return "Kova"
    return "Balık"


# -------------------------
# Session helpers
# -------------------------
def ensure_session_defaults():
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
    if "final_profile" in st.session_state:
        del st.session_state["final_profile"]
    st.session_state.compat_cache = {}


# -------------------------
# UI yardımcıları (RUN'DAN ÖNCE OLMALI)
# -------------------------
def dogum_tarihi_secici(varsayilan: date) -> date:
    aylar = [
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
    ]

    c1, c2, c3 = st.columns(3)

    with c1:
        gun = st.selectbox("Gün", list(range(1, 32)), index=varsayilan.day - 1)

    with c2:
        ay_index = st.selectbox(
            "Ay",
            list(range(12)),
            format_func=lambda x: aylar[x],
            index=varsayilan.month - 1
        )

    with c3:
        yil = st.selectbox(
            "Yıl",
            list(range(1900, date.today().year + 1)),
            index=varsayilan.year - 1900
        )

    return date(yil, ay_index + 1, gun)


def paylasim_sayfasi_goster(profil: dict):
    st.title("🔮 Life Path Test")
    st.caption("Showing a shared result.")

    isim = (profil.get("isim") or "").strip() or "Yolcu"
    burc = profil.get("burc") or "—"
    baskin = profil.get("baskin")
    ikincil = profil.get("ikincil")

    a = ARSHETIPLER.get(baskin, {"ad": baskin, "ikon": ""})
    b = ARSHETIPLER.get(ikincil, {"ad": ikincil, "ikon": ""})

    st.subheader(f"📌 {isim}'s Life Path")
    st.success(
        f"Baskın yönün: **{a['ad']} {a.get('ikon','')}**  |  "
        f"Destek yönün: **{b['ad']} {b.get('ikon','')}**"
    )

    st.markdown(kehanet_metni(baskin, ikincil))

    with st.expander("📊 Puan Özeti", expanded=False):
        puan = profil.get("puan") or {}
        tablo = []
        for k in ["merak", "cesaret", "kontrol", "empati"]:
            ar = ARSHETIPLER[k]
            tablo.append({"Arketip": f"{ar['ad']} {ar.get('ikon','')}", "Puan": puan.get(k, 0)})
        st.table(tablo)

    with st.expander("🎬 Seçim Günlüğü", expanded=False):
        gunluk = profil.get("gunluk") or []
        if not gunluk:
            st.caption("No log yet.")
        else:
            for i, satir in enumerate(gunluk, 1):
                st.write(f"{i}. {satir}")

    st.divider()
    if st.button("✅ I want to take the test too"):
        st.query_params.clear()
        st.rerun()


# -------------------------
# Oyun fonksiyonları
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


def kehanet_metni(baskin, ikincil):
    a = ARSHETIPLER[baskin]
    b = ARSHETIPLER[ikincil]

    girisler = [
        "Bugün seçtiklerin, yarınki alışkanlıklarının taslağı.",
        "Senin kader çizgin, karar anlarında belirginleşiyor.",
        "Bu test bir ‘doğru/yanlış’ değil; bir yön haritası.",
    ]
    kapanislar = [
        "Özetle: Yönün belli. Şimdi sadece yürümek kaldı.",
        "Kader çizgisi sabit değil. Sen her gün yeniden çiziyorsun.",
        "Bunu bir işarete çevir: küçük bir adım seç, bugün uygula.",
    ]

    aksiyon = {
        "merak": "Bu hafta 1 yeni konu seç, 30 dakikalık mikro-öğrenme rutini kur.",
        "cesaret": "48 saat kuralı: Ertelediğin 1 şeyi seç ve 48 saat içinde başlat.",
        "kontrol": "Tek sayfalık plan: Hedef, metrik, ilk adım, risk, B planı yaz.",
        "empati": "İlişki yatırımı: 3 kişiye ‘nasılsın’ mesajı at, somut destek teklif et.",
    }[baskin]

    return f"""
**Baskın Arketip:** **{a["ad"]} {a.get("ikon","")}**  
**İkincil Destek:** **{b["ad"]} {b.get("ikon","")}**

**Motto:** _{a["motto"]}_

{random.choice(girisler)}

### Senin yolun nasıl çalışıyor?
- Güçlerin: {", ".join(a["guc"])}
- Dikkat etmen gereken gölgeler: {", ".join(a["risk"])}

### Bu haftanın net aksiyonu
**{aksiyon}**

{random.choice(kapanislar)}
"""


def sonuc_profili_uret(baskin, ikincil):
    isim = (st.session_state.get("isim") or "").strip() or "Yolcu"
    profil = {
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
    return profil

@st.cache_data(show_spinner=False)
def cached_read_jsonl(path_str: str):
    """
    JSONL dosyasını cache'li şekilde okur.
    path_str string olmalı (Path cache anahtarında bazen sorun çıkarır).
    """
    report = read_jsonl(Path(path_str))
    return report.records

def jsonl_oku(limit=80):
    records = cached_read_jsonl(str(RESULTS_LOG_PATH))
    if not records:
        return []
    if limit is None:
        return records
    return records[-limit:]



def puan_benzerligi(me, other):
    keys = ["merak", "cesaret", "kontrol", "empati"]
    v1 = [me.get("puan", {}).get(k, 0) for k in keys]
    v2 = [other.get("puan", {}).get(k, 0) for k in keys]
    s1, s2 = sum(v1), sum(v2)
    if s1 == 0 or s2 == 0:
        return 0
    v1 = [x / s1 for x in v1]
    v2 = [x / s2 for x in v2]
    diff = sum(abs(a - b) for a, b in zip(v1, v2)) / len(keys)
    sim = 1 - diff
    return int(round(sim * 30))


def uyum_maddeleri(me, other):
    maddeler = []
    iyi = me.get("uyum", {}).get("iyi", [])
    zor = me.get("uyum", {}).get("zor", [])
    ob = other.get("baskin")

    if me.get("baskin") == other.get("baskin"):
        maddeler.append("Baskın arketipiniz aynı: benzer tepki ve tempo.")
    if me.get("ikincil") == other.get("ikincil"):
        maddeler.append("Destek arketipiniz aynı: benzer karar tarzı.")
    if ob in iyi:
        maddeler.append("Karşı tarafın baskın yönü seni tamamlıyor (iyi eşleşme).")
    if ob in zor:
        maddeler.append("Karşı tarafın baskın yönü seni zorlayabilir (çatışma riski).")

    benzer = puan_benzerligi(me, other)
    if benzer >= 24:
        maddeler.append("Karar dağılımınız çok benzer: çatışma az, akış yüksek.")
    elif benzer >= 16:
        maddeler.append("Birçok konuda benzer davranıyorsunuz: uyum orta-iyi.")
    else:
        maddeler.append("Yaklaşım farkı var: doğru iletişimle dengelenir.")

    if me.get("burc") and me.get("burc") == other.get("burc"):
        maddeler.append("Burç aynı: iletişim dili daha kolay tutabilir.")
    return maddeler


def uyum_breakdown(me, other):
        # Pair bazlı cache: aynı ikiliyi tekrar hesaplama
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
        seed=pair_seed
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

    # Cache'e yaz (büyümesin diye basit limit)
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
    kalan = skorlu[top_n:]
    if not kalan:
        return top

    mid = []
    if mid_n > 0:
        start = max(0, len(skorlu)//2 - mid_n)
        mid = skorlu[start:start+mid_n]

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


# -------------------------
# App entrypoint
# -------------------------
def run():
    st.set_page_config(page_title="Life Path Test", page_icon="🔮", layout="centered")
    ensure_session_defaults()

    # 1) Paylaşım linki kontrolü (SADECE BURADA)
    qid = st.query_params.get("id", None)
    if qid:
        paylasilan = find_by_profile_id(RESULTS_LOG_PATH, str(qid))
        if paylasilan:
            paylasim_sayfasi_goster(paylasilan)
            st.stop()
        else:
            st.warning("Bu id ile kayıt bulunamadı. Yeni test başlatılıyor.")
            st.query_params.clear()

    # 2) Normal akış başlığı
    st.title("🔮 Life Path Test")
    st.caption("Make choices. Let the story unfold. At the end, I'll read your path.")

    debug_mode = st.session_state.debug_mode

    # 3) İsim + paylaşım ayarı (adım 0'da)
    if st.session_state.adim == 0:
        st.session_state.isim = st.text_input(
            "Adın ne? (opsiyonel)",
            value=st.session_state.get("isim", "")
        ).strip()

        st.session_state.paylas = st.checkbox(
            "Eşleşme listesinde ismim görünsün",
            value=st.session_state.get("paylas", False)
        )

    # 4) Astro modu (adım 0'da)
    if st.session_state.adim == 0:
        st.session_state.astro = st.checkbox(
            "Astro modu (burç atmosferi ekle)",
            value=st.session_state.get("astro", False)
        )

        if st.session_state.astro:
            dt0 = st.session_state.get("dogum_tarihi") or date.today()
            dt = dogum_tarihi_secici(dt0)
            st.session_state.dogum_tarihi = dt
            st.session_state.burc = burc_hesapla(dt)
        else:
            st.session_state.dogum_tarihi = None
            st.session_state.burc = None

        if st.session_state.get("burc"):
            st.info(
                f"🔭 Atmosfer ({st.session_state.burc}): "
                f"{BURC_TEMALARI.get(st.session_state.burc, '')}"
            )
        else:
            st.info("Astro modu kapalı: Açarsan burç atmosferini de eklerim.")

    # 5) Reset butonu
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("🔁 Reset / Start Over", key="reset"):
            reset_game()
            st.rerun()
    with c2:
        st.write("")

    # 6) İlerleme
    st.progress(min(st.session_state.adim / len(SORULAR), 1.0))
    st.write(f"Progress: **{st.session_state.adim}/{len(SORULAR)}**")
    st.divider()

    # 7) Soru akışı
    if st.session_state.adim < len(SORULAR):
        soru, secenekler = SORULAR[st.session_state.adim]
        st.subheader(soru)
        for yazi, etki, mini_sahne in secenekler:
            if st.button(yazi, key=f"btn_{st.session_state.adim}_{yazi}"):
                uygula(etki, mini_sahne)
                st.rerun()

    # 8) Sonuç ekranı
    else:
        isim = (st.session_state.get("isim") or "").strip() or "Yolcu"
        st.subheader(f"📌 {isim}'s Life Path")

        baskin, ikincil = baskin_ve_ikincil(st.session_state.puan)
        a = ARSHETIPLER[baskin]
        b = ARSHETIPLER[ikincil]

        if "final_profile" not in st.session_state:
            st.session_state.final_profile = sonuc_profili_uret(baskin, ikincil)

        profil = st.session_state.final_profile

        if not st.session_state.get("logged", False):
            record = dict(profil)
            record["profile_id"] = ensure_unique_profile_id(RESULTS_LOG_PATH, record.get("profile_id"))

            written, pid = append_unique_by_profile_id(RESULTS_LOG_PATH, record)

            try:
                profil["profile_id"] = pid
            except Exception:
                pass

            st.session_state.logged = True
            
            cached_read_jsonl.clear()

        st.success(
            f"Baskın yönün: **{a['ad']} {a.get('ikon','')}**  |  "
            f"Destek yönün: **{b['ad']} {b.get('ikon','')}**"
        )
        st.markdown(kehanet_metni(baskin, ikincil))

        st.divider()
        st.subheader("🔗 Share")
        colA, colB = st.columns([1, 2])
        with colA:
            if st.button("Create link", key="btn_share_link"):
                st.query_params["id"] = profil.get("profile_id")
                st.rerun()
        with colB:
            st.caption("After clicking, the URL will update. Copy the link from the address bar and share it.")

        with st.expander("📊 Puan Özeti", expanded=False):
            puan_tablosu = []
            for k, v in st.session_state.puan.items():
                ar = ARSHETIPLER[k]
                puan_tablosu.append({"Arketip": f"{ar['ad']} {ar.get('ikon','')}", "Puan": v})
            st.table(puan_tablosu)

        st.subheader("🧍 Your Profile")
        with st.container(border=True):
            st.markdown(f"### {isim} (You)")
            st.write(f"**Primary:** {a['ad']} {a.get('ikon','')} | **Secondary:** {b['ad']} {b.get('ikon','')}")
            st.write(f"**Sign:** {st.session_state.get('burc') or '—'}")

        st.divider()
        st.subheader("🧩 Travelers like you")

        tum = jsonl_oku(limit=80)
        yakinlar = eslesme_vitrini(profil, tum, top_n=2, mid_n=2, low_n=1)

        st.subheader("💘 Your best matches")
        top2 = yakinlar[:2]

        if not top2:
            st.caption("Not enough data yet.")
        else:
            for rank, (sk, br, p) in enumerate(top2, 1):
                isim2 = (p.get("isim") or "").strip()
                paylas2 = p.get("paylas", False)
                etiket2 = isim2 if (paylas2 and isim2) else "Anonim Yolcu"

                bsk2 = p.get("baskin")
                ik2 = p.get("ikincil")
                a1_2 = ARSHETIPLER.get(bsk2, {"ad": bsk2, "ikon": ""})
                a2_2 = ARSHETIPLER.get(ik2, {"ad": ik2, "ikon": ""})

                baskin_text2 = f"Baskın: {a1_2.get('ad','')} {a1_2.get('ikon','')}"
                ikincil_text2 = f"Destek: {a2_2.get('ad','')} {a2_2.get('ikon','')}"
                burc2 = p.get("burc") or "—"
                nedenler2 = uyum_maddeleri(profil, p)

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
                    neden_maddeler=nedenler2,
                    debug_mode=debug_mode,
                    debug_text=debug_text2
                )

        top2_ids = {p.get("profile_id") for (_, _, p) in top2 if p.get("profile_id")}

        st.subheader("🎯 Other matches")
        sirano = 1
        for (sk, br, p) in yakinlar:
            pid = p.get("profile_id")
            if pid in top2_ids:
                continue

            isim3 = (p.get("isim") or "").strip()
            etiket = isim3 if (p.get("paylas") and isim3) else "Anonim Yolcu"

            bsk = p.get("baskin")
            ik = p.get("ikincil")
            a1 = ARSHETIPLER.get(bsk, {"ad": bsk, "ikon": ""})
            a2 = ARSHETIPLER.get(ik, {"ad": ik, "ikon": ""})

            baskin_text = f"Baskın: {a1.get('ad','')} {a1.get('ikon','')}"
            ikincil_text = f"Destek: {a2.get('ad','')} {a2.get('ikon','')}"
            burc = p.get("burc") or "—"
            nedenler = uyum_maddeleri(profil, p)

            debug_text = None
            if debug_mode:
                debug_text = f"final01={br.final01:.3f} | raw={br.raw:.2f} shaped={br.shaped:.2f}"

            render_match_card(
                idx=sirano,
                ad=etiket,
                sk=sk,
                baskin_text=baskin_text,
                ikincil_text=ikincil_text,
                burc=burc,
                neden_maddeler=nedenler,
                debug_mode=debug_mode,
                debug_text=debug_text
            )
            sirano += 1

        a_r = ARSHETIPLER.get(profil.get("baskin"), {"ad": profil.get("baskin", ""), "ikon": ""})
        b_r = ARSHETIPLER.get(profil.get("ikincil"), {"ad": profil.get("ikincil", ""), "ikon": ""})

        rapor = f"""{profil.get("isim") or "Yolcu"} — Hayat Yolu Testi Raporu
Tarih: {datetime.now().strftime("%d.%m.%Y %H:%M")}
Burç: {profil.get("burc") or "—"}
Baskın: {a_r.get('ad','')} {a_r.get('ikon','')}
Destek: {b_r.get('ad','')} {b_r.get('ikon','')}

Puanlar:
- Kaşif 🧭 (merak): {profil.get("puan", {}).get("merak", 0)}
- Savaşçı ⚔️ (cesaret): {profil.get("puan", {}).get("cesaret", 0)}
- Stratejist 🧠 (kontrol): {profil.get("puan", {}).get("kontrol", 0)}
- Şifacı 🌿 (empati): {profil.get("puan", {}).get("empati", 0)}

{kehanet_metni(profil.get("baskin"), profil.get("ikincil"))}
"""

        rapor_key = f"rapor_kopyala_{profil.get('profile_id','x')}"
        st.session_state[rapor_key] = rapor

        with st.expander("📋 Raporu Kopyala", expanded=False):
            st.text_area("Kopyala (Cmd/Ctrl + C):", key=rapor_key, height=320)

        with st.expander("🎬 Seçim Günlüğün (sahne sahne)", expanded=False):
            for i, satir in enumerate(st.session_state.gunluk, 1):
                st.write(f"{i}. {satir}")


if __name__ == "__main__":
    run()
