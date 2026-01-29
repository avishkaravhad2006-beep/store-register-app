from io import BytesIO
import pandas as pd
import streamlit as st
from datetime import datetime
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ================= PDF =================
def generate_pdf(df, report_date):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, f"Store Daily Report - {report_date}")

    y -= 30
    c.setFont("Helvetica", 9)

    headers = ["Time", "Customer", "Mode", "B Amt", "K Amt", "Charges"]
    xs = [40, 110, 230, 300, 360, 430]

    for i, h in enumerate(headers):
        c.drawString(xs[i], y, h)

    y -= 15
    c.line(40, y, width - 40, y)
    y -= 15

    for _, r in df.iterrows():
        if y < 50:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 9)

        c.drawString(40, y, r["entry_time"])
        c.drawString(110, y, r["customer_name"][:15])
        c.drawString(230, y, r["payment_mode"])
        c.drawString(300, y, f"{r['b_amount']:.2f}")
        c.drawString(360, y, f"{r['k_amount']:.2f}")
        c.drawString(430, y, f"{r['grand_charges']:.2f}")
        y -= 14

    c.save()
    buffer.seek(0)
    return buffer

# ================= DATABASE =================
conn = sqlite3.connect("store.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT,
    entry_time TEXT,
    customer_type TEXT,
    customer_name TEXT,
    payment_mode TEXT,
    b_amount REAL,
    b_charges REAL,
    k_amount REAL,
    k_charges REAL,
    grand_charges REAL,
    remarks TEXT
)
""")
conn.commit()

# ================= SESSION STATE =================
defaults = {
    "customer_name": "",
    "customer_type": "Office",
    "payment_mode": "Cash",
    "remarks": "",
    "b_entries": [{"amount": 0.0, "charge_pct": 0.0}],
    "k_entries": [{"amount": 0.0, "charge_pct": 0.0}],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def reset_form():
    for k, v in defaults.items():
        st.session_state[k] = v

# ================= UI =================
st.set_page_config("Store Credit Register", layout="wide")
st.title("📋 Store Credit Register")
