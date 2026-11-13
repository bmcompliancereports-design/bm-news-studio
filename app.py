import streamlit as st
import tempfile
from pathlib import Path
from bm_engine import render_card, ASPECTS

st.set_page_config(
    page_title="BM NEWS · Batong Malake",
    page_icon="📰",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stApp { background: #0a1624; }
    h1 { color: #ffffff; font-size: 1.6rem !important; }
    h2, h3 { color: #e8f1f8; }
    .stButton>button {
        background: #024E8A; color: white; width: 100%;
        border-radius: 8px; height: 3rem; font-size: 1.05rem;
    }
    .stDownloadButton>button {
        background: #1CB7D1; color: #012444; width: 100%;
        font-weight: 700; border-radius: 8px; height: 3rem;
    }
    div[data-testid="stFileUploader"] { border: 1px solid #1CB7D1; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("BM NEWS")
st.caption("Batong Malake · Inquirer-Grade Editorial Cards")

with st.expander("Settings", expanded=True):
    aspect = st.selectbox("Aspect Ratio", list(ASPECTS.keys()), index=0)
    style = st.selectbox(
        "Style",
        ["hybrid_cover", "quotation", "formal_statement", "supporting"],
        format_func=lambda x: {
            "hybrid_cover": "Hybrid Cover (recommended)",
            "quotation": "Quotation Editorial",
            "formal_statement": "Formal Statement",
            "supporting": "Supporting Card",
        }.get(x, x),
    )
    monochrome = st.checkbox("Monochrome cutout", value=False)
    c1, c2 = st.columns(2)
    with c1:
        slide_num = st.number_input("Slide #", 1, 20, 1)
    with c2:
        slide_total = st.number_input("Total", 1, 20, 1)
    source = st.text_input("Source", "BM NEWS")

st.subheader("Content")
uploaded = st.file_uploader("Upload photo (faces will stay original)", type=["jpg", "jpeg", "png"])
kicker = st.text_input("Kicker", "NATIONAL CHILDREN’S MONTH 2026")
headlines_raw = st.text_area("Headlines (one per line)", "Manindigan!\nTumugon at\nKumalinga", height=90)
subheadline = st.text_input("Subheadline", "SA BATANG HANDA, MAS LIGTAS ANG BANSA")
body = st.text_area("Body", "Youth voices matter. Barangay Batong Malake stands with every child.", height=100)

if uploaded and st.button("Generate Card", type="primary"):
    with st.spinner("Creating card… faces remain 100% original"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(uploaded.getvalue())
            photo_path = tmp.name
        headlines = [ln.strip() for ln in headlines_raw.splitlines() if ln.strip()]
        out_path = Path(tempfile.mkdtemp()) / "card.png"
        try:
            result = render_card(
                photo_path=photo_path,
                kicker=kicker,
                headlines=headlines,
                subheadline=subheadline,
                body=body,
                aspect=aspect,
                style=style,
                monochrome=monochrome,
                slide_num=slide_num,
                slide_total=slide_total,
                source=source,
                output_path=str(out_path),
            )
            st.image(result, use_container_width=True)
            with open(result, "rb") as f:
                st.download_button(
                    "Download PNG",
                    f,
                    file_name=f"BM_{style}_{aspect.replace(':','x')}.png",
                    mime="image/png",
                )
        except Exception as e:
            st.error(str(e))

st.markdown("---")
st.caption("Faces are never regenerated. Only upscaled + seamless background removal. BM NEWS · Batong Malake")
