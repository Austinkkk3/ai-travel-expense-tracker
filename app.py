"""
app.py
Streamlit UI for the AI Travel Expense Tracker application.
Supports hotel invoices, flight receipts, meal receipts, and car rentals.
"""

import io
import os
import uuid
import requests
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from doc_processing import process_invoices, analyze_invoices

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Travel Expense Tracker",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: #F1F5F9;
    }

    .block-container {
        padding-top: 2rem !important;
        padding-left: 3rem !important;
        padding-right: 3rem !important;
        max-width: 1400px !important;
    }

    /* ── Hero ── */
    .hero {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 50%, #1D4ED8 100%);
        border-radius: 20px;
        padding: 2.5rem 3rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    .hero::before {
        content: '';
        position: absolute;
        top: -60px; right: -60px;
        width: 260px; height: 260px;
        background: radial-gradient(circle, rgba(99,102,241,0.35) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero::after {
        content: '';
        position: absolute;
        bottom: -40px; left: 30%;
        width: 180px; height: 180px;
        background: radial-gradient(circle, rgba(59,130,246,0.25) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.75rem;
        font-weight: 500;
        color: rgba(255,255,255,0.85);
        margin-bottom: 1rem;
        backdrop-filter: blur(4px);
    }
    .hero h1 {
        color: #ffffff;
        font-size: 2.4rem;
        font-weight: 800;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.8px;
        line-height: 1.2;
    }
    .hero h1 span {
        background: linear-gradient(90deg, #93C5FD, #C4B5FD);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero p {
        color: rgba(255,255,255,0.65);
        font-size: 1rem;
        margin: 0;
        font-weight: 400;
    }
    .hero-powered {
        position: absolute;
        top: 2rem; right: 2.5rem;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-size: 0.72rem;
        color: rgba(255,255,255,0.6);
        font-weight: 500;
        backdrop-filter: blur(8px);
    }

    /* ── Doc type pills ── */
    .pill {
        display: inline-block;
        border-radius: 20px;
        padding: 3px 10px;
        font-size: 0.72rem;
        font-weight: 600;
        margin: 1px 2px;
    }
    .pill-hotel   { background:#DBEAFE; color:#1D4ED8; }
    .pill-flight  { background:#EDE9FE; color:#6D28D9; }
    .pill-meal    { background:#D1FAE5; color:#065F46; }
    .pill-car     { background:#FEF3C7; color:#92400E; }

    /* ── Panel cards ── */
    .panel {
        background: #ffffff;
        border-radius: 16px;
        padding: 1.75rem 2rem;
        margin-bottom: 1.5rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.04);
    }
    .panel-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 1.2rem;
        display: flex;
        align-items: center;
        gap: 8px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .panel-title-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        background: linear-gradient(135deg, #3B82F6, #8B5CF6);
        display: inline-block;
    }

    /* ── Metric cards ── */
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #F8FAFF 0%, #EFF6FF 100%);
        border: 1px solid #DBEAFE;
        border-radius: 14px;
        padding: 1.1rem 1.25rem;
        position: relative;
        overflow: hidden;
    }
    .metric-card::after {
        content: '';
        position: absolute;
        top: 0; right: 0;
        width: 60px; height: 60px;
        background: radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%);
    }
    .metric-card .m-label {
        font-size: 0.68rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.4rem;
    }
    .metric-card .m-value {
        font-size: 1.6rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1;
    }
    .metric-card .m-sub {
        font-size: 0.72rem;
        color: #94A3B8;
        margin-top: 0.25rem;
    }

    /* ── Confidence bar ── */
    .conf-bar-wrap {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.78rem;
    }
    .conf-bar-bg {
        flex: 1;
        height: 6px;
        background: #E2E8F0;
        border-radius: 3px;
        overflow: hidden;
    }
    .conf-bar-fill {
        height: 100%;
        border-radius: 3px;
    }

    /* ── Status banners ── */
    .banner-ok {
        background: linear-gradient(135deg, #ECFDF5, #D1FAE5);
        border: 1px solid #6EE7B7;
        border-left: 4px solid #10B981;
        border-radius: 10px;
        padding: 0.65rem 1rem;
        font-size: 0.85rem;
        font-weight: 500;
        color: #065F46;
        margin-top: 0.75rem;
    }
    .banner-warn {
        background: linear-gradient(135deg, #FFFBEB, #FEF3C7);
        border: 1px solid #FCD34D;
        border-left: 4px solid #F59E0B;
        border-radius: 10px;
        padding: 0.65rem 1rem;
        font-size: 0.85rem;
        font-weight: 500;
        color: #92400E;
        margin-top: 0.75rem;
    }

    /* ── Buttons ── */
    div.stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.6rem 1.5rem !important;
        height: 42px !important;
        transition: all 0.18s ease !important;
        letter-spacing: 0.01em !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%) !important;
        color: #fff !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(37,99,235,0.35) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(37,99,235,0.5) !important;
        transform: translateY(-1px) !important;
    }
    div.stButton > button[kind="secondary"] {
        background: #ffffff !important;
        color: #2563EB !important;
        border: 1.5px solid #BFDBFE !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06) !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        background: #EFF6FF !important;
        border-color: #93C5FD !important;
        transform: translateY(-1px) !important;
    }
    div.stDownloadButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        height: 42px !important;
        background: linear-gradient(135deg, #059669 0%, #0D9488 100%) !important;
        color: #fff !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(5,150,105,0.3) !important;
        transition: all 0.18s ease !important;
    }

    /* ── File uploader ── */
    /* Browse files button — light style */
    [data-testid="stFileUploaderDropzoneInput"] + div button,
    [data-testid="stFileUploaderDropzone"] button {
        background: #ffffff !important;
        color: #2563EB !important;
        border: 1.5px solid #BFDBFE !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06) !important;
    }
    [data-testid="stFileUploaderDropzone"] button:hover {
        background: #EFF6FF !important;
        border-color: #93C5FD !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        border-radius: 14px !important;
        border: 2px dashed #93C5FD !important;
        background: linear-gradient(135deg, #F8FAFF 0%, #EFF6FF 100%) !important;
        transition: border-color 0.2s !important;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #3B82F6 !important;
    }
    /* Fix: uploaded file names invisible (white text on light bg) */
    /* Target text nodes only — exclude buttons so Browse files stays readable */
    [data-testid="stFileUploader"] span:not(button span),
    [data-testid="stFileUploader"] p,
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] label {
        color: #1E293B !important;
    }
    /* File list items below the dropzone */
    [data-testid="stFileUploaderFile"] *:not(button):not(button *) {
        color: #1E293B !important;
    }

    /* ── Dataframe ── */
    .stDataFrame { border-radius: 12px !important; overflow: hidden !important; border: 1px solid #E2E8F0 !important; }
    [data-testid="stDataFrame"] > div { border-radius: 12px !important; }

    /* ── Divider ── */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #E2E8F0 20%, #E2E8F0 80%, transparent);
        margin: 1.75rem 0;
    }

    /* ── Chart label ── */
    .chart-label {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748B;
        margin-bottom: 0.5rem;
        padding-left: 2px;
    }

    /* ── Footer ── */
    .footer {
        text-align: center;
        padding: 2rem 0 1rem;
        color: #CBD5E1;
        font-size: 0.78rem;
    }
    .footer strong { color: #94A3B8; }

    /* ── Spinner ── */
    .stSpinner > div { border-top-color: #2563EB !important; }

    /* ── Hide default Streamlit chrome ── */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

# ── AI chat helper (Astra DB RAG + watsonx.ai) ───────────────────────────────

def _search_astra(query: str, top_k: int = 5) -> list[str]:
    """Search Astra DB for receipt chunks relevant to the query."""
    try:
        from astrapy import DataAPIClient
        token    = os.getenv("ASTRA_TOKEN")
        endpoint = os.getenv("ASTRA_ENDPOINT")
        name     = os.getenv("ASTRA_COLLECTION", "receipts")
        if not token or not endpoint:
            return []
        db = DataAPIClient(token).get_database_by_api_endpoint(endpoint)
        col = db.get_collection(name)
        # Simple keyword find — return the most recent chunks
        results = col.find({}, limit=top_k)
        return [doc.get("content", "") for doc in results if doc.get("content")]
    except Exception:
        return []


def _ask_ai(question: str, session_id: str) -> str:
    """Answer a question using extracted expense data + watsonx.ai Granite."""
    from model_gateway import invoke_llm

    # Use the already-extracted DataFrame as context — it has ALL line items
    df = st.session_state.get("invoice_df")
    if df is not None and not df.empty:
        # Pre-compute aggregations in Python so the LLM only needs to read, not calculate
        by_category = (
            df.groupby("Category")["Amount"].sum()
            .sort_values()
            .reset_index()
            .rename(columns={"Amount": "Total"})
        )
        by_vendor = (
            df.groupby("Vendor")["Amount"].sum()
            .sort_values(ascending=False)
            .reset_index()
            .rename(columns={"Amount": "Total"})
        )
        by_doctype = (
            df.groupby("Doc Type")["Amount"].sum()
            .sort_values(ascending=False)
            .reset_index()
            .rename(columns={"Amount": "Total"})
        )
        context = f"""--- All Expense Line Items ---
{df.to_string(index=False)}

--- Total Spent by Category (sorted lowest to highest) ---
{by_category.to_string(index=False)}

--- Total Spent by Vendor (sorted highest to lowest) ---
{by_vendor.to_string(index=False)}

--- Total Spent by Document Type ---
{by_doctype.to_string(index=False)}

--- Overall Total: {df['Amount'].sum():.2f} across {len(df)} line items ---"""
    else:
        # Fallback: try Astra DB chunks if no DataFrame in session
        chunks = _search_astra(question, top_k=20)
        context = "\n\n---\n\n".join(chunks) if chunks else "No receipts uploaded yet."

    prompt = f"""You are an AI travel expense assistant. Use the expense data and pre-computed totals below to answer accurately.

Column definitions:
- Date: date of the expense
- Vendor: hotel, airline, restaurant, or rental company name
- Doc Type: Hotel, Flight, Meal, or Car Rental
- Category: expense category (Room, Food & Beverage, Parking, Taxes & Fees, Airfare, etc.)
- Currency: 3-letter code (CAD, USD, etc.)
- Amount: numeric expense amount

{context}

User Question: {question}

Answer concisely using the pre-computed totals above — do not re-calculate."""
    try:
        return invoke_llm(prompt)
    except Exception as e:
        return f"⚠️ Error: {e}"


# Keep backward-compatible alias used in the chat UI below
_ask_langflow = _ask_ai

# ── Session state ─────────────────────────────────────────────────────────────

if "invoice_df" not in st.session_state:
    st.session_state.invoice_df = None
if "show_graphs" not in st.session_state:
    st.session_state.show_graphs = False
if "processing_error" not in st.session_state:
    st.session_state.processing_error = None
if "astra_chunks" not in st.session_state:
    st.session_state.astra_chunks = None
if "astra_error" not in st.session_state:
    st.session_state.astra_error = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="hero">
        <div class="hero-badge">✈️ &nbsp; AI-Powered · IBM watsonx.ai</div>
        <h1>AI Travel Expense <span>Tracker</span></h1>
        <p>Upload hotel invoices, flight receipts, meal receipts, and car rentals — extract and visualize all expenses instantly.</p>
        <div class="hero-powered">Powered by Docling &amp; Granite 3</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Upload panel
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="panel">'
    '<div class="panel-title"><span class="panel-title-dot"></span> Upload Expense Documents</div>',
    unsafe_allow_html=True,
)

# Doc type legend
st.markdown(
    """
    <div style="margin-bottom:1rem; display:flex; gap:8px; flex-wrap:wrap;">
        <span class="pill pill-hotel">🏨 Hotel Invoice</span>
        <span class="pill pill-flight">✈️ Flight Receipt</span>
        <span class="pill pill-meal">🍽️ Meal Receipt</span>
        <span class="pill pill-car">🚗 Car Rental</span>
        <span style="font-size:0.78rem; color:#94A3B8; margin-left:4px; align-self:center;">
            — auto-detected from filename
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_files = st.file_uploader(
    label="Drop PDFs here or click to browse",
    type=["pdf"],
    accept_multiple_files=True,
    help="PDF format only · Maximum 10 files per submission · Doc type auto-detected from filename",
    label_visibility="collapsed",
)

if uploaded_files and len(uploaded_files) > 10:
    st.warning("Maximum 10 files — only the first 10 will be processed.")
    uploaded_files = uploaded_files[:10]

if uploaded_files:
    names = " &nbsp;·&nbsp; ".join(f"📄 {f.name}" for f in uploaded_files)
    st.markdown(
        f'<div class="banner-ok">✅ &nbsp;<strong>{len(uploaded_files)} file(s) ready</strong>'
        f' &nbsp;—&nbsp; {names}</div>',
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Action buttons
# ---------------------------------------------------------------------------

btn_col1, btn_col2, btn_col3, spacer = st.columns([1.1, 1.1, 1.3, 4.5])

with btn_col1:
    submit_clicked = st.button("⚡  Submit", type="primary", width='stretch')
with btn_col2:
    analyze_clicked = st.button("Analyze", type="secondary", width='stretch')

# ---------------------------------------------------------------------------
# Submit logic
# ---------------------------------------------------------------------------

if submit_clicked:
    if not uploaded_files:
        st.error("Please upload at least one expense document before submitting.")
    else:
        st.session_state.show_graphs = False
        st.session_state.processing_error = None
        st.session_state.astra_chunks = None
        st.session_state.astra_error = None

        with st.spinner("Parsing documents and extracting data with AI…"):
            try:
                df = process_invoices(uploaded_files)
                st.session_state.invoice_df = df
            except Exception as exc:
                st.session_state.processing_error = str(exc)

        if st.session_state.processing_error:
            st.error(f"Processing error:\n\n{st.session_state.processing_error}")
        else:
            # ── Auto-save to Astra DB for RAG chatbot ──────────────────────
            with st.spinner("Saving to Astra DB for AI assistant…"):
                try:
                    from astra_helper import upload_files_to_astra
                    chunks = upload_files_to_astra(uploaded_files)
                    st.session_state.astra_chunks = chunks
                except Exception as exc:
                    st.session_state.astra_error = str(exc)

# ---------------------------------------------------------------------------
# Results table
# ---------------------------------------------------------------------------

df: pd.DataFrame | None = st.session_state.invoice_df

if df is not None:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="panel">'
        '<div class="panel-title"><span class="panel-title-dot"></span> Extracted Expenses</div>',
        unsafe_allow_html=True,
    )

    if df.empty:
        st.markdown(
            '<div class="banner-warn">⚠️ &nbsp;No expense line items could be extracted '
            'from the uploaded documents.</div>',
            unsafe_allow_html=True,
        )
    else:
        # Metric cards
        total_amount = df["Amount"].sum()
        num_vendors  = df["Vendor"].nunique()
        num_invoices = len(uploaded_files) if uploaded_files else "—"
        num_rows     = len(df)
        doc_types    = df["Doc Type"].nunique()
        avg_conf     = df["Confidence"].mean() * 100

        st.markdown(
            f"""
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="m-label">Files Processed</div>
                    <div class="m-value">{num_invoices}</div>
                    <div class="m-sub">documents</div>
                </div>
                <div class="metric-card">
                    <div class="m-label">Line Items</div>
                    <div class="m-value">{num_rows}</div>
                    <div class="m-sub">charges extracted</div>
                </div>
                <div class="metric-card">
                    <div class="m-label">Total Amount</div>
                    <div class="m-value">${total_amount:,.0f}</div>
                    <div class="m-sub">{num_vendors} unique vendors</div>
                </div>
                <div class="metric-card">
                    <div class="m-label">Avg Confidence</div>
                    <div class="m-value">{avg_conf:.0f}%</div>
                    <div class="m-sub">{doc_types} document type(s)</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Format display copy
        display_df = df.copy()
        display_df["Amount"] = display_df["Amount"].map("${:,.2f}".format)
        display_df["Confidence"] = display_df["Confidence"].map("{:.0%}".format)

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=min(420, 56 + len(display_df) * 35),
            column_config={
                "Date":        st.column_config.TextColumn("📅  Date",        width="small"),
                "Vendor":      st.column_config.TextColumn("🏢  Vendor",       width="medium"),
                "Doc Type":    st.column_config.TextColumn("📁  Doc Type",     width="small"),
                "Category":    st.column_config.TextColumn("🏷  Category",     width="medium"),
                "Description": st.column_config.TextColumn("📝  Description",  width="large"),
                "Currency":    st.column_config.TextColumn("💱  Currency",     width="small"),
                "Amount":      st.column_config.TextColumn("💵  Amount",       width="small"),
                "Confidence":  st.column_config.TextColumn("🎯  Confidence",   width="small"),
            },
        )

        # Export button — CSV download
        with btn_col3:
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️  Export CSV",
                data=csv_bytes,
                file_name="travel_expenses.csv",
                mime="text/csv",
                width='stretch',
            )

    # ── Astra DB status ───────────────────────────────────────────────────
    if st.session_state.astra_chunks is not None:
        st.markdown(
            f'<div class="banner-ok">🗄️ &nbsp;<strong>Saved to Astra DB</strong>'
            f' — {st.session_state.astra_chunks} chunks stored · '
            f'Ready for AI Assistant</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state.astra_error:
        st.markdown(
            f'<div class="banner-warn">⚠️ &nbsp;<strong>Astra DB upload failed</strong>'
            f' — {st.session_state.astra_error}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Analyze — 3 charts
# ---------------------------------------------------------------------------

if analyze_clicked:
    if df is None or df.empty:
        st.warning("Submit documents first, then click Analyze.")
    else:
        st.session_state.show_graphs = True

if st.session_state.show_graphs and df is not None and not df.empty:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="panel">'
        '<div class="panel-title"><span class="panel-title-dot"></span> Expense Analysis</div>',
        unsafe_allow_html=True,
    )

    with st.spinner("Building charts…"):
        fig_vendor, fig_category, fig_doctype = analyze_invoices(df)

    # Row 1: vendor + category side by side
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown('<div class="chart-label">By Vendor</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_vendor, width='stretch')
    with col2:
        st.markdown('<div class="chart-label">By Expense Category</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_category, width='stretch')

    # Row 2: doc type full width
    st.markdown('<div class="chart-label">By Document Type</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_doctype, width='stretch')

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# AI Assistant chat
# ---------------------------------------------------------------------------

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="panel">'
    '<div class="panel-title"><span class="panel-title-dot"></span> AI Expense Assistant</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="font-size:0.85rem;color:#64748B;margin:-0.5rem 0 1rem;">Ask questions about your uploaded receipts — powered by Langflow &amp; Astra DB</p>',
    unsafe_allow_html=True,
)

# Render chat history
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input box
if prompt := st.chat_input("e.g. What was the total hotel spend?"):
    # Show user message immediately
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call Langflow and stream response
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            answer = _ask_langflow(prompt, st.session_state.chat_session_id)
        st.markdown(answer)
    st.session_state.chat_messages.append({"role": "assistant", "content": answer})

st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="footer">
        <strong>AI Travel Expense Tracker</strong> &nbsp;·&nbsp;
        Powered by IBM watsonx.ai Granite &amp; Docling &nbsp;·&nbsp;
        Built with Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)
