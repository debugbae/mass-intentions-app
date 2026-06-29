"""
Mass Intentions PDF Generator
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import io
import os
import xml.sax.saxutils as saxutils
from datetime import date, timedelta

st.set_page_config(page_title="Mass Intentions PDF", page_icon="✝", layout="centered")

st.markdown("""
<style>
    .block-container { max-width: 760px; padding-top: 2rem; }
    .stButton > button { border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# ── PDF generation ────────────────────────────────────────────────────────────
def find_font():
    candidates = [
        ('/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf',
         '/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf',
         'Carlito', 'Carlito-Bold'),
        ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
         '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
         'Liberation', 'Liberation-Bold'),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
         'DejaVu', 'DejaVu-Bold'),
    ]
    for reg, bold, ra, ba in candidates:
        if ra and os.path.exists(reg) and os.path.exists(bold):
            return reg, bold, ra, ba
    return None, None, None, None


def build_pdf_bytes(days_data):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Table, TableStyle,
        HRFlowable, PageBreak
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    reg_path, bold_path, reg_alias, bold_alias = find_font()
    if reg_path:
        pdfmetrics.registerFont(TTFont(reg_alias, reg_path))
        pdfmetrics.registerFont(TTFont(bold_alias, bold_path))
    else:
        reg_alias  = 'Helvetica'
        bold_alias = 'Helvetica-Bold'

    PW       = 6.5 * inch
    TIME_COL = 1.3 * inch
    INT_COL  = PW - TIME_COL
    CROSS    = '†'
    BULLET   = '•'

    n = ParagraphStyle('n', fontName=reg_alias,  fontSize=10, leading=18)
    b = ParagraphStyle('b', fontName=bold_alias, fontSize=10, leading=18)

    def esc(t): return saxutils.escape(str(t))

    def intentions_para(items):
        lines = []
        for item in items:
            name = esc(item['name'].strip())
            if not name:
                continue
            lines.append(f'{BULLET} {CROSS} {name}' if item['cross'] else f'{BULLET} {name}')
        return Paragraph('<br/>'.join(lines) if lines else '&nbsp;', n)

    story = []
    for i, day in enumerate(days_data):
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.black, spaceAfter=3, spaceBefore=0))
        story.append(Paragraph(esc(day['name']), b))

        rows = [[Paragraph('Time', b), Paragraph('Intentions', b)]]
        for slot in day['slots']:
            rows.append([Paragraph(esc(slot['time']), n), intentions_para(slot['intentions'])])

        t = Table(rows, colWidths=[TIME_COL, INT_COL])
        t.setStyle(TableStyle([
            ('VALIGN',        (0,0), (-1,-1), 'TOP'),
            ('LINEABOVE',     (0,0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW',     (0,0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW',     (0,1), (-1,-1), 0.5, colors.black),
            ('TOPPADDING',    (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1),  8),
            ('LEFTPADDING',   (0,0), (-1,-1),  0),
            ('RIGHTPADDING',  (0,0), (-1,-1),  0),
            ('LEFTPADDING',   (1,0), (1, -1),  8),
        ]))
        story.append(t)
        if i < len(days_data) - 1:
            story.append(PageBreak())

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    doc.build(story)
    return buf.getvalue()


# ── Helpers ───────────────────────────────────────────────────────────────────
def format_date(d):
    """Format a date object as 'Monday June 29 2026'."""
    return f"{d.strftime('%A')} {d.strftime('%B')} {d.day} {d.year}"


def init():
    if 'days' not in st.session_state:
        st.session_state.days = []

init()

TIME_OPTIONS = ['7:00 AM', '12:15 N', '8:00 AM', '9:00 AM', '11:00 AM', '5:00 PM', 'Custom…']

# ── Callbacks ─────────────────────────────────────────────────────────────────
def add_day():
    # Default to next available weekday after last added day
    if st.session_state.days:
        try:
            last = st.session_state.days[-1]['_date']
            next_d = last + timedelta(days=1)
        except Exception:
            next_d = date.today()
    else:
        next_d = date.today()
    st.session_state.days.append({'_date': next_d, 'name': format_date(next_d), 'slots': []})

def remove_day(di):
    st.session_state.days.pop(di)

def add_slot(di):
    # Default to 7:00 AM if no slots yet, else 12:15 N
    default_time = '12:15 N' if st.session_state.days[di]['slots'] else '7:00 AM'
    st.session_state.days[di]['slots'].append({'time': default_time, 'intentions': []})

def remove_slot(di, si):
    st.session_state.days[di]['slots'].pop(si)

def add_intention(di, si):
    st.session_state.days[di]['slots'][si]['intentions'].append({'cross': True, 'name': ''})

def remove_intention(di, si, ii):
    st.session_state.days[di]['slots'][si]['intentions'].pop(ii)

def move_up(di, si, ii):
    lst = st.session_state.days[di]['slots'][si]['intentions']
    if ii > 0:
        lst[ii], lst[ii-1] = lst[ii-1], lst[ii]

def move_down(di, si, ii):
    lst = st.session_state.days[di]['slots'][si]['intentions']
    if ii < len(lst) - 1:
        lst[ii], lst[ii+1] = lst[ii+1], lst[ii]


# ── UI ────────────────────────────────────────────────────────────────────────
st.title("✝ Mass Intentions PDF")
st.caption("Add days and intentions below, then click **Generate PDF**.")

st.divider()

for di, day in enumerate(st.session_state.days):

    # Day header row: date picker + remove button
    col_date, col_del = st.columns([5, 1])
    with col_date:
        picked = st.date_input(
            "Date",
            value=day.get('_date', date.today()),
            key=f"day_{di}_date",
            label_visibility="collapsed",
            format="MM/DD/YYYY",
        )
        # Update stored date and formatted name whenever picker changes
        day['_date'] = picked
        day['name']  = format_date(picked)
    with col_del:
        st.button("🗑", key=f"del_day_{di}", on_click=remove_day, args=(di,), help="Remove day")

    # Show formatted name as a preview
    st.caption(f"**{day['name']}**")

    # Time slots
    for si, slot in enumerate(day['slots']):
        tc1, tc2, tc3 = st.columns([2, 5, 0.7])
            with tc1:
                time_sel = st.selectbox(
                    "Time", TIME_OPTIONS,
                    index=TIME_OPTIONS.index(slot['time']) if slot['time'] in TIME_OPTIONS else len(TIME_OPTIONS)-1,
                    key=f"slot_{di}_{si}_sel",
                    label_visibility="collapsed",
                )
                if time_sel == 'Custom…':
                    slot['time'] = st.text_input(
                        "Custom time",
                        value=slot['time'] if slot['time'] not in TIME_OPTIONS else '',
                        key=f"slot_{di}_{si}_custom",
                        label_visibility="collapsed",
                        placeholder="e.g. 6:00 PM",
                    )
                else:
                    slot['time'] = time_sel
            with tc3:
                st.button("🗑", key=f"del_slot_{di}_{si}", on_click=remove_slot, args=(di, si), help="Remove slot")

            # Intentions
            for ii, intention in enumerate(slot['intentions']):
                ic1, ic2, ic3, ic4, ic5 = st.columns([0.6, 3.8, 0.5, 0.5, 0.5])
                with ic1:
                    intention['cross'] = st.checkbox(
                        "†", value=intention['cross'],
                        key=f"int_{di}_{si}_{ii}_cross",
                        help="Check for deceased (†)",
                    )
                with ic2:
                    intention['name'] = st.text_input(
                        "Name", value=intention['name'],
                        placeholder="Name or intention…",
                        key=f"int_{di}_{si}_{ii}_name",
                        label_visibility="collapsed",
                    )
                with ic3:
                    st.button("↑", key=f"up_{di}_{si}_{ii}", on_click=move_up,   args=(di,si,ii), disabled=(ii==0))
                with ic4:
                    st.button("↓", key=f"dn_{di}_{si}_{ii}", on_click=move_down, args=(di,si,ii), disabled=(ii==len(slot['intentions'])-1))
                with ic5:
                    st.button("✕", key=f"del_int_{di}_{si}_{ii}", on_click=remove_intention, args=(di,si,ii))

            if slot['intentions']:
                st.caption("☑ = deceased (†)  ·  unchecked = special intention")

            st.button(f"＋ Add intention", key=f"add_int_{di}_{si}", on_click=add_intention, args=(di, si))

    st.button("＋ Add time slot", key=f"add_slot_{di}", on_click=add_slot, args=(di,))
    st.divider()

st.button("＋ Add day", on_click=add_day, type="secondary")

st.divider()

# Filename + generate
filename = st.text_input("PDF filename", value="WEEKDAY MASS INTENTIONS.pdf")
if not filename.endswith('.pdf'):
    filename += '.pdf'

if st.button("📄 Generate PDF", type="primary", disabled=len(st.session_state.days) == 0):
    clean = []
    for d in st.session_state.days:
        slots = [
            {'time': s['time'], 'intentions': [i for i in s['intentions'] if i['name'].strip()]}
            for s in d['slots'] if any(i['name'].strip() for i in s['intentions'])
        ]
        if slots:
            clean.append({'name': d['name'], 'slots': slots})

    if not clean:
        st.warning("Please add at least one day with intentions before generating.")
    else:
        with st.spinner("Generating PDF…"):
            try:
                pdf_bytes = build_pdf_bytes(clean)
                st.success("PDF ready!")
                st.download_button("⬇ Download PDF", data=pdf_bytes, file_name=filename, mime="application/pdf")
            except Exception as e:
                st.error(f"Error: {e}")
                st.exception(e)
