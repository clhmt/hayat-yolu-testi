import streamlit as st
import random

st.set_page_config(page_title="Hayat Yolu Testi", page_icon="🔮", layout="centered")

# -------------------------
# Konfig / İçerik
# -------------------------
ARSHETIPLER = {
    "merak": {
        "ad": "Kaşif",
        "motto": "Cevap değil, doğru soru güç verir.",
        "aciklama": "Yeni fikirlere hızlı açılırsın. Bilmediğin yere gitmek seni korkutmaz; merakın seni taşır.",
        "guc": ["Öğrenme hızı", "Yaratıcı problem çözme", "Fırsatları görme"],
        "risk": ["Dağılma", "Yarım bırakma", "Sürekli seçenek arama"]
    },
    "cesaret": {
        "ad": "Savaşçı",
        "motto": "Korku var diye durmam.",
        "aciklama": "Risk alabilirsin. Karar anında beklemek yerine hamle yapmayı seçersin.",
        "guc": ["Hızlı aksiyon", "Liderlik", "Zor anlarda soğukkanlılık"],
        "risk": ["Acelecilik", "Gereksiz çatışma", "Sabırsızlık"]
    },
    "kontrol": {
        "ad": "Stratejist",
        "motto": "Plan yapan kazanır.",
        "aciklama": "Sistem kurar, işi ölçer, kontrol edersin. Kaosu azaltırsın, düzen kurarsın.",
        "guc": ["Disiplin", "Planlama", "Süreç yönetimi"],
        "risk": ["Aşırı kontrol", "Esneklik kaybı", "Kendini yıpratma"]
    },
    "empati": {
        "ad": "Şifacı",
        "motto": "İnsanı anlamadan hayat anlaşılmaz.",
        "aciklama": "İlişki yönetimi güçlüdür. Ortamı okur, insanları hissedersin.",
        "guc": ["İletişim", "Güven inşası", "Duygusal zekâ"],
        "risk": ["Fazla yük alma", "Sınır koyamama", "Herkesi memnun etmeye çalışma"]
    },
}

# Hikaye sahneleri: (soru_metni, [(secenek_yazisi, etki_dict, mini_sahne_metni), ...])
SORULAR = [
    ("Telefonuna gecenin bir yarısı tek kelime mesaj geliyor: “SEÇ.”",
     [
         ("Mesajı sessize alıp sabah bakarım", {"kontrol": 2}, "Karanlıkta panik yok. Önce kontrol, sonra karar."),
         ("Kim bu diye araştırırım", {"merak": 2}, "İz sürüyorsun. Detaylar sana ipucu gibi geliyor."),
         ("Hemen cevap yazarım: 'Ne seçimi?'", {"cesaret": 2}, "Doğrudan temasa giriyorsun. Cesur, net."),
         ("Arayıp iyi misin diye sorarım", {"empati": 2}, "Önce insan. Durum ne, kimin yardıma ihtiyacı var?"),
     ]),
    ("Ertesi gün yolda yürürken yerde parlak bir anahtar görüyorsun.",
     [
         ("Cebime koyarım, sonra düşünürüm", {"kontrol": 2}, "Kaynak topladın. Ne zaman lazım olacağı belli olmaz."),
         ("Neye ait olabilir diye çevreyi incelerim", {"merak": 2}, "Burası bir sahne. Her şey bir işaret."),
         ("Kapılara bakıp denemek isterim", {"cesaret": 2}, "Denemeden bilemezsin. Risk, bazen kısayoldur."),
         ("Birine ait mi diye etrafa sorarım", {"empati": 2}, "Kayıp eşya değil, belki kayıp bir hikaye."),
     ]),
    ("Bir kafede oturuyorsun. Garson masaya not bırakıyor: “Bugün tek bir alışkanlığını değiştir.”",
     [
         ("Plan yaparım: 7 gün takip ederim", {"kontrol": 2}, "Sürdürülebilir değişim, ölçülebilir olmalı."),
         ("Merak ettiğim yeni bir şeyi denerim", {"merak": 2}, "Rutin kırılırsa zihin açılır."),
         ("Zor olanı seçerim: ertelersem kaybederim", {"cesaret": 2}, "Kendine meydan okuma moduna girdin."),
         ("Birine yardım ederek başlarım", {"empati": 2}, "Değişim en hızlı başkasına dokununca olur."),
     ]),
    ("Birisi sana ‘Çok düşünüyorsun’ diyor. İçinden ne geçiyor?",
     [
         ("Haklı. Basitleştirip sistem kurmalıyım", {"kontrol": 2}, "Düşünceyi sürece çevirme refleksi."),
         ("Düşünmek güzeldir, yeni bağlantılar çıkar", {"merak": 2}, "Zihin haritası sende sürekli çalışır."),
         ("Düşünmek yetmez, hareket şart", {"cesaret": 2}, "Düşünceyi aksiyona çevirmeyi seçiyorsun."),
         ("Belki de beni anlamıyorlar", {"empati": 2}, "İletişim boşluğu hissediyorsun, köprü kurmak istersin."),
     ]),
    ("Gece rüyanda bir yol ayrımı görüyorsun. Solda sis, sağda ışık.",
     [
         ("Işığa giderim, riski azaltırım", {"kontrol": 2}, "Öngörülebilir olanı seçtin."),
         ("Sise giderim, orada bir şey var", {"merak": 2}, "Bilinmeyenin çağrısı güçlü."),
         ("Hiç düşünmem, koşarım", {"cesaret": 2}, "Karar anı uzamaz. Hareket başlar."),
         ("İkisini de denemek için birini çağırırım", {"empati": 2}, "Yolu yalnız yürümek zorunda değilsin."),
     ]),
]

