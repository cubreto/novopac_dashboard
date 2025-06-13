import streamlit as st
st.set_page_config(page_title="Novo PAC Dashboard", layout="wide")

st.title("🚧 Novo PAC Dashboard – Skeleton")
st.info(
    "Dashboard scaffold is up. "
    "• PostgreSQL running on port 5435  "
    "• Streamlit on port 8507  "
    "Replace this file with real tabs once ETL is loaded."
)

# simple health-check
st.write("🔄 If you see this inside the container, the build succeeded.")
