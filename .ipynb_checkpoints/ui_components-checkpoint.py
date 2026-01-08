import streamlit as st

def uyum_etiketi(sk: int) -> str:
    return (
        "🔥 Çok Uyumlu" if sk >= 85 else
        "✅ Uyumlu" if sk >= 75 else
        "⚠️ Zorlayıcı" if sk >= 60 else
        "🧊 Düşük Uyum"
    )

def render_match_card(
    idx: int,
    ad: str,
    sk: int,
    baskin_text: str,
    ikincil_text: str,
    burc: str,
    neden_maddeler: list[str],
    debug_mode: bool = False,
    debug_text: str | None = None,
):
    etiket = uyum_etiketi(sk)

    with st.container(border=True):
        # ÜST BAR: isim + skor
        left, right = st.columns([3, 1], vertical_alignment="center")
        with left:
            st.markdown(f"### {idx}. {ad}")
            st.caption(f"{baskin_text}  •  {ikincil_text}")
        with right:
            st.markdown(f"## {sk}")
            st.caption(etiket)

        # ALT: burç + neden
        meta1, meta2 = st.columns([1, 2], vertical_alignment="top")
        with meta1:
            st.caption("Burç")
            st.write(burc)
        with meta2:
            st.caption("Neden uyumlu?")
            for m in neden_maddeler[:3]:
                st.write(f"• {m}")

        # detay alanı
        with st.expander("Detay"):
            for m in neden_maddeler:
                st.write(f"• {m}")
            if debug_mode and debug_text:
                st.divider()
                st.caption(debug_text)