# -------------------------
# Yardımcılar
# -------------------------
def reset_game():
    st.session_state.puan = {k: 0 for k in ARSHETIPLER.keys()}
    st.session_state.adim = 0
    st.session_state.gunluk = []  # sahne logu

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

    # küçük “fal” varyasyonu
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

    # “Kurumsal” ama motive eden aksiyon önerisi
    aksiyon = {
        "merak": "Bu hafta 1 yeni konu seç, 30 dakikalık mikro-öğrenme rutini kur.",
        "cesaret": "48 saat kuralı: Ertelediğin 1 şeyi seç ve 48 saat içinde başlat.",
        "kontrol": "Tek sayfalık plan: Hedef, metrik, ilk adım, risk, B planı yaz.",
        "empati": "İlişki yatırımı: 3 kişiye ‘nasılsın’ mesajı at, somut destek teklif et."
    }[baskin]

    metin = f"""
**Baskın Arketip:** **{a["ad"]}**  
**İkincil Destek:** **{b["ad"]}**

**Motto:** _{a["motto"]}_

{random.choice(girisler)}

### Senin yolun nasıl çalışıyor?
- Güçlerin: {", ".join(a["guc"])}
- Dikkat etmen gereken gölgeler: {", ".join(a["risk"])}

### Bu haftanın net aksiyonu
**{aksiyon}**

{random.choice(kapanislar)}
"""
    return metin

# -------------------------
# UI
# -------------------------
st.title("🔮 Hayat Yolu Testi")
st.caption("Seçim yap. Hikaye ilerlesin. En sonda ‘kader çizgini’ yorumlayayım.")

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🔁 Sıfırla / Yeniden Başla", key="reset"):
        reset_game()
with col2:
    st.write("")  # boşluk
    st.write("")

if "puan" not in st.session_state or "adim" not in st.session_state:
    reset_game()

# İlerleme
st.progress(min(st.session_state.adim / len(SORULAR), 1.0))
st.write(f"İlerleme: **{st.session_state.adim}/{len(SORULAR)}**")

st.divider()

# Oyun akışı
if st.session_state.adim < len(SORULAR):
    soru, secenekler = SORULAR[st.session_state.adim]
    st.subheader(soru)
    st.write("Aşağıdan bir seçenek seç. Seçim ‘etki’ yaratır.")
    for yazi, etki, mini_sahne in secenekler:
        # önemli: key benzersiz olmalı
        if st.button(yazi, key=f"btn_{st.session_state.adim}_{yazi}"):
            uygula(etki, mini_sahne)
            st.rerun()
else:
    st.subheader("📌 Kader Çizgin")
    baskin, ikincil = baskin_ve_ikincil(st.session_state.puan)

    st.success(f"Baskın yönün: **{ARSHETIPLER[baskin]['ad']}**  |  Destek yönün: **{ARSHETIPLER[ikincil]['ad']}**")
    st.markdown(kehanet_metni(baskin, ikincil))

    with st.expander("🎬 Seçim Günlüğün (sahne sahne)"):
        for i, satir in enumerate(st.session_state.gunluk, 1):
            st.write(f"{i}. {satir}")

    st.divider()
    st.write("İstersen soruları ve hikayeyi daha ‘edebi’ hale getirip, sonuç metnini daha ‘fal’ gibi büyütebiliriz.")
