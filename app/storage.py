from __future__ import annotations

import json
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
import gspread


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _secrets_sheet_id() -> str:
    if "SHEET_ID" in st.secrets:
        return str(st.secrets["SHEET_ID"])
    if "sheets" in st.secrets and "spreadsheet_id" in st.secrets["sheets"]:
        return str(st.secrets["sheets"]["spreadsheet_id"])
    raise KeyError("SHEET_ID yok. secrets.toml içine SHEET_ID veya [sheets].spreadsheet_id koy.")


def _service_account_info() -> Dict[str, Any]:
    if "gcp_service_account" not in st.secrets:
        raise KeyError("gcp_service_account yok. secrets.toml içine [gcp_service_account] koy.")
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info and isinstance(info["private_key"], str):
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    return info


@st.cache_resource(show_spinner=False)
def _get_gspread_client() -> gspread.Client:
    return gspread.service_account_from_dict(_service_account_info())


@st.cache_resource(show_spinner=False)
def _get_spreadsheet(sheet_id: str):
    client = _get_gspread_client()
    return client.open_by_key(sheet_id)


def _get_worksheet(sheet_id: str, tab_name: str):
    cache_key = f"_ws_cache::{sheet_id}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = {}

    if tab_name in st.session_state[cache_key]:
        return st.session_state[cache_key][tab_name]

    spreadsheet = _get_spreadsheet(sheet_id)
    ws = spreadsheet.worksheet(tab_name)
    st.session_state[cache_key][tab_name] = ws
    return ws


def _safe_json(x: Any) -> str:
    try:
        return json.dumps(x, ensure_ascii=False)
    except Exception:
        return json.dumps(str(x), ensure_ascii=False)


def gsheets_append(tab_name: str, row: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        sheet_id = _secrets_sheet_id()
        ws = _get_worksheet(sheet_id, tab_name)

        header_cache_key = f"_header::{sheet_id}::{tab_name}"
        if header_cache_key in st.session_state:
            header = st.session_state[header_cache_key]
        else:
            header = ws.row_values(1)
            st.session_state[header_cache_key] = header

        if not header:
            return False, f"{tab_name} header boş. İlk satır kolon isimleri olmalı."

        values: List[Any] = []
        for col in header:
            v = row.get(col, "")
            if isinstance(v, (dict, list)):
                v = _safe_json(v)
            values.append(v)

        for attempt in range(4):
            try:
                ws.append_row(values, value_input_option="USER_ENTERED")
                # results okuma cache'ini kır (yeni veri geldi)
                st.cache_data.clear()
                return True, f"Sheets write ok: {tab_name}"
            except Exception as e:
                msg = str(e)
                if "429" in msg or "Quota" in msg:
                    time.sleep(1.2 * (attempt + 1))
                    continue
                raise

        return False, "Sheets ERROR: 429 quota exceeded (append retry limit)."

    except Exception as e:
        tr = traceback.format_exc()
        return False, f"{type(e).__name__}: {e} | trace: {tr}"


@st.cache_data(ttl=30, show_spinner=False)
def gsheets_fetch_recent_results(limit: int = 50, max_rows_scan: int = 1500) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    results tabından son kayıtları getirir.
    Quota'yı korumak için:
      - 30 sn cache
      - max_rows_scan ile aralığı sınırlı (büyürse ayarlarsın)
    """
    try:
        sheet_id = _secrets_sheet_id()
        ws = _get_worksheet(sheet_id, "results")

        header = ws.row_values(1)
        if not header:
            return False, [], "results header boş."

        # Basit ama efektif: A1:Z{max_rows_scan} ile sınırlı okuma
        # (Erken dönemde yeterli; ileride DB’ye geçince ağlamazsın.)
        values = ws.get_values(f"A1:Z{max_rows_scan}")
        if not values or len(values) < 2:
            return True, [], "no data"

        rows = values[1:]  # header hariç
        # Sondan limit kadar al
        rows = rows[-limit:]

        out: List[Dict[str, Any]] = []
        for r in rows:
            d: Dict[str, Any] = {}
            for i, col in enumerate(header):
                d[col] = r[i] if i < len(r) else ""
            # result_json parse
            rj = d.get("result_json", "")
            if rj:
                try:
                    d["_result"] = json.loads(rj)
                except Exception:
                    d["_result"] = {"raw": rj}
            else:
                d["_result"] = d
            out.append(d)

        return True, out, "ok"

    except Exception as e:
        tr = traceback.format_exc()
        return False, [], f"{type(e).__name__}: {e} | trace: {tr}"
