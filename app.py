import os
import io
import json
import hashlib
import requests
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import calendar
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(__file__)
# On Railway, set DATA_DIR to the path of a persistent volume (e.g. /data).
# Locally it defaults to the app directory so nothing changes.
DATA_DIR = os.getenv("DATA_DIR", BASE_DIR)
os.makedirs(DATA_DIR, exist_ok=True)

# Load token from the data dir .env first (persisted by _update_env on Railway)
_data_env = os.path.join(DATA_DIR, ".env")
if os.path.exists(_data_env):
    load_dotenv(_data_env, override=True)

XERO_CLIENT_ID        = os.getenv("XERO_CLIENT_ID")
XERO_CLIENT_SECRET    = os.getenv("XERO_CLIENT_SECRET")
XERO_TENANT_ID        = os.getenv("XERO_TENANT_ID")
XERO_WHT_ACCOUNT_CODE = os.getenv("XERO_WHT_ACCOUNT_CODE", "627")
ENV_FILE       = _data_env
ACCOUNTS_FILE  = os.path.join(BASE_DIR, "accounts.json")
COA_FILE       = os.path.join(BASE_DIR, "chart_of_accounts.csv")

# ── Xero Tracking Categories ──────────────────────────────────────────────────

XERO_DEPARTMENTS = [
    "", "BI & Analytics", "Business Development", "Customer Experience",
    "Engineering", "Executive", "Finance", "Home", "Human Resources",
    "International Expansion", "Legal", "Marketing", "Operations", "Product",
    "Retrenchments", "Support", "Technology",
]

