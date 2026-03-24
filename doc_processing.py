"""
doc_processing.py
Business logic layer: converts PDF invoices to structured data
using docling for document parsing and pandas for data handling.
Supports hotel, flight, meal, and car rental document types.
"""

import io
import json
import re
import tempfile
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

def _make_converter():
    opts = PdfPipelineOptions()
    opts.do_ocr = False          # no OCR model download needed
    opts.do_table_structure = True
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )

from model_gateway import invoke_llm

# ---------------------------------------------------------------------------
# Extraction prompts — one per document type
# ---------------------------------------------------------------------------

HOTEL_PROMPT = """\
You are an expert at extracting structured expense data from hotel invoice documents.

--- BEGIN DOCUMENT ---
{markdown}
--- END DOCUMENT ---

Extract ALL expense line items from this hotel invoice. For each line item return:
  - "date": date in YYYY-MM-DD format
  - "vendor": hotel name, cleaned and normalized
  - "doc_type": always "Hotel"
  - "category": one of [Room, Food & Beverage, Parking, Spa & Wellness, Taxes & Fees, Telephone, Laundry, Minibar, Miscellaneous]
  - "description": original line item text from the invoice
  - "currency": 3-letter ISO currency code (USD, CAD, EUR, etc.)
  - "amount": numeric amount as float, no currency symbols, no commas
  - "confidence": your confidence in this extraction (0.0 to 1.0)

Rules:
  - Create ONE row per line item, not one row per night
  - Amount must be a plain float. Strip $, commas, and currency codes
  - If a field is not present, use null
  - Always return a positive float for amount, never null or string

Return ONLY a valid JSON array. No explanation. No markdown fences.
"""

FLIGHT_PROMPT = """\
You are an expert at extracting structured expense data from airline receipts and booking confirmations.

--- BEGIN DOCUMENT ---
{markdown}
--- END DOCUMENT ---

Extract the following fields for each charge:
  - "date": travel date (departure date) in YYYY-MM-DD format
  - "vendor": airline name
  - "doc_type": always "Flight"
  - "category": one of [Airfare, Baggage Fee, Seat Upgrade, Travel Insurance, Change Fee, Miscellaneous]
  - "description": route (e.g. "YYZ to SFO") and flight number if available
  - "currency": 3-letter ISO currency code
  - "amount": numeric amount as float, no currency symbols
  - "confidence": 0.0 to 1.0

Rules:
  - Create ONE row per charge type (base fare, baggage, seat upgrade are separate rows)
  - Amount must be a plain float
  - If a field is not present, use null

Return ONLY a valid JSON array. No explanation. No markdown fences.
"""

MEAL_PROMPT = """\
You are an expert at extracting structured expense data from restaurant and meal receipts.

--- BEGIN DOCUMENT ---
{markdown}
--- END DOCUMENT ---

Extract the following fields:
  - "date": date in YYYY-MM-DD format
  - "vendor": restaurant or establishment name
  - "doc_type": always "Meal"
  - "category": one of [Breakfast, Lunch, Dinner, Coffee & Snacks, Alcohol, Miscellaneous]
  - "description": meal type and any notable details
  - "currency": 3-letter ISO currency code
  - "amount": total amount as float, no currency symbols
  - "confidence": 0.0 to 1.0

Rules:
  - Create ONE row for the meal total
  - Amount must be a plain float
  - If a field is not present, use null

Return ONLY a valid JSON array. No explanation. No markdown fences.
"""

CAR_PROMPT = """\
You are an expert at extracting structured expense data from car rental and ground transportation receipts.

--- BEGIN DOCUMENT ---
{markdown}
--- END DOCUMENT ---

Extract the following fields for each charge:
  - "date": pickup date in YYYY-MM-DD format
  - "vendor": rental company name
  - "doc_type": always "Car Rental"
  - "category": one of [Base Rental, Fuel, Insurance, Toll Charges, GPS & Equipment, Taxes & Fees, Miscellaneous]
  - "description": vehicle class and duration, or specific charge description
  - "currency": 3-letter ISO currency code
  - "amount": numeric amount as float, no currency symbols
  - "confidence": 0.0 to 1.0

Rules:
  - Create ONE row per charge type
  - Amount must be a plain float
  - If a field is not present, use null

Return ONLY a valid JSON array. No explanation. No markdown fences.
"""

