import sqlite3
import pandas as pd
import streamlit as st
from passwordlab.config import DB_PATH

st.set_page_config(page_title="PasswordLab Results", layout="wide")
st.title("PasswordLab — Experiment Dashboard")
st.caption("Synthetic localhost laboratory results only.")
if not DB_PATH.exists():
    st.info("No experiments recorded yet. Run the local agent first.")
    st.stop()
with sqlite3.connect(DB_PATH) as conn:
    df = pd.read_sql_query("SELECT * FROM experiments ORDER BY id DESC", conn)
if df.empty:
    st.info("No experiment records found.")
    st.stop()
a, b, c = st.columns(3)
a.metric("Experiments", len(df))
b.metric("Total attempts", int(df["attempts"].sum()))
c.metric("Successful authentications", int(df["successes"].sum()))
st.subheader("Experiment history")
st.dataframe(df, use_container_width=True)
st.subheader("Attempts by simulation mode")
summary = df.groupby("mode", as_index=False)[["attempts", "successes"]].sum()
st.bar_chart(summary.set_index("mode"))
st.subheader("Defensive interpretation")
st.markdown("- Dictionary success can indicate predictable or reused passwords.\\n"
            "- Brute-force feasibility depends on search-space size and password length.\\n"
            "- MFA, rate limiting, monitoring and secure password storage are important controls.\\n"
            "- Results from this tiny lab do not predict production attack times.")
