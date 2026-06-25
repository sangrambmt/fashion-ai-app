import os
import sys
import shutil
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Allow `streamlit run app/main.py` from the project root
sys.path.insert(0, str(Path(__file__).parent))

from classifier import classify_image
from db import (
    init_db, save_image, get_images, get_filter_options,
    update_notes, delete_image,
)

load_dotenv(override=True)
init_db()

ROOT = Path(__file__).parent.parent
UPLOAD_DIR = ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

CONTINENTS = ["Africa", "Asia", "Europe", "North America", "South America", "Oceania"]
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}

st.set_page_config(
    page_title="Fashion Inspiration Library",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { min-width: 260px; max-width: 260px; }
.card-meta { font-size: 0.82rem; color: #666; margin-top: 2px; }
.tag-badge {
    display: inline-block;
    background: #f0f0f0;
    border-radius: 4px;
    padding: 1px 7px;
    font-size: 0.78rem;
    margin: 1px;
}
.ai-badge { background: #e8f4fd; color: #1a73e8; }
.designer-badge { background: #fef3e2; color: #e37400; }
</style>
""", unsafe_allow_html=True)

# Sidebar filters
opts = get_filter_options()

with st.sidebar:
    st.title("🔍 Filters")

    search = st.text_input("Search", placeholder="e.g. embroidered neckline")

    with st.expander("Garment", expanded=True):
        sel_garment  = st.multiselect("Type",             options=opts.get("garment_type", []))
        sel_style    = st.multiselect("Style",            options=opts.get("style", []))
        sel_material = st.multiselect("Material",         options=opts.get("material", []))
        sel_pattern  = st.multiselect("Pattern",          options=opts.get("pattern", []))
        sel_season   = st.multiselect("Season",           options=opts.get("season", []))
        sel_occasion = st.multiselect("Occasion",         options=opts.get("occasion", []))
        sel_consumer = st.multiselect("Consumer Profile", options=opts.get("consumer_profile", []))

    with st.expander("Location"):
        known_continents = opts.get("continent", [])
        continent_opts = sorted(set(CONTINENTS + known_continents))
        sel_continent = st.multiselect("Continent", options=continent_opts)
        sel_country   = st.multiselect("Country",   options=opts.get("country", []))
        sel_city      = st.multiselect("City",       options=opts.get("city", []))

    with st.expander("Time"):
        sel_year = st.multiselect("Year", options=opts.get("upload_year", []))
        raw_months = opts.get("upload_month", [])
        month_labels = [MONTH_NAMES.get(m, str(m)) for m in raw_months]
        sel_month_labels = st.multiselect("Month", options=month_labels)
        sel_month = [
            raw_months[month_labels.index(lbl)]
            for lbl in sel_month_labels
            if lbl in month_labels
        ]

    with st.expander("Designer"):
        sel_designer = st.multiselect("Designer", options=opts.get("designer", []))

    st.divider()
    if st.button("Clear All Filters", use_container_width=True):
        st.rerun()

# Header 
st.title("Fashion Inspiration Library")
st.caption("Upload garment images · Classify with AI · Search, filter & annotate")

# Upload section 
with st.expander("⬆️  Upload New Image", expanded=not bool(get_filter_options().get("garment_type"))):
    col_file, col_meta = st.columns([2, 2])

    with col_file:
        uploaded = st.file_uploader("Garment photo", type=["jpg", "jpeg", "png"])
        designer_name = st.text_input("Designer / photographer handle", placeholder="e.g. @sofia")

    with col_meta:
        st.caption("Where was this captured?")
        loc_continent = st.selectbox("Continent", ["(not specified)"] + CONTINENTS)
        loc_country   = st.text_input("Country", placeholder="e.g. France")
        loc_city      = st.text_input("City",    placeholder="e.g. Paris")

    if uploaded:
        dest = UPLOAD_DIR / uploaded.name
        with open(dest, "wb") as fh:
            shutil.copyfileobj(uploaded, fh)

        st.image(str(dest), width=220)

        if st.button("Classify & Save", type="primary"):
            with st.spinner("Analysing with GPT-4o-mini…"):
                try:
                    data = classify_image(str(dest))
                    location = {
                        "continent": "" if loc_continent == "(not specified)" else loc_continent,
                        "country":   loc_country,
                        "city":      loc_city,
                    }
                    save_image(str(dest), data, location=location, designer=designer_name)
                    st.success("Classified and saved.")
                    with st.expander("AI output"):
                        st.json(data)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Classification failed: {exc}")

# Library grid 
items = get_images(
    search=search,
    garment_types=sel_garment,
    styles=sel_style,
    materials=sel_material,
    patterns=sel_pattern,
    seasons=sel_season,
    occasions=sel_occasion,
    consumer_profiles=sel_consumer,
    continents=sel_continent,
    countries=sel_country,
    cities=sel_city,
    years=sel_year,
    months=sel_month,
    designers=sel_designer,
)

st.divider()
active = any([
    search, sel_garment, sel_style, sel_material, sel_pattern, sel_season,
    sel_occasion, sel_consumer, sel_continent, sel_country, sel_city,
    sel_year, sel_month, sel_designer,
])
total = len(items)
suffix = " (filtered)" if active else ""
st.subheader(f"Library — {total} image{'s' if total != 1 else ''}{suffix}")

if not items:
    st.info("No images match the current filters.")
    st.stop()

# Pagination via session state
PAGE_SIZE = 30
current_filters = (
    search,
    tuple(sel_garment), tuple(sel_style), tuple(sel_material),
    tuple(sel_pattern), tuple(sel_season), tuple(sel_occasion),
    tuple(sel_consumer), tuple(sel_continent), tuple(sel_country),
    tuple(sel_city), tuple(sel_year), tuple(sel_month), tuple(sel_designer),
)
if st.session_state.get("_last_filters") != current_filters:
    st.session_state["_last_filters"] = current_filters
    st.session_state["_page"] = 1

page = st.session_state.get("_page", 1)
visible = items[: page * PAGE_SIZE]


def _location_display(item: dict) -> str:
    parts = []
    for user_f, ai_f in [("city", "ai_city"), ("country", "ai_country"), ("continent", "ai_continent")]:
        val = (item.get(user_f) or item.get(ai_f) or "").strip()
        if val and val.lower() != "unknown":
            parts.append(val)
    return ", ".join(parts)


def _render_card(item: dict):
    path = item["image_path"]
    if os.path.exists(path):
        st.image(path, use_column_width=True)
    else:
        st.warning("Image not found")

    garment = (item.get("garment_type") or "Unknown").title()
    style   = (item.get("style") or "").title()
    st.markdown(f"**{garment}**" + (f" · {style}" if style else ""))

    season   = item.get("season") or ""
    occasion = item.get("occasion") or ""
    if season or occasion:
        st.markdown(
            f'<p class="card-meta">{season.title()}{"  ·  " if season and occasion else ""}{occasion.title()}</p>',
            unsafe_allow_html=True,
        )

    loc = _location_display(item)
    if loc:
        st.markdown(f'<p class="card-meta">📍 {loc}</p>', unsafe_allow_html=True)

    meta_parts = []
    if item.get("upload_date"):
        meta_parts.append(item["upload_date"])
    if item.get("designer"):
        handle = item["designer"].lstrip("@")
        meta_parts.append(f"@{handle}")
    if meta_parts:
        st.markdown(f'<p class="card-meta">{" · ".join(meta_parts)}</p>', unsafe_allow_html=True)

    if item.get("designer_tags"):
        tags_html = " ".join(
            f'<span class="tag-badge designer-badge">{t.strip()}</span>'
            for t in item["designer_tags"].split(",")
            if t.strip()
        )
        st.markdown(tags_html, unsafe_allow_html=True)

    with st.expander("Details & Annotations"):
        st.markdown('<span class="tag-badge ai-badge">AI Classification</span>', unsafe_allow_html=True)
        st.write(item.get("description") or "")

        ai_fields = [
            ("Material",          "material"),
            ("Colors",            "color_palette"),
            ("Pattern",           "pattern"),
            ("Consumer Profile",  "consumer_profile"),
            ("Trend Notes",       "trend_notes"),
            ("Location Context",  "location_context"),
        ]
        for label, key in ai_fields:
            val = item.get(key)
            if val:
                st.write(f"**{label}:** {val}")

        ai_loc_parts = [
            item.get("ai_city", ""), item.get("ai_country", ""), item.get("ai_continent", "")
        ]
        ai_loc = ", ".join(p for p in ai_loc_parts if p and p.lower() != "unknown")
        if ai_loc:
            st.write(f"**AI-inferred location:** {ai_loc}")

        st.divider()
        st.markdown('<span class="tag-badge designer-badge">Designer Annotations</span>', unsafe_allow_html=True)

        tags  = st.text_input(
            "Tags (comma-separated)",
            value=item.get("designer_tags") or "",
            key=f"tags_{item['id']}",
        )
        notes = st.text_area(
            "Notes",
            value=item.get("designer_notes") or "",
            key=f"notes_{item['id']}",
            height=80,
        )
        col_save, col_del = st.columns([3, 1])
        with col_save:
            if st.button("Save annotations", key=f"save_{item['id']}"):
                update_notes(item["id"], tags, notes)
                st.success("Saved.")
        with col_del:
            if st.button("Delete", key=f"del_{item['id']}", type="secondary"):
                path = delete_image(item["id"])
                if path and os.path.exists(path):
                    os.remove(path)
                st.rerun()


# Render grid
for row_start in range(0, len(visible), 3):
    cols = st.columns(3)
    for offset, col in enumerate(cols):
        idx = row_start + offset
        if idx < len(visible):
            with col:
                _render_card(visible[idx])

if len(visible) < total:
    remaining = total - len(visible)
    if st.button(f"Load more  ({remaining} remaining)", use_container_width=True):
        st.session_state["_page"] = page + 1
        st.rerun()