_PROMPT_MAP = {
    "hotel":  HOTEL_PROMPT,
    "flight": FLIGHT_PROMPT,
    "meal":   MEAL_PROMPT,
    "car":    CAR_PROMPT,
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_doc_type(filename: str) -> str:
    """Detect document type from filename heuristics. Defaults to hotel."""
    name = filename.lower()
    if any(k in name for k in ["flight", "air", "airline", "ticket", "boarding", "itinerary"]):
        return "flight"
    if any(k in name for k in ["meal", "restaurant", "food", "lunch", "dinner", "breakfast", "cafe", "receipt"]):
        return "meal"
    if any(k in name for k in ["car", "rental", "rent", "enterprise", "hertz", "avis", "budget", "vehicle"]):
        return "car"
    # Default: hotel
    return "hotel"


def _pdf_to_markdown(pdf_bytes: bytes) -> str:
    """Convert a PDF (as bytes) to markdown using docling."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        converter = _make_converter()
        result = converter.convert(tmp_path)
        return result.document.export_to_markdown()
    finally:
        os.unlink(tmp_path)


def _parse_llm_json(raw: str) -> list[dict]:
    """Extract and parse a JSON array from the LLM response."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"```$", "", raw).strip()

    start = raw.find("[")
    end   = raw.rfind("]")
    if start == -1 or end == -1:
        return []

    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return []


def _parse_amount(raw_value) -> float:
    """Robustly parse an amount value to float."""
    if raw_value is None:
        return 0.0
    amount_str = str(raw_value).strip()
    # Remove currency symbols and spaces
    amount_str = re.sub(r"[£€¥₹$\s]", "", amount_str)
    # Handle European format: 1.234,56 → 1234.56
    if "," in amount_str and "." in amount_str:
        if amount_str.index(",") < amount_str.index("."):
            amount_str = amount_str.replace(",", "")
        else:
            amount_str = amount_str.replace(".", "").replace(",", ".")
    else:
        amount_str = amount_str.replace(",", "")
    try:
        return abs(float(amount_str))
    except (ValueError, TypeError):
        return 0.0


def _normalize_row(row: dict) -> dict:
    """Normalise a single extracted row into the standard column schema."""
    confidence = 1.0
    try:
        confidence = float(row.get("confidence", 1.0))
        confidence = max(0.0, min(1.0, confidence))
    except (ValueError, TypeError):
        confidence = 1.0

    vendor = (
        str(row.get("vendor", "") or row.get("hotel", "")).strip()
    )

    return {
        "Date":        str(row.get("date", "")).strip(),
        "Vendor":      vendor,
        "Doc Type":    str(row.get("doc_type", "Hotel")).strip(),
        "Category":    str(row.get("category", "")).strip(),
        "Description": str(row.get("description", "")).strip(),
        "Currency":    str(row.get("currency", "USD") or "USD").strip().upper(),
        "Amount":      _parse_amount(row.get("amount", 0.0)),
        "Confidence":  round(confidence, 2),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_invoices(uploaded_files: list) -> pd.DataFrame:
    """
    Process a list of uploaded PDF files and return a combined DataFrame.

    Automatically detects document type (hotel, flight, meal, car rental)
    from the filename and applies the appropriate extraction prompt.

    Returns a DataFrame with columns:
        Date, Vendor, Doc Type, Category, Description, Currency, Amount, Confidence
    """
    all_rows: list[dict] = []

    for uploaded_file in uploaded_files:
        if isinstance(uploaded_file, (str, os.PathLike)):
            filename  = os.path.basename(str(uploaded_file))
            with open(uploaded_file, "rb") as f:
                pdf_bytes = f.read()
        else:
            filename  = getattr(uploaded_file, "name", "invoice.pdf")
            uploaded_file.seek(0)
            pdf_bytes = uploaded_file.read()

        doc_type = _detect_doc_type(filename)
        markdown = _pdf_to_markdown(pdf_bytes)
        prompt   = _PROMPT_MAP[doc_type].format(markdown=markdown)
        llm_out  = invoke_llm(prompt)
        rows     = _parse_llm_json(llm_out)

        for row in rows:
            all_rows.append(_normalize_row(row))

    columns = ["Date", "Vendor", "Doc Type", "Category", "Description", "Currency", "Amount", "Confidence"]

    if not all_rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(all_rows)
    df["Amount"]     = pd.to_numeric(df["Amount"],     errors="coerce").fillna(0.0)
    df["Confidence"] = pd.to_numeric(df["Confidence"], errors="coerce").fillna(1.0)
    return df[columns]


def analyze_invoices(df: pd.DataFrame) -> tuple:
    """
    Build three Plotly figures from the expense DataFrame.

    Returns:
        (fig_vendor, fig_category, fig_doctype) — tuple of three Plotly Figure objects.
        fig_vendor:   Bar chart — total expenses by vendor.
        fig_category: Donut chart — total expenses by expense category.
        fig_doctype:  Bar chart — total expenses by document type.
    """
    df_clean = df[df["Amount"] > 0].copy()

    # Shared layout defaults (margin omitted — set per-chart to avoid duplicate kwarg)
    base_layout = dict(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13),
        title_font=dict(size=16, color="#1E293B"),
    )

    # ── Chart 1: Expenses by Vendor ──────────────────────────────────────────
    vendor_totals = (
        df_clean.groupby("Vendor", as_index=False)["Amount"]
        .sum()
        .sort_values("Amount", ascending=False)
    )

    fig_vendor = px.bar(
        vendor_totals,
        x="Vendor",
        y="Amount",
        text_auto=".2f",
        color="Vendor",
        color_discrete_sequence=px.colors.qualitative.Bold,
        title="Total Expenses by Vendor",
        labels={"Amount": "Total Amount ($)", "Vendor": "Vendor"},
    )
    fig_vendor.update_traces(textposition="outside")
    fig_vendor.update_layout(
        **base_layout,
        margin=dict(t=55, b=40, l=40, r=20),
        showlegend=False,
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#E2E8F0"),
    )

    # ── Chart 2: Expenses by Category ────────────────────────────────────────
    cat_totals = (
        df_clean.groupby("Category", as_index=False)["Amount"]
        .sum()
        .sort_values("Amount", ascending=False)
    )

    fig_category = px.pie(
        cat_totals,
        names="Category",
        values="Amount",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        title="Total Expenses by Category",
        hole=0.4,
    )
    fig_category.update_traces(
        textposition="inside",
        textinfo="percent+label",
        insidetextorientation="radial",
        hovertemplate="%{label}<br>$%{value:,.2f} (%{percent})<extra></extra>",
    )
    fig_category.update_layout(
        **base_layout,
        margin=dict(t=55, b=40, l=20, r=20),
        legend=dict(orientation="v", x=1.02, y=0.5, bgcolor="rgba(0,0,0,0)"),
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )

    # ── Chart 3: Expenses by Document Type ───────────────────────────────────
    doctype_totals = (
        df_clean.groupby("Doc Type", as_index=False)["Amount"]
        .sum()
        .sort_values("Amount", ascending=False)
    )

    _DOCTYPE_COLORS = {
        "Hotel":      "#3B82F6",
        "Flight":     "#8B5CF6",
        "Meal":       "#10B981",
        "Car Rental": "#F59E0B",
    }
    colors = [_DOCTYPE_COLORS.get(d, "#64748B") for d in doctype_totals["Doc Type"]]

    fig_doctype = px.bar(
        doctype_totals,
        x="Doc Type",
        y="Amount",
        text_auto=".2f",
        title="Total Expenses by Document Type",
        labels={"Amount": "Total Amount ($)", "Doc Type": "Document Type"},
        color="Doc Type",
        color_discrete_sequence=colors,
    )
    fig_doctype.update_traces(textposition="outside")
    fig_doctype.update_layout(
        **base_layout,
        margin=dict(t=55, b=40, l=40, r=20),
        showlegend=False,
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#E2E8F0"),
    )

    return fig_vendor, fig_category, fig_doctype
