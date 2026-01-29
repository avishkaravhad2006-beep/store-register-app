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
now = datetime.now()
st.caption(f"Date: {now:%Y-%m-%d} | Time: {now:%H:%M:%S}")

tab_new, tab_today, tab_all, tab_summary = st.tabs(
    ["➕ New Entry", "📅 Today’s Entries", "📄 All Entries (Edit)", "📊 Today Summary"]
)

# ================= NEW ENTRY =================
with tab_new:
    st.subheader("📝 New Entry")

    st.radio("Customer Type", ["Office", "Others"], horizontal=True, key="customer_type")
    st.radio("Payment Mode", ["Cash", "UPI"], horizontal=True, key="payment_mode")
    st.text_input("Customer Name *", key="customer_name")

    st.divider()

    # -------- B --------
    st.subheader("B (भरलेले)")
    b_amt = b_chg = 0.0
    for i, e in enumerate(st.session_state.b_entries):
        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            e["amount"] = st.number_input(f"B Amount #{i+1}", 0.0, key=f"b_amt_{i}")
        with c2:
            e["charge_pct"] = st.number_input(f"Charge % #{i+1}", 0.0, 10.0, 0.5, key=f"b_chg_{i}")
        ch = e["amount"] * e["charge_pct"] / 100
        with c3:
            st.write(f"Charge: ₹ {ch:.2f}")
        b_amt += e["amount"]
        b_chg += ch

    if st.button("➕ Add B Entry"):
        st.session_state.b_entries.append({"amount": 0.0, "charge_pct": 0.0})

    st.divider()

    # -------- K --------
    st.subheader("K (काढलेले)")
    k_amt = k_chg = 0.0
    for i, e in enumerate(st.session_state.k_entries):
        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            e["amount"] = st.number_input(f"K Amount #{i+1}", 0.0, key=f"k_amt_{i}")
        with c2:
            e["charge_pct"] = st.number_input(f"Charge % #{i+1}", 0.0, 10.0, 0.5, key=f"k_chg_{i}")
        ch = e["amount"] * e["charge_pct"] / 100
        with c3:
            st.write(f"Charge: ₹ {ch:.2f}")
        k_amt += e["amount"]
        k_chg += ch

    if st.button("➕ Add K Entry"):
        st.session_state.k_entries.append({"amount": 0.0, "charge_pct": 0.0})

    st.divider()
    st.metric("Total Charges", f"₹ {b_chg + k_chg:.2f}")
    st.text_area("Remarks", key="remarks")

    if st.button("💾 Save Entry", use_container_width=True):
        if not st.session_state.customer_name.strip():
            st.error("Customer name is required")
            st.stop()

        cursor.execute("""
        INSERT INTO entries VALUES (
            NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """, (
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"),
            st.session_state.customer_type,
            st.session_state.customer_name,
            st.session_state.payment_mode,
            b_amt, b_chg, k_amt, k_chg,
            b_chg + k_chg,
            st.session_state.remarks
        ))
        conn.commit()
        st.success("Entry saved")
        reset_form()
        st.rerun()

# ================= TODAY ENTRIES =================
with tab_today:
    st.subheader("📅 Today’s Entries")
    today = now.strftime("%Y-%m-%d")
    df = pd.read_sql_query(
        "SELECT entry_time, customer_name, payment_mode, b_amount, k_amount, grand_charges FROM entries WHERE entry_date=? ORDER BY id DESC",
        conn, params=(today,)
    )
    st.dataframe(df, use_container_width=True) if not df.empty else st.info("No entries")

# ================= ALL ENTRIES (EDIT) =================
with tab_all:
    st.subheader("✏️ Edit Entry")

    df_all = pd.read_sql_query("SELECT * FROM entries ORDER BY id DESC", conn)
    if df_all.empty:
        st.info("No entries")
        st.stop()

    st.dataframe(df_all, use_container_width=True)

    eid = st.selectbox("Select Entry ID", df_all["id"])
    row = df_all[df_all.id == eid].iloc[0]

    en = st.text_input("Customer Name", row.customer_name, key="edit_name")
    pm = st.radio("Payment Mode", ["Cash", "UPI"], index=0 if row.payment_mode=="Cash" else 1, key="edit_pm")
    b_amt = st.number_input("B Amount", value=row.b_amount, key="edit_ba")
    b_chg = st.number_input("B Charges", value=row.b_charges, key="edit_bc")
    k_amt = st.number_input("K Amount", value=row.k_amount, key="edit_ka")
    k_chg = st.number_input("K Charges", value=row.k_charges, key="edit_kc")
    rm = st.text_area("Remarks", row.remarks, key="edit_rm")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Update Entry"):
            cursor.execute("""
            UPDATE entries SET
            customer_name=?, payment_mode=?,
            b_amount=?, b_charges=?,
            k_amount=?, k_charges=?,
            grand_charges=?, remarks=?
            WHERE id=?
            """, (en, pm, b_amt, b_chg, k_amt, k_chg, b_chg+k_chg, rm, eid))
            conn.commit()
            st.success("Entry updated")
            st.rerun()

    with c2:
        if st.button("🗑️ Delete Entry"):
            cursor.execute("DELETE FROM entries WHERE id=?", (eid,))
            conn.commit()
            st.warning("Entry deleted")
            st.rerun()

# ================= SUMMARY =================
with tab_summary:
    st.subheader("📊 Today Summary")

    s = pd.read_sql_query("""
    SELECT COUNT(*) c, SUM(b_amount) b, SUM(k_amount) k, SUM(grand_charges) ch
    FROM entries WHERE entry_date=?
    """, conn, params=(today,)).iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entries", int(s.c))
    c2.metric("Total B", f"₹ {s.b or 0:.2f}")
    c3.metric("Total K", f"₹ {s.k or 0:.2f}")
    c4.metric("Charges", f"₹ {s.ch or 0:.2f}")

    st.divider()

    exp = pd.read_sql_query(
        "SELECT entry_time, customer_name, payment_mode, b_amount, k_amount, grand_charges FROM entries WHERE entry_date=?",
        conn, params=(today,)
    )

    buf = BytesIO()
    exp.to_excel(buf, index=False)
    st.download_button("📊 Excel", buf.getvalue(), f"Store_{today}.xlsx")

    st.download_button("📄 PDF", generate_pdf(exp, today), f"Store_{today}.pdf")
