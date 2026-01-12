import streamlit as st

LANGS = {
    "tr": "Türkçe",
    "en": "English",
}

TEXTS = {
    "app_title": {
        "tr": "🔮 Hayat Yolu Testi",
        "en": "🔮 Life Path Test",
    },
    "app_caption": {
        "tr": "Seçim yap. Hikaye ilerlesin. En sonda ‘kader çizgini’ yorumlayayım.",
        "en": "Make choices. Let the story unfold. At the end, I'll interpret your 'life path'.",
    },
    "shared_caption": {
        "tr": "Paylaşılan sonuç görüntüleniyor.",
        "en": "Viewing a shared result.",
    },
    "btn_restart": {
        "tr": "🔁 Sıfırla / Yeniden Başla",
        "en": "🔁 Restart",
    },
    "progress": {
        "tr": "İlerleme: **{step}/{total}**",
        "en": "Progress: **{step}/{total}**",
    },
    "share": {"tr": "🔗 Paylaş", "en": "🔗 Share"},
    "btn_make_link": {"tr": "Link oluştur", "en": "Create link"},
    "share_hint": {
        "tr": "Butona basınca URL güncellenecek. Adres çubuğundaki linki kopyalayıp paylaş.",
        "en": "After clicking, the URL updates. Copy the link from the address bar and share it.",
    },
    "my_profile": {"tr": "🧍 Senin Profilin", "en": "🧍 Your Profile"},
    "similar_travelers": {"tr": "🧩 Benim gibi yolcular", "en": "🧩 Similar Travelers"},
    "best_matches": {"tr": "💘 En iyi eşleşmelerin", "en": "💘 Your Best Matches"},
    "other_matches": {"tr": "🎯 Diğer eşleşmeler", "en": "🎯 Other Matches"},
    "not_enough_data": {"tr": "Henüz yeterli veri yok.", "en": "Not enough data yet."},
    "btn_take_test_too": {
        "tr": "✅ Testi ben de çözmek istiyorum",
        "en": "✅ I want to take the test too",
    },
    "result_title": {
        "tr": "📌 {name} için Kader Çizgin",
        "en": "📌 {name}'s Life Path",
    },
    "daily_log_empty": {"tr": "Günlük yok.", "en": "No daily log."},
    "lang_label": {"tr": "Dil / Language", "en": "Language / Dil"},
}

TRAITS = {
    "merak": {"tr": "Merak", "en": "Curiosity"},
    "cesaret": {"tr": "Cesaret", "en": "Courage"},
    "kontrol": {"tr": "Kontrol", "en": "Control"},
    "empati": {"tr": "Empati", "en": "Empathy"},
}

SIGNS = [
    ("aries", {"tr": "Koç", "en": "Aries"}),
    ("taurus", {"tr": "Boğa", "en": "Taurus"}),
    ("gemini", {"tr": "İkizler", "en": "Gemini"}),
    ("cancer", {"tr": "Yengeç", "en": "Cancer"}),
    ("leo", {"tr": "Aslan", "en": "Leo"}),
    ("virgo", {"tr": "Başak", "en": "Virgo"}),
    ("libra", {"tr": "Terazi", "en": "Libra"}),
    ("scorpio", {"tr": "Akrep", "en": "Scorpio"}),
    ("sagittarius", {"tr": "Yay", "en": "Sagittarius"}),
    ("capricorn", {"tr": "Oğlak", "en": "Capricorn"}),
    ("aquarius", {"tr": "Kova", "en": "Aquarius"}),
    ("pisces", {"tr": "Balık", "en": "Pisces"}),
]

def get_lang() -> str:
    return st.session_state.get("lang", "tr")

def init_lang_selector(default: str = "tr") -> str:
    if "lang" not in st.session_state:
        st.session_state["lang"] = default

    opts = list(LANGS.keys())
    labels = [LANGS[k] for k in opts]
    current = st.session_state["lang"]
    idx = opts.index(current) if current in opts else 0

    # Sidebar kullanmak en stabil: üstte UI bozulmuyor
    chosen = st.sidebar.selectbox(
        TEXTS["lang_label"][current],
        options=opts,
        format_func=lambda k: LANGS[k],
        index=idx,
        key="lang_selector",
    )
    st.session_state["lang"] = chosen
    return chosen

def t(key: str, **kwargs) -> str:
    lang = get_lang()
    item = TEXTS.get(key, {})
    s = item.get(lang) or item.get("en") or item.get("tr") or key
    return s.format(**kwargs) if kwargs else s

def trait_label(trait_key: str) -> str:
    lang = get_lang()
    item = TRAITS.get(trait_key, {})
    return item.get(lang) or item.get("en") or item.get("tr") or trait_key

def sign_label(sign_key: str) -> str:
    lang = get_lang()
    for k, names in SIGNS:
        if k == sign_key:
            return names.get(lang) or names.get("en") or names.get("tr") or sign_key
    return sign_key

def sign_keys():
    return [k for k, _ in SIGNS]
