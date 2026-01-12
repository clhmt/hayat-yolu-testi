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
        "name_optional": "Adın ne? (opsiyonel)",
        "show_name_in_matches": "Eşleşme listesinde ismim görünsün",
        "astro_mode": "Astro modu (burç atmosferi ekle)",
        "astro_off": "Astro modu kapalı: Açarsan burç atmosferini de eklerim.",

        
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
        "name_optional": "What's your name? (optional)",
        "show_name_in_matches": "Show my name in the match list",
        "astro_mode": "Astro mode (adds zodiac vibe)",
        "astro_off": "Astro mode is off. Turn it on to add zodiac atmosphere.",

    }
}

def t(lang: str, key: str) -> str:
    lang = lang if lang in TEXT else "tr"
    return TEXT[lang].get(key, TEXT["tr"].get(key, key))