XERO_CHANNELS = [
    "", "Abdel Aziz El Sallab", "ABT", "Ahmed El Sallab", "AL MAHGOUB",
    "Amazon", "Amazon (LCM)", "Amazon Non UDS", "Amazon SPX", "APT",
    "Belda App", "Brain and Nerve Center", "Burouj", "Cario Gate", "City Edge",
    "Duravit Egypt", "El Araby",
    "Emaar Misr, Marassi Development (North Cost Safe)",
    "Fridge for Restaurant Management (Zooba)", "G-Express", "Grome", "GS1",
    "HBS for Petroleum Services", "Head office", "Katameya Office Building",
    "Marina El Alamein (North Cost Safe)", "Marketplace", "Materials",
    "Mivida (Emaar)", "Mostafa El Sallab", "opex", "Orion", "Raya", "RHI",
    "Taktuf", "Techne Summit organizers", "Telal (North Cost Safe)",
    "Upstream Projects", "Uptown (Emaar)", "Workmanship",
]

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="CIB → Xero", page_icon="🏦", layout="wide")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&display=swap');

  :root {
    --khaki:      #94aedf;
    --khaki-50:   rgba(148,174,223,0.5);
    --khaki-10:   rgba(148,174,223,0.1);
    --taupe:      #5b5449;
    --off-white:  #f3f4ee;
    --midnight:   #0a0a0a;
    --green:      #3b4b30;
  }

  html, body, [class*="css"] {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    background-color: #ffffff !important;
    color: var(--midnight) !important;
  }

  /* Hide streamlit chrome */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding: 48px 80px !important; max-width: 1200px !important; }

  /* Headings */
  h1 { font-size: 20px !important; font-weight: 400 !important; line-height: 24px !important; }
  h2 { font-size: 15px !important; font-weight: 500 !important; line-height: 24px !important; }
  h3 { font-size: 15px !important; font-weight: 500 !important; line-height: 24px !important; }
  p, li, span, label { font-size: 15px !important; line-height: 24px !important; }

  /* Caption / muted */
  .muted { color: var(--taupe); font-size: 13px !important; }

  /* Divider */
  hr { border: none; border-top: 1.5px solid var(--khaki-10) !important; margin: 24px 0 !important; }

  /* File uploader */
  [data-testid="stFileUploader"] {
    background: white;
    border: 1.5px solid var(--khaki-10);
    border-radius: 12px;
    padding: 16px;
    transition: border-color 0.2s ease;
  }
  [data-testid="stFileUploader"]:hover { border-color: var(--khaki-50); }

  /* Metric cards */
  [data-testid="stMetric"] {
    background: white;
    border: 1.5px solid var(--khaki-10);
    border-radius: 12px;
    padding: 16px 20px !important;
  }
  [data-testid="stMetricLabel"] { font-size: 12px !important; font-weight: 500 !important;
    text-transform: uppercase; letter-spacing: 0.04em; color: var(--taupe) !important; }
  [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 400 !important; }

  /* Buttons */
  .stButton > button {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 15px !important;
    font-weight: 400 !important;
    border-radius: 8px !important;
    border: 1.5px solid var(--midnight) !important;
    background: var(--midnight) !important;
    color: white !important;
    padding: 8px 20px !important;
    transition: opacity 0.05s ease !important;
    height: auto !important;
  }
  .stButton > button:hover { opacity: 0.8 !important; }
  .stButton > button[kind="secondary"] {
    background: transparent !important;
    color: var(--midnight) !important;
  }

  /* Tabs */
  [data-testid="stTabs"] [role="tablist"] {
    gap: 0 !important;
    border-bottom: 1.5px solid var(--khaki-10);
    margin-bottom: 24px;
  }
  [data-testid="stTabs"] button[role="tab"] {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 15px !important;
    font-weight: 400 !important;
    color: var(--taupe) !important;
    padding: 8px 16px !important;
    border-radius: 0 !important;
    background: transparent !important;
    border: none !important;
    opacity: 0.6;
    transition: opacity 0.05s ease;
  }
  [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    opacity: 1 !important;
    color: var(--midnight) !important;
    border-bottom: 2px solid var(--midnight) !important;
    font-weight: 500 !important;
  }
  [data-testid="stTabs"] button[role="tab"]:hover { opacity: 0.8; }

  /* Expander */
  [data-testid="stExpander"] {
    border: 1.5px solid var(--khaki-10) !important;
    border-radius: 12px !important;
    background: white;
  }
  [data-testid="stExpander"] summary { font-size: 15px !important; padding: 12px 16px !important; }

  /* Dataframe — make cells selectable/copyable */
  [data-testid="stDataFrame"] { border-radius: 12px !important; overflow: hidden; }
  [data-testid="stDataFrame"] iframe { border-radius: 12px !important; }

  /* Select box / inputs */
  [data-testid="stSelectbox"] > div > div,
  [data-testid="stDateInput"] > div > div {
    border: 1.5px solid var(--khaki-10) !important;
    border-radius: 8px !important;
    font-size: 15px !important;
    background: white !important;
  }

  /* Status badge helpers */
  .badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .badge-new  { background: #e5eafe; color: #1a3a8f; }
  .badge-done { background: #e8eadd; color: var(--taupe); }
  .badge-warn { background: rgba(196,149,76,0.2); color: #7a5c20; }

  /* Info / warning / success override */
  [data-testid="stAlert"] {
    border-radius: 8px !important;
    font-size: 15px !important;
  }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_processed_ids(log_file: str) -> set:
    if os.path.exists(log_file):
        with open(log_file) as f:
            return set(json.load(f))
    return set()


def save_processed_ids(ids: set, log_file: str):
    with open(log_file, "w") as f:
        json.dump(list(ids), f, indent=2)


def make_tx_id(row):
    fp = f"{row['date']}|{row['description']}|{row['debit']}|{row['credit']}"
    return hashlib.sha256(fp.encode()).hexdigest()[:16]


def read_csv_any_encoding(file, **kwargs) -> pd.DataFrame:
    """Try common encodings × separators; return the first that parses cleanly.
    Separators tried: tab, comma, semicolon, pipe.
    Only UnicodeDecodeError triggers the encoding retry loop."""
    encodings  = ["utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]
    separators = ["\t", ",", ";", "|"]
    last_err   = None
    for enc in encodings:
        for sep in separators:
            try:
                if hasattr(file, "seek"):
                    file.seek(0)
                df = pd.read_csv(file, encoding=enc, sep=sep, **kwargs)
                # Reject single-column results — delimiter probably wrong
                if len(df.columns) > 1:
                    return df
                last_err = ValueError(f"Only 1 column detected with sep={sep!r} enc={enc}")
            except UnicodeDecodeError as e:
                last_err = e
                break          # wrong encoding — try next one
            except Exception as e:
                last_err = e   # wrong separator or bad row — try next
    raise ValueError(f"Could not parse file: {last_err}")


def clean_amount(val):
    if pd.isna(val) or str(val).strip() == "":
        return 0.0
    return float(str(val).replace(",", "").strip())


def is_ach_corpay(description: str) -> bool:
    return "Online - ACH Corpay" in description


# ── Accounts config ───────────────────────────────────────────────────────────

def load_accounts() -> list:
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE) as f:
            return json.load(f)
    # Fallback: single EGP account from env
    return [{
        "id": "egp", "name": "CIB EGP",
        "xero_bank_account_id": os.getenv("XERO_BANK_ACCOUNT_ID", ""),
        "default_account_code": os.getenv("XERO_DEFAULT_ACCOUNT_CODE", "850"),
        "rules_file": "rules_egp.json",
        "processed_log": "processed_egp.json",
        "xero_ids_log": "xero_ids_egp.json",
    }]


# ── Chart of accounts ─────────────────────────────────────────────────────────

@st.cache_data
def load_coa() -> dict:
    """Returns {code: name} lookup."""
    if not os.path.exists(COA_FILE):
        return {}
    df = pd.read_csv(COA_FILE)
    df.columns = df.columns.str.strip().str.lstrip("*")
    df = df.dropna(subset=["Code"])
    df["Code"] = df["Code"].astype(str).str.strip()
    return dict(zip(df["Code"], df["Name"]))


@st.cache_data
def load_bank_account_codes() -> set:
    """Return set of account codes whose Type == 'Bank'.
    These cannot be used as line-item AccountCode in Xero BankTransactions."""
    if not os.path.exists(COA_FILE):
        return set()
    df = pd.read_csv(COA_FILE)
    df.columns = df.columns.str.strip().str.lstrip("*")
    df = df.dropna(subset=["Code"])
    df["Code"] = df["Code"].astype(str).str.strip()
    df["Type"] = df["Type"].astype(str).str.strip()
    return set(df.loc[df["Type"].str.lower() == "bank", "Code"].tolist())


# ── Rules engine ──────────────────────────────────────────────────────────────

def load_rules(rules_file: str) -> list:
    if os.path.exists(rules_file):
        with open(rules_file) as f:
            return json.load(f)
    return []


def save_rules(rules: list, rules_file: str):
    with open(rules_file, "w") as f:
        json.dump(rules, f, indent=2)


def _extract_payer_name(description: str) -> str:
    """Extract Payer Name from CIB IPN descriptions."""
    import re
    # Pattern: "Payer Name: NAME Living Expenses"
    m = re.search(r"Payer Name:\s*(.+?)\s+Living Expenses", description)
    if m:
        return m.group(1).strip()
    # Fallback: everything after "Payer Name: " up to " - "
    m = re.search(r"Payer Name:\s*(.+?)(?:\s+-\s+|\s+Total Fees)", description)
    if m:
        return m.group(1).strip()
    return "Unknown Payer"


def apply_rules(description: str, rules: list, default_account_code: str = "850",
                direction: str = "") -> dict:
    """
    Returns classification dict for the first matching rule.
    `direction` is "debit" or "credit"; rules with `applies_to` only match when directions align.
    Rules with `transfer_to_account_id` flag the row as an interbank transfer send.
    Rules with `skip_as_transfer_receipt` flag the row to be skipped (other side posts the transfer).
    """
    for rule in rules:
        keyword = rule.get("match_contains", "")
        if not keyword or keyword.lower() not in description.lower():
            continue
        applies_to = rule.get("applies_to", "")
        if applies_to and direction and applies_to != direction:
            continue
        contact = rule.get("contact", "CIB Bank Import")
        if contact == "extract:payer_name":
            contact = _extract_payer_name(description)
        return {
            "contact":                  contact,
            "narration":                rule.get("narration") or description[:255],
            "account_code":             rule.get("account_code", default_account_code),
            "rule_id":                  rule.get("id", ""),
            "transfer_to_account_id":   rule.get("transfer_to_account_id", ""),
            "skip_as_transfer_receipt": bool(rule.get("skip_as_transfer_receipt", False)),
            "export_only":              bool(rule.get("export_only", False)),
            "department":               rule.get("department", "") or "",
            "channel":                  rule.get("channel", "") or "",
        }
    return {
        "contact":                  "CIB Bank Import",
        "narration":                description[:255],
        "account_code":             default_account_code,
        "rule_id":                  "",
        "transfer_to_account_id":   "",
        "skip_as_transfer_receipt": False,
        "export_only":              False,
        "department":               "",
        "channel":                  "",
    }


# ── Parsers ───────────────────────────────────────────────────────────────────

def parse_statement(file, rules: list, default_account_code: str = "850") -> pd.DataFrame:
    # Auto-detect the header row by scanning for the row containing "Posting Date"
    raw = read_csv_any_encoding(file, header=None, on_bad_lines="skip")
    if hasattr(file, "seek"):
        file.seek(0)
    header_row = 3  # fallback
    for i, row in raw.iterrows():
        vals = [str(v).strip() for v in row if pd.notna(v)]
        if any("Posting Date" in v or "posting date" in v.lower() for v in vals):
            header_row = i
            break
    if hasattr(file, "seek"):
        file.seek(0)
    df = read_csv_any_encoding(file, header=header_row, on_bad_lines="skip")
    df.columns = df.columns.str.strip()
    df = df.rename(columns={
        "Posting Date":        "date",
        "BackOffice Reference": "reference",
        "Description":         "description",
        "Withdrawal":          "debit",
        "Deposit":             "credit",
    })
    df = df.dropna(subset=["date"])
    df["date"] = pd.to_datetime(df["date"].str.strip(), dayfirst=True, errors="coerce").dt.date
    df = df.dropna(subset=["date"])
    df["debit"]       = df["debit"].apply(clean_amount)
    df["credit"]      = df["credit"].apply(clean_amount)
    df["description"] = df["description"].fillna("CIB Transaction").str.strip()
    df["reference"]   = df.get("reference", pd.Series(dtype=str)).fillna("").str.strip()
    df["is_batch"]    = df["description"].apply(is_ach_corpay)
    df["tx_id"]       = df.apply(make_tx_id, axis=1)

    # Apply rules to derive contact, narration, account_code, and transfer flags
    applied = df.apply(
        lambda r: apply_rules(
            r["description"], rules, default_account_code,
            "debit" if r["debit"] > 0 else "credit",
        ),
        axis=1,
    )
    df["contact"]                  = applied.apply(lambda x: x["contact"])
    df["narration"]                = applied.apply(lambda x: x["narration"])
    df["account_code"]             = applied.apply(lambda x: x["account_code"])
    df["rule_id"]                  = applied.apply(lambda x: x["rule_id"])
    df["transfer_to_account_id"]   = applied.apply(lambda x: x["transfer_to_account_id"])
    df["is_transfer_send"]         = df["transfer_to_account_id"].astype(bool)
    df["is_transfer_skip"]         = applied.apply(lambda x: x["skip_as_transfer_receipt"])
    df["is_export_only"]           = applied.apply(lambda x: x["export_only"])
    df["department"]               = applied.apply(lambda x: x["department"])
    df["channel"]                  = applied.apply(lambda x: x["channel"])

    return df[["date", "description", "debit", "credit", "reference",
               "is_batch", "tx_id", "contact", "narration", "account_code", "rule_id",
               "transfer_to_account_id", "is_transfer_send", "is_transfer_skip",
               "is_export_only", "department", "channel"]]


def parse_batch_detail(file, batch_date: date, batch_reference: str,
                       rules: list = None, default_account_code: str = "850") -> tuple[pd.DataFrame, dict]:
    """
    Parse a batch detail file (CSV or Excel).
    Returns (dataframe, mapping_info) where mapping_info describes which columns were found.
    Auto-detects header row and handles a wide range of column names.
    """
    _HEADER_KEYWORDS = {
        "description", "narration", "amount", "debit", "credit", "name",
        "beneficiary", "employee", "salary", "net", "withdrawal", "deposit", "date",
    }
    _DATE_NAMES    = {"date", "posting date", "transaction date", "value date", "payment date"}
    _DESC_NAMES    = {
        "description", "narration", "details", "particulars",
        "comment", "comments", "payment details", "payment description",
        "remarks", "purpose", "note", "notes",
    }
    _CONTACT_NAMES = {
        "creditor name", "creditor", "beneficiary", "beneficiary name",
        "payee", "payee name", "recipient", "employee name", "employee",
        "name", "account name", "account holder",
    }
    _REF_NAMES = {
        "reference", "ref", "reference no", "reference number", "ref no",
        "ref number", "payment ref", "payment reference", "transaction ref",
        "transaction reference", "txn ref", "voucher", "voucher no",
        "check number", "cheque number", "cheque no",
        "batch reference", "batch ref", "batch no", "batch number",
    }
    _DEBIT_NAMES = {
        "amount", "debit", "withdrawal", "net amount", "net salary", "net pay",
        "salary", "payment amount", "transfer amount", "paid amount", "net",
        "gross amount", "gross salary", "gross", "total amount", "total",
        "transaction amount", "txn amount", "tran amount",
    }
    _CREDIT_NAMES = {"credit", "deposit"}

    def _find_header_row(raw_df):
        best_row, best_score = 0, 0
        for i, row in raw_df.iterrows():
            vals = [str(v).strip().lower() for v in row if pd.notna(v) and str(v).strip()]
            score = sum(1 for v in vals if any(k in v for k in _HEADER_KEYWORDS))
            if score > best_score:
                best_score, best_row = score, i
        return best_row

    name = getattr(file, "name", "")
    if name.endswith((".xlsx", ".xls")):
        data = file.read()
        raw  = pd.read_excel(io.BytesIO(data), header=None)
        header_row = _find_header_row(raw)
        df = pd.read_excel(io.BytesIO(data), header=header_row)
    else:
        raw = read_csv_any_encoding(file, header=None, on_bad_lines="skip")
        if hasattr(file, "seek"):
            file.seek(0)
        header_row = _find_header_row(raw)
        if hasattr(file, "seek"):
            file.seek(0)
        df = read_csv_any_encoding(file, header=header_row, on_bad_lines="skip")

    df.columns = df.columns.astype(str).str.strip().str.lower()

    # Map columns — track what was found for UI feedback
    col_map     = {}
    mapped_from = {}
    for c in df.columns:
        if c in _DATE_NAMES    and "date"        not in col_map.values():
            col_map[c] = "date";        mapped_from["date"]        = c
        elif c in _CONTACT_NAMES and "contact"   not in col_map.values():
            col_map[c] = "contact";     mapped_from["contact"]     = c
        elif c in _DESC_NAMES  and "description" not in col_map.values():
            col_map[c] = "description"; mapped_from["description"]  = c
        elif c in _REF_NAMES   and "reference"   not in col_map.values():
            col_map[c] = "reference";   mapped_from["reference"]   = c
        elif c in _DEBIT_NAMES and "debit"       not in col_map.values():
            col_map[c] = "debit";       mapped_from["debit"]        = c
        elif c in _CREDIT_NAMES and "credit"     not in col_map.values():
            col_map[c] = "credit";      mapped_from["credit"]       = c

    df = df.rename(columns=col_map)

    # Fallback: if still no debit column, find the first numeric column (>50 % numeric values)
    if "debit" not in df.columns:
        skip = {"date", "description", "credit", "reference"}
        for c in df.columns:
            if c in skip:
                continue
            numeric = pd.to_numeric(
                df[c].astype(str).str.replace(",", "").str.strip(), errors="coerce"
            )
            if numeric.notna().sum() > len(df) * 0.5 and numeric.sum() > 0:
                df["debit"]         = numeric.fillna(0)
                mapped_from["debit"] = f"{c} (auto-detected)"
                break

    # Date
    if "date" not in df.columns:
        df["date"] = batch_date
    else:
        df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce").dt.date
        df["date"] = df["date"].fillna(batch_date)

    if "description" not in df.columns:
        df["description"] = "Batch item"

    df["debit"]  = df["debit"].apply(clean_amount)  if "debit"  in df.columns else pd.Series([0.0]*len(df))
    df["credit"] = df["credit"].apply(clean_amount) if "credit" in df.columns else pd.Series([0.0]*len(df))

    # Drop empty description rows and likely footer/total rows
    df = df.dropna(subset=["description"])
    df = df[df["description"].astype(str).str.strip() != ""]
    df = df[~df["description"].astype(str).str.lower().str.strip().isin(
        ["total", "grand total", "sub total", "subtotal"]
    )]

    # Contact: use mapped column if present, else blank (will show as CIB Bank Import later)
    if "contact" not in df.columns:
        df["contact"] = ""
    else:
        df["contact"] = df["contact"].fillna("").astype(str).str.strip()

    # Apply rules to get account_code, department, channel, narration
    if rules:
        applied = df["description"].apply(
            lambda d: apply_rules(d, rules, default_account_code, "debit")
        )
        df["account_code"] = applied.apply(lambda x: x["account_code"])
        df["narration"]    = df["description"].astype(str).str.strip()   # narration = Comment text
        df["department"]   = applied.apply(lambda x: x["department"])
        df["channel"]      = applied.apply(lambda x: x["channel"])
        df["rule_id"]      = applied.apply(lambda x: x["rule_id"])
        # Use rule contact only when file gave no contact for this row
        rule_contacts = applied.apply(lambda x: x["contact"])
        df["contact"] = df["contact"].where(df["contact"] != "", rule_contacts)
    else:
        df["account_code"] = default_account_code
        df["narration"]    = df["description"].astype(str).str.strip()
        df["department"]   = ""
        df["channel"]      = ""
        df["rule_id"]      = ""

    # Use reference column from file if present; fall back to batch_reference
    if "reference" in df.columns:
        df["reference"] = df["reference"].fillna("").astype(str).str.strip()
        df["reference"] = df["reference"].where(df["reference"] != "", batch_reference)
    else:
        df["reference"] = batch_reference
    df["is_batch"]         = False
    df["is_transfer_send"] = False
    df["is_transfer_skip"] = False
    df["is_export_only"]   = False
    df["tx_id"]            = df.apply(make_tx_id, axis=1)

    mapping_info = {
        "header_row":  header_row,
        "raw_columns": list(raw.iloc[header_row].astype(str).tolist()) if header_row < len(raw) else [],
        "mapped":      mapped_from,
    }
    return df[["date", "description", "debit", "credit", "reference", "is_batch", "tx_id",
               "contact", "narration", "account_code", "rule_id",
               "department", "channel",
               "is_transfer_send", "is_transfer_skip", "is_export_only"]], mapping_info


# ── Xero ──────────────────────────────────────────────────────────────────────

def get_xero_token() -> str:
    refresh_token = os.getenv("XERO_REFRESH_TOKEN")
    r = requests.post(
        "https://identity.xero.com/connect/token",
        auth=(XERO_CLIENT_ID, XERO_CLIENT_SECRET),
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
    )
    r.raise_for_status()
    data = r.json()
    new_refresh = data["refresh_token"]
    _update_env("XERO_REFRESH_TOKEN", new_refresh)
    os.environ["XERO_REFRESH_TOKEN"] = new_refresh
    return data["access_token"]


def _update_env(key: str, value: str):
    lines = open(ENV_FILE).readlines() if os.path.exists(ENV_FILE) else []
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}\n")
    with open(ENV_FILE, "w") as f:
        f.writelines(lines)


def xero_headers(token: str) -> dict:
    return {
        "Authorization":  f"Bearer {token}",
        "Xero-Tenant-Id": XERO_TENANT_ID,
        "Accept":         "application/json",
        "Content-Type":   "application/json",
    }


def _parse_xero_date(s: str) -> str:
    try:
        ms = int(s.replace("/Date(", "").split("+")[0].split("-")[0])
        return datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d")
    except Exception:
        return ""


def fetch_xero_transactions(token: str, date_from: date, date_to: date,
                             bank_account_id: str = "") -> set:
    where = (
        f'BankAccount.AccountID=Guid("{bank_account_id}")'
        f'&&Date>=DateTime({date_from.year},{date_from.month},{date_from.day})'
        f'&&Date<=DateTime({date_to.year},{date_to.month},{date_to.day})'
        f'&&Status!="DELETED"'
    )
    existing, page = set(), 1
    while True:
        r = requests.get(
            "https://api.xero.com/api.xro/2.0/BankTransactions",
            headers=xero_headers(token),
            params={"where": where, "page": page},
        )
        if r.status_code != 200:
            break
        txs = r.json().get("BankTransactions", [])
        if not txs:
            break
        for tx in txs:
            xero_date  = _parse_xero_date(tx.get("Date", ""))
            amount     = float(tx.get("Total", tx.get("Amount", 0)))
            ref        = (tx.get("Reference") or "").strip()
            narration  = (tx.get("Narration") or "").strip()
            backoffice = (ref or narration).split(" ")[0].split("-")[0].strip()
            existing.add(f"{xero_date}|{amount:.2f}|{backoffice}")
        page += 1
    return existing


def make_xero_key(row) -> str:
    amount     = row["debit"] if row["debit"] > 0 else row["credit"]
    backoffice = row["reference"].split(" ")[0].split("-")[0].strip()
    return f"{row['date']}|{amount:.2f}|{backoffice}"


def post_to_xero(df: pd.DataFrame, token: str,
                 bank_account_id: str = "", default_account_code: str = "850",
                 xero_ids_log: str = ""):
    bank_codes   = load_bank_account_codes()   # codes that can't be line-item accounts
    transactions = []
    invalid_codes_seen: set = set()

    for _, row in df.iterrows():
        is_spend = row["debit"] > 0
        amount   = float(row["debit"] if is_spend else row["credit"])
        contact      = str(row.get("contact", "CIB Bank Import") or "CIB Bank Import")
        narration    = str(row.get("narration", row["description"]) or row["description"])[:255]
        account_code = str(row.get("account_code", default_account_code) or default_account_code)

        # Xero rejects Bank-type accounts as line-item codes — fall back to suspense
        if account_code in bank_codes:
            invalid_codes_seen.add(account_code)
            account_code = default_account_code

        # Build tracking categories (only include non-blank selections)
        tracking = []
        dept = str(row.get("department", "") or "").strip()
        chan = str(row.get("channel", "") or "").strip()
        if dept:
            tracking.append({"Name": "Department", "Option": dept})
        if chan:
            tracking.append({"Name": "Channels", "Option": chan})

        line_item = {
            "Description": narration,
            "UnitAmount":  amount,
            "AccountCode": account_code,
            "TaxType":     "NONE",
            "Quantity":    1,
        }
        if tracking:
            line_item["Tracking"] = tracking

        transactions.append({
            "Type":        "SPEND" if is_spend else "RECEIVE",
            "Date":        str(row["date"]),
            "Amount":      amount,
            "Reference":   (str(row.get("reference") or row["description"]))[:255],
            "Narration":   narration,
            "Contact":     {"Name": contact},
            "BankAccount": {"AccountID": bank_account_id},
            "IsReconciled": False,
            "LineItems": [line_item],
        })

    if invalid_codes_seen:
        st.warning(
            f"⚠ Account code(s) {', '.join(sorted(invalid_codes_seen))} are Bank-type accounts "
            f"and can't be used as line-item codes. Those transactions were posted to "
            f"{default_account_code} (Suspense) instead. Update the rule to use a non-bank account."
        )
    posted, errors = 0, []
    xero_ids = _load_xero_ids(xero_ids_log)

    for i in range(0, len(transactions), 50):
        batch = transactions[i : i + 50]
        r = requests.post(
            "https://api.xero.com/api.xro/2.0/BankTransactions",
            headers=xero_headers(token),
            json={"BankTransactions": batch},
        )
        if r.status_code == 200:
            posted += len(batch)
            for tx in r.json().get("BankTransactions", []):
                xero_id = tx.get("BankTransactionID")
                ref     = tx.get("Reference", "")
                if xero_id:
                    xero_ids[ref] = xero_id
        else:
            errors.append(r.text)

    _save_xero_ids(xero_ids, xero_ids_log)
    return posted, errors


def post_bank_transfers(df: pd.DataFrame, token: str, from_account_id: str) -> tuple[int, list]:
    """
    Post interbank transfers via the Xero BankTransfers API.
    Each row in df must have a non-empty `transfer_to_account_id`.
    The BankTransfers API automatically creates the debit on the FROM account
    and the credit on the TO account — no separate BankTransaction needed on either side.
    """
    posted, errors = 0, []
    for _, row in df.iterrows():
        to_account_id = str(row.get("transfer_to_account_id", "")).strip()
        if not to_account_id:
            errors.append(f"{row['date']}: missing transfer_to_account_id in rule")
            continue
        amount = float(row["debit"] if row["debit"] > 0 else row["credit"])
        r = requests.post(
            "https://api.xero.com/api.xro/2.0/BankTransfers",
            headers=xero_headers(token),
            json={"BankTransfers": [{
                "FromBankAccount": {"AccountID": from_account_id},
                "ToBankAccount":   {"AccountID": to_account_id},
                "Amount":          round(amount, 2),
                "Date":            str(row["date"]),
                "Reference":       str(row.get("reference", ""))[:255],
            }]},
        )
        if r.status_code == 200:
            posted += 1
        else:
            try:
                resp = r.json()
                val_msgs = []
                for el in resp.get("Elements", []):
                    for ve in el.get("ValidationErrors", []):
                        val_msgs.append(ve.get("Message", ""))
                    for acct_key in ("FromBankAccount", "ToBankAccount"):
                        for ve in el.get(acct_key, {}).get("ValidationErrors", []):
                            val_msgs.append(f"{acct_key}: {ve.get('Message','')}")
                detail = "; ".join(val_msgs) if val_msgs else resp.get("Message", r.text)
            except Exception:
                detail = r.text
            errors.append(
                f"{row['date']} {amount:.2f} | FROM={from_account_id} "
                f"TO={to_account_id} | {detail}"
            )
    return posted, errors


def build_xero_import_csv(df: pd.DataFrame) -> bytes:
    """
    Format a DataFrame of transactions as a Xero Statement Import CSV.
    Columns: *Date, *Amount, Payee, Description, Reference, Check Number
    Amount is negative for debits (money out), positive for credits (money in).
    """
    rows = []
    for _, row in df.iterrows():
        if row["debit"] > 0:
            amount = -abs(float(row["debit"]))
        else:
            amount = abs(float(row["credit"]))
        rows.append({
            "*Date":        pd.Timestamp(row["date"]).strftime("%m/%d/%Y"),
            "*Amount":      f"{amount:.2f}",
            "Payee":        str(row.get("contact", "") or ""),
            "Description":  str(row.get("narration", row.get("description", "")) or "")[:255],
            "Reference":    str(row.get("reference", "") or "")[:255],
            "Check Number": "",
        })
    out = io.StringIO()
    pd.DataFrame(rows).to_csv(out, index=False)
    return out.getvalue().encode("utf-8")


def _load_xero_ids(log_file: str = "") -> dict:
    if log_file and os.path.exists(log_file):
        with open(log_file) as f:
            return json.load(f)
    return {}


def _save_xero_ids(ids: dict, log_file: str = ""):
    if log_file:
        with open(log_file, "w") as f:
            json.dump(ids, f, indent=2)


def fetch_outstanding_invoices(
    token: str,
    invoice_type: str = "BOTH",
    date_from: date = None,
    date_to: date = None,
) -> list:
    """
    Fetch AUTHORISED invoices with AmountDue > 0.
    Date filter is applied via the API WHERE clause (keeps pagination sane across 280k+ invoices).
    AmountDue > 0 is checked in Python (not reliably filterable via Xero WHERE).
    """
    headers = xero_headers(token)
    results = []
    for itype in (["ACCREC", "ACCPAY"] if invoice_type == "BOTH" else [invoice_type]):
        where = f'Type=="{itype}"&&Status=="AUTHORISED"'
        if date_from:
            where += f"&&Date>=DateTime({date_from.year},{date_from.month},{date_from.day})"
        if date_to:
            where += f"&&Date<=DateTime({date_to.year},{date_to.month},{date_to.day})"
        page = 1
        while True:
            r = requests.get(
                "https://api.xero.com/api.xro/2.0/Invoices",
                headers=headers,
                params={"where": where, "page": page},
            )
            if r.status_code != 200:
                st.error(f"Xero Invoices API error (page {page}): {r.status_code} — {r.text[:300]}")
                break
            invs = r.json().get("Invoices", [])
            if not invs:
                break
            for inv in invs:
                if float(inv.get("AmountDue", 0)) > 0:
                    results.append(inv)
            page += 1
    return results


def post_payment(invoice_id: str, amount: float, date_str: str, token: str,
                 bank_account_id: str = "") -> tuple[bool, str]:
    """Post a payment linking a bank transaction to an invoice."""
    r = requests.post(
        "https://api.xero.com/api.xro/2.0/Payments",
        headers=xero_headers(token),
        json={"Payments": [{
            "Invoice":  {"InvoiceID": invoice_id},
            "Account":  {"AccountID": bank_account_id},
            "Amount":   amount,
            "Date":     date_str,
        }]},
    )
    if r.status_code == 200:
        return True, ""
    return False, r.text


def create_wht_credit_note(
    invoice_id: str,
    contact_name: str,
    invoice_number: str,
    wht_amount: float,
    date_str: str,
    token: str,
) -> tuple[bool, str]:
    """
    Create an ACCREC credit note for the WHT amount (account 627 WHT Receivable),
    with description = invoice number and reference = "Deduct from Account",
    then allocate it to the invoice to reduce the outstanding balance.
    """
    headers = xero_headers(token)

    r = requests.post(
        "https://api.xero.com/api.xro/2.0/CreditNotes",
        headers=headers,
        json={"CreditNotes": [{
            "Type": "ACCREC",
            "Contact": {"Name": contact_name},
            "Date": date_str,
            "Status": "AUTHORISED",
            "Reference": "Deduct from Account",
            "LineItems": [{
                "Description": invoice_number,
                "UnitAmount": round(wht_amount, 2),
                "Quantity": 1,
                "AccountCode": XERO_WHT_ACCOUNT_CODE,
            }],
        }]},
    )
    if r.status_code != 200:
        return False, r.text

    cn_list = r.json().get("CreditNotes", [])
    if not cn_list:
        return False, f"No CreditNotes in response: {r.text}"
    cn_id = cn_list[0].get("CreditNoteID")
    if not cn_id:
        return False, f"No CreditNoteID in response: {r.text}"

    r2 = requests.put(
        f"https://api.xero.com/api.xro/2.0/CreditNotes/{cn_id}/Allocations",
        headers=headers,
        json={"Allocations": [{
            "Invoice": {"InvoiceID": invoice_id},
            "Amount": round(wht_amount, 2),
        }]},
    )
    if r2.status_code != 200:
        return False, f"Credit note created (ID {cn_id}) but allocation failed: {r2.text}"
    return True, ""


def void_xero_transactions(xero_ids: list[str], token: str):
    """Set a list of BankTransactionIDs to DELETED in Xero."""
    payload = {"BankTransactions": [
        {"BankTransactionID": xid, "Status": "DELETED"} for xid in xero_ids
    ]}
    voided, errors = 0, []
    for i in range(0, len(xero_ids), 50):
        batch_ids = xero_ids[i : i + 50]
        r = requests.post(
            "https://api.xero.com/api.xro/2.0/BankTransactions",
            headers=xero_headers(token),
            json={"BankTransactions": [
                {"BankTransactionID": xid, "Status": "DELETED"} for xid in batch_ids
            ]},
        )
        if r.status_code == 200:
            voided += len(batch_ids)
        else:
            errors.append(r.text)
    return voided, errors


def display_df(df: pd.DataFrame, show_rules: bool = False):
    """Render as HTML table with inline column filters and drag-to-select."""
    import uuid
    d = df.copy()
    d["type"]   = d.apply(lambda r: "Spend" if r["debit"] > 0 else "Receive", axis=1)
    d["amount"] = d.apply(lambda r: r["debit"] if r["debit"] > 0 else r["credit"], axis=1)
    d["amount"] = d["amount"].map(lambda x: f"{x:,.2f}")
    cols = ["date", "type", "amount", "description", "reference"]
    if "is_batch" in d.columns:
        d["batch"] = d["is_batch"].map(lambda x: "⚠ Batch" if x else "")
        cols.append("batch")
    if show_rules and "contact" in d.columns:
        cols += ["contact", "narration", "account_code"]
    d = d[cols]

    tid = f"t{uuid.uuid4().hex[:8]}"

    # Build filter inputs per column — dropdown for low-cardinality, text for rest
    DROPDOWN_COLS = {"type", "account_code", "contact", "batch", "rule_id"}
    header_row1 = ""
    header_row2 = ""
    for col in d.columns:
        label = col.replace("_", " ").upper()
        header_row1 += f'<th class="col-{col}">{label}</th>'
        uniq = sorted(d[col].dropna().astype(str).unique().tolist())
        if col in DROPDOWN_COLS and len(uniq) <= 20:
            opts = "".join(f'<option value="{v}">{v}</option>' for v in uniq)
            ctrl = f'<select onchange="filterTable_{tid}()"><option value="">All</option>{opts}</select>'
        else:
            ctrl = f'<input type="text" placeholder="Filter..." oninput="filterTable_{tid}()">'
        header_row2 += f'<th class="filter-row">{ctrl}</th>'

    rows = ""
    for _, row in d.iterrows():
        cells = "".join(f"<td>{row[c]}</td>" for c in d.columns)
        rows += f"<tr>{cells}</tr>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{ font-family: 'DM Sans', sans-serif; background: white; }}
      .wrap {{ overflow-x: auto; }}
      table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
      thead th {{
        padding: 8px 12px;
        color: #5b5449;
        font-weight: 500;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid rgba(148,174,223,0.2);
        white-space: nowrap;
        text-align: left;
      }}
      .filter-row th {{
        padding: 4px 8px;
        background: #fafafa;
        border-bottom: 1.5px solid rgba(148,174,223,0.3);
      }}
      .filter-row input, .filter-row select {{
        width: 100%;
        font-size: 12px;
        font-family: 'DM Sans', sans-serif;
        padding: 4px 6px;
        border: 1.5px solid rgba(148,174,223,0.3);
        border-radius: 6px;
        background: white;
        color: #0a0a0a;
        outline: none;
      }}
      .filter-row input:focus, .filter-row select:focus {{
        border-color: #94aedf;
      }}
      tbody td {{
        padding: 8px 12px;
        border-bottom: 1px solid rgba(148,174,223,0.12);
        white-space: nowrap;
        color: #0a0a0a;
        user-select: text;
      }}
      tbody tr:hover td {{ background: #f8f8f8; }}
      #count {{ font-size: 12px; color: #5b5449; margin-top: 8px; }}
    </style>
    </head>
    <body>
    <div class="wrap">
      <table id="tbl">
        <thead>
          <tr>{header_row1}</tr>
          <tr class="filter-row">{header_row2}</tr>
        </thead>
        <tbody id="tbody">{rows}</tbody>
      </table>
    </div>
    <p id="count">{len(d)} transactions</p>
    <script>
      function doFilter() {{
        const filterInputs = document.querySelectorAll('.filter-row th input, .filter-row th select');
        const filters = Array.from(filterInputs).map(el => el.value.toLowerCase());
        let visible = 0;
        document.querySelectorAll('#tbody tr').forEach(row => {{
          const cells = Array.from(row.cells);
          const show = filters.every((f, i) => !f || cells[i].textContent.toLowerCase().includes(f));
          row.style.display = show ? '' : 'none';
          if (show) visible++;
        }});
        document.getElementById('count').textContent = visible + ' of {len(d)} transactions';
      }}
      document.querySelectorAll('.filter-row input, .filter-row select').forEach(el => {{
        el.addEventListener('input', doFilter);
        el.addEventListener('change', doFilter);
      }});
    </script>
    </body>
    </html>
    """
    components.html(html, height=min(600, 120 + len(d) * 36), scrolling=True)


# ── Header ────────────────────────────────────────────────────────────────────

_col_logo, _col_account = st.columns([3, 1])
with _col_logo:
    st.image(os.path.join(BASE_DIR, "PictureFilkhedma.png"), width=160)
    st.markdown('<p class="muted" style="margin-top:8px">CIB Bank → Xero sync</p>',
                unsafe_allow_html=True)
with _col_account:
    st.markdown("<br>", unsafe_allow_html=True)
    _accounts     = load_accounts()
    _account_names = [a["name"] for a in _accounts]
    _prev_acct    = st.session_state.get("_selected_account", _account_names[0])
    _selected     = st.selectbox(
        "Account", _account_names,
        index=_account_names.index(_prev_acct) if _prev_acct in _account_names else 0,
        key="account_selector",
    )
    # If account changed, clear statement state for clean slate
    if _prev_acct != _selected:
        for _k in ["invoices", "inv_by_contact", "reverse_txs", "matches"]:
            st.session_state.pop(_k, None)
        st.session_state["_selected_account"] = _selected

# Derive active account config
acct = next((a for a in _accounts if a["name"] == _selected), _accounts[0])
BANK_ACCOUNT_ID    = acct["xero_bank_account_id"]
DEFAULT_ACCT_CODE  = acct["default_account_code"]
RULES_FILE_PATH    = os.path.join(BASE_DIR, acct["rules_file"])
PROCESSED_LOG_PATH = os.path.join(DATA_DIR, acct["processed_log"])
XERO_IDS_LOG_PATH  = os.path.join(DATA_DIR, acct["xero_ids_log"])
ACCT_STMT_KEY      = f"statement_df_{acct['id']}"
ACCT_BATCH_KEY     = f"batch_uploads_{acct['id']}"
ACCT_ALLOC_KEY     = f"allocations_{acct['id']}"

# Warn if bank account not configured
if not BANK_ACCOUNT_ID:
    st.warning(
        f"**{acct['name']}** has no Xero Bank Account ID configured. "
        "Edit `accounts.json` to add it before syncing."
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

ACCT_COMBINED_KEY = f"combined_batch_{acct['id']}"

if ACCT_STMT_KEY not in st.session_state:
    st.session_state[ACCT_STMT_KEY] = None
if ACCT_BATCH_KEY not in st.session_state:
    st.session_state[ACCT_BATCH_KEY] = {}
if ACCT_COMBINED_KEY not in st.session_state:
    st.session_state[ACCT_COMBINED_KEY] = None
if ACCT_ALLOC_KEY not in st.session_state:
    st.session_state[ACCT_ALLOC_KEY] = {}   # {tx_id: {contact, narration, account, department, channel}}

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_statement, tab_batch, tab_review, tab_match, tab_rules, tab_reverse = st.tabs(
    ["Statement Upload", "Batch Detail Upload", "Review & Sync", "Match Invoices", "Rules", "Reverse"]
)


# ════════════════════════════════════════════════════════════════════════════
# TAB A — Statement Upload
# ════════════════════════════════════════════════════════════════════════════

with tab_statement:
    st.markdown("<h2>Upload CIB Statement</h2>", unsafe_allow_html=True)
    st.markdown('<p class="muted">The monthly .xls file exported from CIB internet banking.</p>',
                unsafe_allow_html=True)

    uploaded = st.file_uploader("Choose file", type=["xls", "xlsx", "csv"], key="stmt_upload",
                                 label_visibility="collapsed")

    if uploaded:
        with st.expander("Raw file preview (first 10 rows)", expanded=False):
            raw = read_csv_any_encoding(uploaded, header=None, on_bad_lines="skip")
            st.dataframe(raw.head(10), use_container_width=True)
            uploaded.seek(0)

        try:
            uploaded.seek(0)
            df = parse_statement(uploaded, load_rules(RULES_FILE_PATH), DEFAULT_ACCT_CODE)
            st.session_state[ACCT_STMT_KEY] = df
        except Exception as e:
            st.error(f"Failed to parse statement: {e}")
            st.stop()

        batch_rows   = df[df["is_batch"]]
        regular_rows = df[~df["is_batch"]]

        c1, c2, c3 = st.columns(3)
        c1.metric("Total transactions", len(df))
        c2.metric("Regular",            len(regular_rows))
        c3.metric("ACH Corpay (batch)", len(batch_rows))

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>All transactions</h3>", unsafe_allow_html=True)

        st.caption("Drag to select · Ctrl/Cmd+C to copy")
        display_df(df, show_rules=True)

        if not batch_rows.empty:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown(
                '<p><span class="badge badge-warn">⚠ Batch payments detected</span></p>'
                '<p class="muted">The transactions below are ACH Corpay batch payments — '
                'each one covers multiple payees. Go to the <strong>Batch Detail Upload</strong> tab '
                'to upload the breakdown for each one before syncing.</p>',
                unsafe_allow_html=True,
            )
            display_df(batch_rows)


# ════════════════════════════════════════════════════════════════════════════
# TAB B — Batch Detail Upload
# ════════════════════════════════════════════════════════════════════════════

with tab_batch:
    st.markdown("<h2>Batch Detail Upload</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p class="muted">Upload the ACH Corpay breakdown so the app can replace each batch '
        'total with its individual line items when syncing to Xero.</p>',
        unsafe_allow_html=True,
    )

    df_stmt       = st.session_state[ACCT_STMT_KEY]
    batch_uploads = st.session_state[ACCT_BATCH_KEY]
    combined_batch = st.session_state[ACCT_COMBINED_KEY]

    if df_stmt is None:
        st.info("Upload a statement first on the Statement Upload tab.")
    else:
        batch_rows = df_stmt[df_stmt["is_batch"]].reset_index(drop=True)
        if batch_rows.empty:
            st.success("No ACH Corpay batch transactions found in the statement.")
        else:
            statement_batch_total = round(batch_rows["debit"].sum(), 2)

            st.markdown("<hr>", unsafe_allow_html=True)

            batch_mode = st.radio(
                "Upload mode",
                ["Individual file per batch", "Single combined file (all batches)"],
                key=f"batch_mode_{acct['id']}",
                horizontal=True,
            )

            # Clear the opposite mode's data when switching
            if batch_mode == "Individual file per batch" and combined_batch is not None:
                st.session_state[ACCT_COMBINED_KEY] = None
                combined_batch = None
            if batch_mode == "Single combined file (all batches)" and batch_uploads:
                st.session_state[ACCT_BATCH_KEY] = {}
                batch_uploads = {}

            st.markdown("<hr>", unsafe_allow_html=True)

            # ── Mode A: individual files ──────────────────────────────────
            if batch_mode == "Individual file per batch":
                for _, row in batch_rows.iterrows():
                    ref     = row["reference"]
                    label   = f"{row['date']}  ·  {ref}  ·  {row['debit']:,.2f}"
                    already = ref in batch_uploads

                    with st.expander(
                        f"{'✅' if already else '📎'}  {label}",
                        expanded=not already,
                    ):
                        col_a, col_b = st.columns([2, 1])
                        with col_a:
                            batch_file = st.file_uploader(
                                "Upload batch detail file (CSV or Excel)",
                                type=["csv", "xls", "xlsx"],
                                key=f"batch_{acct['id']}_{ref}",
                                label_visibility="collapsed",
                            )
                        with col_b:
                            batch_date = st.date_input(
                                "Batch date",
                                value=row["date"],
                                key=f"bdate_{acct['id']}_{ref}",
                            )

                        if batch_file:
                            try:
                                detail_df, minfo = parse_batch_detail(
                                batch_file, batch_date, ref,
                                rules=load_rules(RULES_FILE_PATH),
                                default_account_code=DEFAULT_ACCT_CODE,
                            )
                                batch_uploads[ref] = detail_df
                                st.session_state[ACCT_BATCH_KEY] = batch_uploads
                                st.success(f"Loaded {len(detail_df)} line items.")
                                with st.expander("Column mapping", expanded=False):
                                    st.json(minfo)
                                display_df(detail_df)
                            except Exception as e:
                                st.error(f"Could not parse batch file: {e}")
                        elif already:
                            detail_df = batch_uploads[ref]
                            st.success(f"{len(detail_df)} line items loaded.")
                            display_df(detail_df)

                # Summary
                uploaded_refs = set(batch_uploads.keys())
                pending_refs  = set(batch_rows["reference"].tolist()) - uploaded_refs
                st.markdown("<hr>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                c1.metric("Batches in statement",        len(batch_rows))
                c2.metric("Batches uploaded",            len(uploaded_refs))
                c3.metric("Batches pending",             len(pending_refs))
                if pending_refs:
                    st.warning(f"Missing detail for: {', '.join(pending_refs)}")

            # ── Mode B: single combined file ──────────────────────────────
            else:
                st.markdown(
                    f'<p class="muted">There are <strong>{len(batch_rows)} batch row(s)</strong> '
                    f'on the statement totalling '
                    f'<strong>{statement_batch_total:,.2f}</strong>. '
                    f'Upload one file containing all individual items — the app will verify '
                    f'the total matches before proceeding.</p>',
                    unsafe_allow_html=True,
                )

                combined_file = st.file_uploader(
                    "Upload combined batch detail file (CSV or Excel)",
                    type=["csv", "xls", "xlsx"],
                    key=f"combined_{acct['id']}",
                    label_visibility="collapsed",
                )

                if combined_file:
                    try:
                        first_batch_date = batch_rows.iloc[0]["date"]
                        cdf, minfo = parse_batch_detail(
                            combined_file, first_batch_date, "COMBINED",
                            rules=load_rules(RULES_FILE_PATH),
                            default_account_code=DEFAULT_ACCT_CODE,
                        )

                        with st.expander("Column mapping (expand to debug)", expanded=False):
                            st.json(minfo)
                            st.caption(f"Rows parsed: {len(cdf)}  ·  Debit sum: {cdf['debit'].sum():,.2f}  ·  Credit sum: {cdf['credit'].sum():,.2f}")

                        file_total = round(cdf["debit"].sum() + cdf["credit"].sum(), 2)
                        diff       = round(abs(statement_batch_total - file_total), 2)

                        st.markdown("<hr>", unsafe_allow_html=True)
                        rc1, rc2, rc3 = st.columns(3)
                        rc1.metric("Statement batch total", f"{statement_batch_total:,.2f}")
                        rc2.metric("File total",            f"{file_total:,.2f}")
                        rc3.metric("Difference",            f"{diff:,.2f}",
                                   delta=None if diff == 0 else f"{diff:+,.2f}",
                                   delta_color="off" if diff == 0 else "inverse")

                        if diff == 0:
                            st.success(f"✅ Totals match — {len(cdf)} line items loaded.")
                            st.session_state[ACCT_COMBINED_KEY] = cdf
                            combined_batch = cdf
                            display_df(cdf)
                        else:
                            st.error(
                                f"❌ Totals don't match (difference: {diff:,.2f}). "
                                "Check the file contains all batch items and no extras."
                            )
                            st.session_state[ACCT_COMBINED_KEY] = None

                    except Exception as e:
                        st.error(f"Could not parse combined file: {e}")

                elif combined_batch is not None:
                    file_total = round(combined_batch["debit"].sum() + combined_batch["credit"].sum(), 2)
                    st.success(f"✅ {len(combined_batch)} line items loaded · total {file_total:,.2f}")
                    display_df(combined_batch)


# ════════════════════════════════════════════════════════════════════════════
# TAB C — Review & Sync
# ════════════════════════════════════════════════════════════════════════════

with tab_review:
    st.markdown("<h2>Review & Sync</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p class="muted">Transactions are checked live against Xero. '
        'Duplicates are excluded automatically.</p>',
        unsafe_allow_html=True,
    )

    df_stmt        = st.session_state[ACCT_STMT_KEY]
    batch_uploads  = st.session_state[ACCT_BATCH_KEY]
    combined_batch = st.session_state.get(ACCT_COMBINED_KEY)
    if df_stmt is None:
        st.info("Upload a statement first on the Statement Upload tab.")
    else:
        frames = []
        combined_added = False
        for _, row in df_stmt.iterrows():
            ref = row["reference"]
            if row["is_batch"]:
                if combined_batch is not None:
                    # Single combined file mode — inject all items once
                    if not combined_added:
                        frames.append(combined_batch)
                        combined_added = True
                elif ref in batch_uploads:
                    frames.append(batch_uploads[ref])
                else:
                    frames.append(pd.DataFrame([row]))
            else:
                frames.append(pd.DataFrame([row]))

        final_df = pd.concat(frames, ignore_index=True)

        # ── Reconciliation check ──────────────────────────────────────────────
        stmt_total   = df_stmt["debit"].sum() + df_stmt["credit"].sum()
        review_total = final_df["debit"].sum() + final_df["credit"].sum()
        diff         = round(abs(stmt_total - review_total), 2)
        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("Statement total",    f"{stmt_total:,.2f}")
        rc2.metric("Review & Sync total", f"{review_total:,.2f}")
        if diff == 0:
            rc3.success("✓ Totals reconcile")
        else:
            rc3.error(f"⚠ Difference: {diff:,.2f} — upload missing batch details")

        st.markdown("<hr>", unsafe_allow_html=True)
        with st.spinner("Connecting to Xero..."):
            try:
                token = get_xero_token()
                xero_ok = True
            except Exception as e:
                st.error(f"Xero auth failed: {e}")
                xero_ok = False

        if xero_ok:
            date_from = final_df["date"].min()
            date_to   = final_df["date"].max()

            with st.spinner(f"Checking Xero for existing transactions ({date_from} → {date_to})..."):
                xero_existing = fetch_xero_transactions(token, date_from, date_to, BANK_ACCOUNT_ID)

            final_df["xero_key"] = final_df.apply(make_xero_key, axis=1)
            final_df["in_xero"]  = final_df["xero_key"].isin(xero_existing)

            processed_ids = load_processed_ids(PROCESSED_LOG_PATH)
            final_df["in_log"] = final_df["tx_id"].isin(processed_ids)

            new_df  = final_df[~final_df["in_xero"]].reset_index(drop=True)
            skipped = len(final_df) - len(new_df)

            c1, c2, c3 = st.columns(3)
            c1.metric("Total in statement",       len(final_df))
            c2.metric("New — not in Xero",        len(new_df))
            c3.metric("Already in Xero (hidden)", skipped)
            st.markdown("<hr>", unsafe_allow_html=True)

            if not new_df.empty:
                st.markdown("<h3>New transactions</h3>", unsafe_allow_html=True)
                st.caption("Click any cell to select · Ctrl/Cmd+C to copy · Shift-click to select a range")

                pending_batches = new_df[new_df["is_batch"] == True] if "is_batch" in new_df.columns else pd.DataFrame()
                if not pending_batches.empty:
                    st.warning(
                        f"{len(pending_batches)} ACH Corpay batch row(s) have no detail uploaded — "
                        "they will be posted as a single lump sum. Upload detail on the Batch Detail Upload tab to break them down."
                    )

                # ── Editable allocation table ─────────────────────────────
                coa_edit = load_coa()
                account_options = sorted([f"{code} — {name}" for code, name in coa_edit.items()])

                def _acct_label(code):
                    name = coa_edit.get(str(code), "")
                    return f"{code} — {name}" if name else str(code)

                saved_allocs = st.session_state[ACCT_ALLOC_KEY]

                def _saved(tx_id, field, default):
                    a = saved_allocs.get(tx_id)
                    return a[field] if a and field in a and a[field] else default

                edit_df = pd.DataFrame({
                    "date":        new_df["date"],
                    "type":        new_df.apply(lambda r: "Spend" if r["debit"] > 0 else "Receive", axis=1),
                    "amount":      new_df.apply(lambda r: r["debit"] if r["debit"] > 0 else r["credit"], axis=1),
                    "description": new_df["description"],
                    "reference":   new_df.get("reference", pd.Series([""] * len(new_df))),
                    "contact":  [_saved(new_df.iloc[i]["tx_id"], "contact",    new_df.iloc[i].get("contact") or "CIB Bank Import") for i in range(len(new_df))],
                    "narration":[_saved(new_df.iloc[i]["tx_id"], "narration",  new_df.iloc[i].get("narration") or "")              for i in range(len(new_df))],
                    "account":  [_saved(new_df.iloc[i]["tx_id"], "account",    _acct_label(new_df.iloc[i].get("account_code") or DEFAULT_ACCT_CODE)) for i in range(len(new_df))],
                    "department":[_saved(new_df.iloc[i]["tx_id"], "department", str(new_df.iloc[i].get("department") or ""))        for i in range(len(new_df))],
                    "channel":  [_saved(new_df.iloc[i]["tx_id"], "channel",    str(new_df.iloc[i].get("channel") or ""))            for i in range(len(new_df))],
                })

                st.markdown(
                    '<p class="muted" style="margin-bottom:8px">Edit <strong>Contact</strong>, '
                    '<strong>Narration</strong>, <strong>Account</strong>, '
                    '<strong>Department</strong> and <strong>Channel</strong> on any row before syncing. '
                    'Other columns are read-only.</p>',
                    unsafe_allow_html=True,
                )

                edited = st.data_editor(
                    edit_df,
                    key=f"review_edit_{acct['id']}",
                    column_config={
                        "date":        st.column_config.DateColumn("Date",        disabled=True),
                        "type":        st.column_config.TextColumn("Type",        disabled=True, width="small"),
                        "amount":      st.column_config.NumberColumn("Amount",    disabled=True, format="%.2f"),
                        "description": st.column_config.TextColumn("Description", disabled=True, width="large"),
                        "reference":   st.column_config.TextColumn("Reference",   disabled=True),
                        "contact":     st.column_config.TextColumn("Contact",     width="medium"),
                        "narration":   st.column_config.TextColumn("Narration",   width="medium"),
                        "account":     st.column_config.SelectboxColumn(
                                           "Account", options=account_options, width="medium"),
                        "department":  st.column_config.SelectboxColumn(
                                           "Department", options=XERO_DEPARTMENTS, width="medium"),
                        "channel":     st.column_config.SelectboxColumn(
                                           "Channel", options=XERO_CHANNELS, width="medium"),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

                # ── Save allocations ─────────────────────────────────────
                if st.button("💾 Save allocations", key=f"save_alloc_{acct['id']}"):
                    new_saved = {}
                    for i in range(len(new_df)):
                        tx_id = new_df.iloc[i]["tx_id"]
                        new_saved[tx_id] = {
                            "contact":    edited.iloc[i]["contact"],
                            "narration":  edited.iloc[i]["narration"],
                            "account":    edited.iloc[i]["account"],
                            "department": edited.iloc[i]["department"],
                            "channel":    edited.iloc[i]["channel"],
                        }
                    st.session_state[ACCT_ALLOC_KEY].update(new_saved)
                    st.success("Allocations saved — they will be pre-filled next time you visit this tab.")

                # Push edits back into new_df for posting
                sync_df = new_df.copy()
                sync_df["contact"]      = edited["contact"].fillna("CIB Bank Import").values
                sync_df["narration"]    = edited["narration"].fillna("").values
                sync_df["account_code"] = edited["account"].apply(
                    lambda x: str(x).split(" — ")[0] if pd.notna(x) and x else DEFAULT_ACCT_CODE
                ).values
                sync_df["department"]   = edited["department"].fillna("").values
                sync_df["channel"]      = edited["channel"].fillna("").values

                # Ensure flags exist and are boolean (NaN from concat → float → TypeError)
                for _flag in ("is_transfer_send", "is_transfer_skip", "is_export_only"):
                    if _flag not in sync_df.columns:
                        sync_df[_flag] = False
                    else:
                        sync_df[_flag] = sync_df[_flag].fillna(False).astype(bool)
                if "transfer_to_account_id" not in sync_df.columns:
                    sync_df["transfer_to_account_id"] = ""

                transfer_send_df = sync_df[sync_df["is_transfer_send"]  & ~sync_df["is_export_only"]].reset_index(drop=True)
                transfer_skip_df = sync_df[sync_df["is_transfer_skip"]].reset_index(drop=True)
                export_only_df   = sync_df[sync_df["is_export_only"]].reset_index(drop=True)
                regular_df       = sync_df[
                    ~sync_df["is_transfer_send"] &
                    ~sync_df["is_transfer_skip"] &
                    ~sync_df["is_export_only"]
                ].reset_index(drop=True)

                st.markdown("<hr>", unsafe_allow_html=True)

                # Routing summary
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("Regular (auto-sync)",        len(regular_df),       help="Posted automatically via BankTransactions API")
                mc2.metric("Interbank transfers (send)", len(transfer_send_df), help="Posted via BankTransfers API — auto-creates both sides in Xero")
                mc3.metric("Interbank receipts (skip)",  len(transfer_skip_df), help="Created automatically by the BankTransfer above")
                mc4.metric("Cross-currency (export)",    len(export_only_df),   help="Download as Xero CSV and upload manually")

                # ── Cross-currency export section ────────────────────────────
                if not export_only_df.empty:
                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown("<h3>Cross-currency interbank transfers</h3>", unsafe_allow_html=True)
                    st.markdown(
                        '<p class="muted">These transfers span currencies and can\'t be auto-posted '
                        'via Xero\'s BankTransfers API. Download the CSV below and import it directly '
                        'into the relevant bank account in Xero '
                        '(<strong>Accounting → Bank Accounts → Import</strong>).</p>',
                        unsafe_allow_html=True,
                    )
                    display_df(export_only_df, show_rules=True)

                    _csv_bytes = build_xero_import_csv(export_only_df)
                    st.download_button(
                        label=f"Download Xero import CSV ({len(export_only_df)} rows)",
                        data=_csv_bytes,
                        file_name=f"xero_interbank_{acct['id']}_{date.today()}.csv",
                        mime="text/csv",
                        key=f"export_csv_{acct['id']}",
                    )

                if not transfer_send_df.empty:
                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown(
                        '<p class="muted">💸 <strong>Same-currency interbank transfers</strong> will be '
                        'posted via the Xero BankTransfers API — this automatically creates the debit '
                        '<em>and</em> credit on both accounts.</p>',
                        unsafe_allow_html=True,
                    )

                st.markdown("<hr>", unsafe_allow_html=True)

                if st.button("Sync to Xero", type="primary", use_container_width=False):
                    all_errors = []

                    with st.spinner("Posting to Xero..."):
                        t_posted, t_errors = 0, []
                        if not transfer_send_df.empty:
                            t_posted, t_errors = post_bank_transfers(
                                transfer_send_df, token, BANK_ACCOUNT_ID
                            )
                            all_errors.extend(t_errors)

                        r_posted, r_errors = 0, []
                        if not regular_df.empty:
                            r_posted, r_errors = post_to_xero(
                                regular_df, token, BANK_ACCOUNT_ID,
                                DEFAULT_ACCT_CODE, XERO_IDS_LOG_PATH
                            )
                            all_errors.extend(r_errors)

                    if all_errors:
                        st.error(f"{len(all_errors)} error(s):")
                        for err in all_errors:
                            st.code(err, language="json")
                    else:
                        save_processed_ids(processed_ids | set(new_df["tx_id"]), PROCESSED_LOG_PATH)
                        parts = []
                        if r_posted:
                            parts.append(f"{r_posted} transaction(s)")
                        if t_posted:
                            parts.append(f"{t_posted} interbank transfer(s)")
                        if transfer_skip_df.shape[0]:
                            parts.append(f"{transfer_skip_df.shape[0]} receipt(s) skipped")
                        if export_only_df.shape[0]:
                            parts.append(f"{export_only_df.shape[0]} cross-currency row(s) skipped — download CSV above")
                        st.success(f"✓ {', '.join(parts)}.")
                        st.balloons()
            else:
                st.success("All transactions are already in Xero. Nothing to sync.")


# ════════════════════════════════════════════════════════════════════════════
# TAB D — Match Invoices
# ════════════════════════════════════════════════════════════════════════════

with tab_match:
    st.markdown("<h2>Match Invoices</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p class="muted">Fetch outstanding invoices from Xero and allocate bank receipts '
        'to them. WHT is handled automatically — a credit note is posted to account 627 '
        '(WHT Receivable) with the invoice number as description and '
        '"Deduct from Account" as reference, then the net amount is posted as a payment.</p>',
        unsafe_allow_html=True,
    )

    df_stmt        = st.session_state[ACCT_STMT_KEY]
    batch_uploads  = st.session_state[ACCT_BATCH_KEY]
    combined_batch = st.session_state.get(ACCT_COMBINED_KEY)
    if df_stmt is None:
        st.info("Upload a statement first on the Statement Upload tab.")
    else:
        st.markdown("<hr>", unsafe_allow_html=True)

        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        inv_date_from = col_f1.date_input("Invoices from", value=date(2026, 1, 1), key="inv_from")
        inv_date_to   = col_f2.date_input("Invoices to",   value=date.today(),      key="inv_to")
        inv_type_lbl  = col_f3.radio(
            "Invoice type",
            ["Both", "Sales invoices (ACCREC)", "Bills (ACCPAY)"],
            horizontal=True,
            key="inv_type_radio",
        )
        type_map = {"Both": "BOTH", "Sales invoices (ACCREC)": "ACCREC", "Bills (ACCPAY)": "ACCPAY"}

        if st.button("Fetch outstanding invoices", key="fetch_inv"):
            with st.spinner("Connecting to Xero..."):
                try:
                    _inv_token = get_xero_token()
                except Exception as e:
                    st.error(f"Xero auth failed: {e}")
                    _inv_token = None
            if _inv_token:
                with st.spinner("Fetching invoices..."):
                    invs = fetch_outstanding_invoices(
                        _inv_token,
                        type_map[inv_type_lbl],
                        inv_date_from,
                        inv_date_to,
                    )
                inv_by_contact: dict[str, list] = {}
                for inv in invs:
                    cname = inv.get("Contact", {}).get("Name", "Unknown")
                    inv_by_contact.setdefault(cname, []).append(inv)
                st.session_state["invoices"]       = invs
                st.session_state["inv_by_contact"] = inv_by_contact
                st.success(
                    f"Fetched {len(invs)} outstanding invoice(s) across "
                    f"{len(inv_by_contact)} contact(s)."
                )

        invoices       = st.session_state.get("invoices", [])
        inv_by_contact = st.session_state.get("inv_by_contact", {})

        if invoices:
            # Expand batch rows (respects both individual and combined batch modes)
            frames = []
            combined_added = False
            for _, row in df_stmt.iterrows():
                ref = row["reference"]
                if row["is_batch"]:
                    if combined_batch is not None:
                        if not combined_added:
                            frames.append(combined_batch)
                            combined_added = True
                    elif ref in batch_uploads:
                        frames.append(batch_uploads[ref])
                    else:
                        frames.append(pd.DataFrame([row]))
                else:
                    frames.append(pd.DataFrame([row]))
            all_rows = pd.concat(frames, ignore_index=True)

            # Only show rows whose detected contact has outstanding invoices
            matched_rows = all_rows[
                all_rows["contact"].isin(inv_by_contact.keys())
            ].reset_index(drop=True)

            unmatched_rows = all_rows[
                ~all_rows["contact"].isin(inv_by_contact.keys())
            ]

            st.markdown("<hr>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Invoices fetched",                 len(invoices))
            c2.metric("Statement rows with matches",      len(matched_rows))
            c3.metric("Statement rows — no invoice match", len(unmatched_rows))

            if matched_rows.empty:
                st.info(
                    "No statement transactions have a contact that matches any outstanding "
                    "invoice. Check that contact names in Rules match exactly what's in Xero."
                )
            else:
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown("<h3>Allocate receipts to invoices</h3>", unsafe_allow_html=True)
                st.markdown(
                    '<p class="muted">For each bank receipt, check the invoice(s) it covers '
                    'and enter the net <strong>Pay amount</strong> (what was actually received). '
                    'Enter <strong>WHT</strong> if the customer withheld tax — a credit note '
                    'will be posted to account 627 automatically.</p>',
                    unsafe_allow_html=True,
                )

                for row_idx, stmt_row in matched_rows.iterrows():
                    contact      = stmt_row["contact"]
                    bank_amount  = round(float(
                        stmt_row["debit"] if stmt_row["debit"] > 0 else stmt_row["credit"]
                    ), 2)
                    contact_invs = inv_by_contact.get(contact, [])
                    direction    = "Spend" if stmt_row["debit"] > 0 else "Receive"

                    # Check how much is already allocated for this row
                    allocated = sum(
                        st.session_state.get(f"pay_{row_idx}_{i}", 0.0)
                        for i in range(len(contact_invs))
                        if st.session_state.get(f"sel_{row_idx}_{i}", False)
                    )
                    remaining = round(bank_amount - allocated, 2)
                    status_icon = "✅" if abs(remaining) < 0.01 else "🔗"

                    with st.expander(
                        f"{status_icon}  {stmt_row['date']}  ·  {direction}  ·  "
                        f"EGP {bank_amount:,.2f}  ·  {str(stmt_row['description'])[:55]}",
                        expanded=(abs(remaining) >= 0.01),
                    ):
                        st.markdown(
                            f"<span class='muted'>Contact: <strong>{contact}</strong> · "
                            f"{len(contact_invs)} outstanding invoice(s)</span>",
                            unsafe_allow_html=True,
                        )
                        st.markdown("<br>", unsafe_allow_html=True)

                        # Column headers
                        hc1, hc2, hc3, hc4 = st.columns([0.5, 4, 2, 2])
                        hc2.markdown("<span class='muted' style='font-size:11px;text-transform:uppercase;letter-spacing:.05em'>Invoice</span>", unsafe_allow_html=True)
                        hc3.markdown("<span class='muted' style='font-size:11px;text-transform:uppercase;letter-spacing:.05em'>Pay amount (EGP)</span>", unsafe_allow_html=True)
                        hc4.markdown("<span class='muted' style='font-size:11px;text-transform:uppercase;letter-spacing:.05em'>WHT (EGP)</span>", unsafe_allow_html=True)

                        for inv_idx, inv in enumerate(contact_invs):
                            inv_id      = inv.get("InvoiceID", "")
                            inv_num     = inv.get("InvoiceNumber", "—")
                            inv_due     = round(float(inv.get("AmountDue", 0)), 2)
                            inv_type_v  = inv.get("Type", "")
                            inv_date_v  = _parse_xero_date(inv.get("Date", ""))

                            sel_key = f"sel_{row_idx}_{inv_idx}"
                            pay_key = f"pay_{row_idx}_{inv_idx}"
                            wht_key = f"wht_{row_idx}_{inv_idx}"

                            c1, c2, c3, c4 = st.columns([0.5, 4, 2, 2])
                            sel = c1.checkbox("", key=sel_key)
                            c2.markdown(
                                f"**{inv_num}** &nbsp; <span class='muted'>{inv_type_v} · {inv_date_v}</span><br>"
                                f"<span class='muted'>Due: EGP {inv_due:,.2f}</span>",
                                unsafe_allow_html=True,
                            )

                            # Initialise pay amount to inv_due on first render
                            if pay_key not in st.session_state:
                                st.session_state[pay_key] = inv_due
                            if wht_key not in st.session_state:
                                st.session_state[wht_key] = 0.0

                            c3.number_input(
                                "pay", min_value=0.0, max_value=float(inv_due * 2),
                                step=0.01, key=pay_key,
                                label_visibility="collapsed",
                                disabled=not sel,
                            )
                            c4.number_input(
                                "wht", min_value=0.0, max_value=float(inv_due * 2),
                                step=0.01, key=wht_key,
                                label_visibility="collapsed",
                                disabled=not sel,
                            )

                        # Running totals
                        allocated = round(sum(
                            st.session_state.get(f"pay_{row_idx}_{i}", 0.0)
                            for i in range(len(contact_invs))
                            if st.session_state.get(f"sel_{row_idx}_{i}", False)
                        ), 2)
                        remaining = round(bank_amount - allocated, 2)
                        st.markdown("<hr style='margin:12px 0'>", unsafe_allow_html=True)
                        tc1, tc2, tc3 = st.columns(3)
                        tc1.metric("Bank amount", f"EGP {bank_amount:,.2f}")
                        tc2.metric("Allocated",   f"EGP {allocated:,.2f}")
                        tc3.metric(
                            "Unallocated", f"EGP {remaining:,.2f}",
                            delta=None if abs(remaining) < 0.01 else f"{remaining:+,.2f}",
                            delta_color="off" if abs(remaining) < 0.01 else "inverse",
                        )

                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown(
                    '<p class="muted">Transactions matched here are posted directly as '
                    'Invoice Payments — do <strong>not</strong> also sync them in the '
                    'Review & Sync tab.</p>',
                    unsafe_allow_html=True,
                )

                if st.button("Post payments to Xero", type="primary", key="post_payments"):
                    with st.spinner("Connecting to Xero..."):
                        try:
                            token = get_xero_token()
                        except Exception as e:
                            st.error(f"Xero auth failed: {e}")
                            token = None

                    if token:
                        ok, fail = 0, []
                        jobs = []  # (inv_id, inv_num, contact_name, pay_amt, wht_amt, date_str)

                        for row_idx, stmt_row in matched_rows.iterrows():
                            contact_invs = inv_by_contact.get(stmt_row["contact"], [])
                            for inv_idx, inv in enumerate(contact_invs):
                                if not st.session_state.get(f"sel_{row_idx}_{inv_idx}", False):
                                    continue
                                pay_amt = round(float(st.session_state.get(f"pay_{row_idx}_{inv_idx}", 0.0)), 2)
                                wht_amt = round(float(st.session_state.get(f"wht_{row_idx}_{inv_idx}", 0.0)), 2)
                                if pay_amt <= 0:
                                    continue
                                jobs.append((
                                    inv.get("InvoiceID", ""),
                                    inv.get("InvoiceNumber", ""),
                                    inv.get("Contact", {}).get("Name", ""),
                                    pay_amt,
                                    wht_amt,
                                    str(stmt_row["date"]),
                                ))

                        if not jobs:
                            st.warning("No invoices selected — tick at least one checkbox.")
                        else:
                            progress = st.progress(0)
                            for i, (inv_id, inv_num, cname, pay_amt, wht_amt, date_str) in enumerate(jobs):
                                # Step 1: WHT credit note (if any)
                                if wht_amt > 0:
                                    success, err = create_wht_credit_note(
                                        inv_id, cname, inv_num, wht_amt, date_str, token
                                    )
                                    if not success:
                                        fail.append(f"WHT credit note for {inv_num}: {err}")
                                        progress.progress((i + 1) / len(jobs))
                                        continue

                                # Step 2: payment for net amount
                                success, err = post_payment(inv_id, pay_amt, date_str, token, BANK_ACCOUNT_ID)
                                if success:
                                    ok += 1
                                else:
                                    fail.append(f"Payment for {inv_num}: {err}")
                                progress.progress((i + 1) / len(jobs))

                            if fail:
                                st.error(f"{len(fail)} error(s):")
                                for e in fail:
                                    st.code(e, language="json")
                            if ok:
                                st.success(f"✓ {ok} payment(s) posted — invoices marked as paid.")
                                # Clear state
                                st.session_state["invoices"]       = []
                                st.session_state["inv_by_contact"] = {}
                                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TAB E — Rules
# ════════════════════════════════════════════════════════════════════════════

with tab_rules:
    st.markdown("<h2>Mapping Rules</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p class="muted">Rules are applied in order. The first matching rule wins. '
        'Contact set to <code>extract:payer_name</code> pulls the name from the description.</p>',
        unsafe_allow_html=True,
    )

    coa   = load_coa()
    rules = load_rules(RULES_FILE_PATH)

    st.markdown(
        f'<p class="muted">Editing rules for <strong>{acct["name"]}</strong>. '
        'Rules are applied in order — first match wins. '
        'Contact <code>extract:payer_name</code> pulls the name from the description.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("<hr>", unsafe_allow_html=True)

    # Display existing rules
    for i, rule in enumerate(rules):
        account_name  = coa.get(rule.get("account_code", ""), "")
        account_label = f"{rule['account_code']} — {account_name}" if account_name else rule.get("account_code", "")
        with st.expander(f"**{rule.get('match_contains', '')}** → {rule.get('contact', '')} · {account_label}", expanded=False):
            col1, col2 = st.columns(2)
            new_keyword   = col1.text_input("Match keyword",  value=rule.get("match_contains", ""), key=f"kw_{acct['id']}_{i}")
            new_contact   = col2.text_input("Contact name",   value=rule.get("contact", ""),         key=f"ct_{acct['id']}_{i}")
            new_narration = col1.text_input("Narration",      value=rule.get("narration") or "",     key=f"nr_{acct['id']}_{i}")

            coa_options   = [f"{code} — {name}" for code, name in sorted(coa.items())]
            current_code  = rule.get("account_code", "")
            current_label = f"{current_code} — {coa.get(current_code, '')}" if current_code in coa else current_code
            selected = col2.selectbox("Account", options=coa_options,
                                      index=coa_options.index(current_label) if current_label in coa_options else 0,
                                      key=f"ac_{acct['id']}_{i}")
            new_code = selected.split(" — ")[0]

            col_save, col_del, _ = st.columns([1, 1, 4])
            if col_save.button("Save", key=f"save_{acct['id']}_{i}"):
                rules[i]["match_contains"] = new_keyword
                rules[i]["contact"]        = new_contact
                rules[i]["narration"]      = new_narration or None
                rules[i]["account_code"]   = new_code
                save_rules(rules, RULES_FILE_PATH)
                st.success("Saved.")
                st.rerun()
            if col_del.button("Delete", key=f"del_{acct['id']}_{i}"):
                rules.pop(i)
                save_rules(rules, RULES_FILE_PATH)
                st.rerun()

    # Add new rule
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<h3>Add a new rule</h3>", unsafe_allow_html=True)
    with st.form(f"new_rule_{acct['id']}"):
        col1, col2 = st.columns(2)
        nkw   = col1.text_input("Match keyword (contains)")
        nct   = col2.text_input("Contact name")
        nnr   = col1.text_input("Narration (leave blank to keep original)")
        coa_options = [f"{code} — {name}" for code, name in sorted(coa.items())]
        nac   = col2.selectbox("Account", options=coa_options)
        ndesc = st.text_input("Rule description (for your reference)")
        submitted = st.form_submit_button("Add rule")
        if submitted and nkw:
            rules.append({
                "id":             nkw.lower().replace(" ", "_"),
                "description":    ndesc,
                "match_contains": nkw,
                "contact":        nct,
                "narration":      nnr or None,
                "account_code":   nac.split(" — ")[0],
            })
            save_rules(rules, RULES_FILE_PATH)
            st.success(f"Rule added for '{nkw}'.")
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TAB E — Reverse
# ════════════════════════════════════════════════════════════════════════════

with tab_reverse:
    st.markdown("<h2>Reverse a Sync</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p class="muted">Fetches all transactions posted to the CIB EGP account '
        'by this app (Contact = "CIB Bank Import") and deletes them from Xero.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("<hr>", unsafe_allow_html=True)

    _today         = date.today()
    _first_of_month = _today.replace(day=1)
    _last_of_month  = _today.replace(day=calendar.monthrange(_today.year, _today.month)[1])

    col_a, col_b = st.columns(2)
    date_from_r = col_a.date_input("From", value=_first_of_month, key="rev_from")
    date_to_r   = col_b.date_input("To",   value=_last_of_month,  key="rev_to")

    if st.button("Fetch from Xero", key="rev_fetch"):
        with st.spinner("Connecting to Xero..."):
            try:
                token = get_xero_token()
            except Exception as e:
                st.error(f"Xero auth failed: {e}")
                st.stop()

        where = (
            f'BankAccount.AccountID=Guid("{BANK_ACCOUNT_ID}")'
            f'&&Contact.Name="CIB Bank Import"'
            f'&&Date>=DateTime({date_from_r.year},{date_from_r.month},{date_from_r.day})'
            f'&&Date<=DateTime({date_to_r.year},{date_to_r.month},{date_to_r.day})'
        )

        all_txs, page = [], 1
        with st.spinner("Fetching..."):
            while True:
                r = requests.get(
                    "https://api.xero.com/api.xro/2.0/BankTransactions",
                    headers=xero_headers(token),
                    params={"where": where, "page": page},
                )
                if r.status_code != 200:
                    st.error(r.text)
                    break
                txs = r.json().get("BankTransactions", [])
                if not txs:
                    break
                all_txs.extend(txs)
                page += 1

        st.session_state["reverse_txs"] = all_txs

    txs_to_reverse = st.session_state.get("reverse_txs", [])

    if txs_to_reverse:
        rows = [{
            "date":       _parse_xero_date(tx.get("Date", "")),
            "type":       tx.get("Type", ""),
            "amount":     tx.get("Total", 0),
            "reference":  tx.get("Reference", ""),
            "xero_id":    tx.get("BankTransactionID", ""),
        } for tx in txs_to_reverse]

        st.markdown(f"<h3>{len(rows)} transactions found</h3>", unsafe_allow_html=True)
        st.caption("Click any cell to select · Ctrl/Cmd+C to copy")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<p class="muted">This will permanently delete all of the above from Xero.</p>',
                    unsafe_allow_html=True)

        confirm = st.checkbox("I understand this is permanent — delete these from Xero")
        if confirm:
            if st.button("Delete all from Xero", type="primary", key="rev_delete"):
                with st.spinner("Connecting to Xero..."):
                    try:
                        token = get_xero_token()
                    except Exception as e:
                        st.error(f"Xero auth failed: {e}")
                        st.stop()

                xero_ids = [tx["BankTransactionID"] for tx in txs_to_reverse]
                with st.spinner(f"Deleting {len(xero_ids)} transactions..."):
                    voided, errors = void_xero_transactions(xero_ids, token)

                if errors:
                    st.error(f"{len(errors)} error(s):")
                    for err in errors:
                        st.code(err, language="json")
                else:
                    _save_xero_ids({}, XERO_IDS_LOG_PATH)
                    save_processed_ids(set(), PROCESSED_LOG_PATH)
                    st.session_state["reverse_txs"] = []
                    st.success(f"✓ {voided} transactions deleted from Xero.")
                    st.rerun()
    elif "reverse_txs" in st.session_state:
        st.info("No transactions found for that date range with Contact = 'CIB Bank Import'.")
