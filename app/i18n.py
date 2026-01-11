# app/i18n.py

TEXT = {
    "tr": {
        "page_title": "Hayat Yolu Testi",
        "title": "🔮 Hayat Yolu Testi",
        "subtitle": "Seçim yap. Hikaye ilerlesin. En sonda 'kader çizgini' yorumlayayım.",
        "sidebar_title": "Ayarlar",
        "language": "Dil",
        "debug": "Debug modu",
        "start_over": "Baştan Başla",
        "download_result": "Sonucu indir (JSON)",
    },
    "en": {
        "page_title": "Life Path Test",
        "title": "🔮 Life Path Test",
        "subtitle": "Make choices. Let the story unfold. At the end, I’ll interpret your path.",
        "sidebar_title": "Settings",
        "language": "Language",
        "debug": "Debug mode",
        "start_over": "Start Over",
        "download_result": "Download result (JSON)",
    }
}

def t(lang: str, key: str) -> str:
    lang = lang if lang in TEXT else "tr"
    return TEXT[lang].get(key, TEXT["tr"].get(key, key))
