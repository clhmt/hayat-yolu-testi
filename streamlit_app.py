import streamlit as st

# Güvenli import: main.py içinde run_app varsa onu çağırır.
# Yoksa net hata basar (sessiz fail yok).
try:
    from app.main import run_app
except Exception as e:
    st.set_page_config(page_title="IZ", layout="wide")
    st.error(f"ImportError: app.main içinden run_app import edilemedi: {e}")
    st.stop()

run_app()
