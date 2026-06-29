"""
Mass Intentions PDF Generator
Our Lady of Guadalupe Catholic Parish — Doral, FL
"""

import streamlit as st
import io
import os
import xml.sax.saxutils as saxutils
from datetime import date, timedelta

PARISH_NAME    = "Our Lady of Guadalupe Catholic Parish"
PARISH_ADDRESS = "11691 NW 25 Street · Doral, FL 33172"
PARISH_PHONE   = "(305) 593-6123"

st.set_page_config(page_title="OLOG Mass Intentions", page_icon="✝", layout="centered")

st.markdown("""
<style>
.stApp { background-color: #FAF8F4; }
.block-container { max-width: 780px; padding-top: 1rem !important; }

.olog-header {
    background-color: #1B3A6B;
    color: white;
    padding: 32px 32px 22px 32px;
    border-radius: 8px 8px 0 0;
    margin-bottom: 0;
    text-align: center;
}
.olog-header .cross { font-size: 2rem; color: #C9A227; line-height: 1; margin-bottom: 8px; display: block; }
.olog-header h1 { font-size: 1.35rem; font-weight: 700; margin: 0 0 6px 0; color: white; }
.olog-gold-rule { height: 3px; background: #C9A227; border: none; margin: 0; }
.olog-subheader {
    background-color: #EDE8DC;
    text-align: center;
    padding: 8px 16px 10px;
    margin-bottom: 20px;
}
.olog-subheader .subtitle {
    font-size: 0.72rem; color: #555; font-weight: 600;
    letter-spacing: 2px; text-transform: uppercase; margin: 0 0 2px 0;
}
.olog-subheader .address { font-size: 0.78rem; color: #777; margin: 0; }

.day-header {
    background-color: #1B3A6B;
    color: white;
    padding: 7px 14px;
    border-radius: 6px 6px 0 0;
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 0;
}
.day-card {
    background: white;
    border: 1px solid #D5CEBC;
    border-top: none;
    border-radius: 0 0 6px 6px;
    padding: 14px 16px 10px 16px;
    margin-bottom: 20px;
}
.slot-label {
    background: #EDE8DC;
    border-left: 3px solid #C9A227;
    padding: 3px 10px;
    font-size: 0.8rem;
    font-weight: 600;
    color: #1B3A6B;
    border-radius: 0;
    margin-bottom: 6px;
    display: inline-block;
}

.stButton > button[kind="primary"] {
    background-color: #1B3A6B !important; color: white !important;
    border: none !important; border-radius: 4px !important;
}
.stButton > button[kind="primary"]:hover { background-color: #254d8f !important; }
.stButton > button[kind="secondary"] {
    border: 1px solid #1B3A6B !important; color: #1B3A6B !important;
    border-radius: 4px !important; background: white !important;
}
.stDownloadButton > button {
    background-color: #C9A227 !important; color: white !important;
    border: none !important; font-weight: 600 !important; border-radius: 4px !important;
}
.stDownloadButton > button:hover { background-color: #a8841e !important; }

.olog-footer {
    text-align: center; color: #888; font-size: 0.73rem;
    padding: 16px 0 8px 0; border-top: 2px solid #C9A227; margin-top: 16px;
}
</style>
""", unsafe_allow_html=True)


# ── PDF generation ─────────────────────────────────────────────────────────────
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


def build_pdf_bytes(days_data, date_range_label=''):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Table, TableStyle,
        HRFlowable, PageBreak, Spacer
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

    NAVY      = colors.HexColor('#1B3A6B')
    GOLD      = colors.HexColor('#C9A227')
    GREY55    = colors.HexColor('#555555')
    GREY88    = colors.HexColor('#888888')
    ROW_EVEN  = colors.HexColor('#F4F1EB')
    HDR_BG    = colors.HexColor('#EDE8DC')

    PW       = 6.5 * inch
    TIME_COL = 1.3 * inch
    INT_COL  = PW - TIME_COL
    CROSS    = '†'
    BULLET   = '•'

    parish_style    = ParagraphStyle('parish',    fontName=bold_alias, fontSize=15, leading=20, alignment=1, textColor=NAVY)
    section_style   = ParagraphStyle('section',   fontName=reg_alias,  fontSize=8,  leading=12, alignment=1, textColor=GREY55, spaceAfter=2, letterSpacing=1.5)
    address_style   = ParagraphStyle('address',   fontName=reg_alias,  fontSize=8,  leading=12, alignment=1, textColor=GREY88)
    daterange_style = ParagraphStyle('daterange', fontName=bold_alias, fontSize=12, leading=16, alignment=1, textColor=NAVY, spaceBefore=3)
    day_hdr_style   = ParagraphStyle('day_hdr',   fontName=bold_alias, fontSize=11, leading=16, textColor=NAVY, spaceBefore=2, spaceAfter=4)
    n = ParagraphStyle('n', fontName=reg_alias,  fontSize=10, leading=18)
    b = ParagraphStyle('b', fontName=bold_alias, fontSize=10, leading=18, textColor=GREY55)

    def esc(t):
        return saxutils.escape(str(t))

    def intentions_para(items):
        lines = []
        for item in items:
            name = esc(item['name'].strip())
            if not name:
                continue
            lines.append(f'{BULLET} {CROSS} {name}' if item['cross'] else f'{BULLET} {name}')
        return Paragraph('<br/>'.join(lines) if lines else '&nbsp;', n)

    def draw_footer(canv, doc):
        canv.saveState()
        canv.setFont(reg_alias, 8)
        canv.setFillColor(GREY88)
        pw, ph = letter
        canv.drawCentredString(pw / 2, 0.45 * inch, f"Page {doc.page}")
        canv.restoreState()

    story = []
    for i, day in enumerate(days_data):
        if i == 0:
            story.append(Paragraph(esc(PARISH_NAME), parish_style))
            story.append(HRFlowable(width='100%', thickness=2.5, color=GOLD, spaceAfter=4, spaceBefore=5))
            story.append(Paragraph('WEEKDAY MASS INTENTIONS', section_style))
            if date_range_label:
                story.append(Paragraph(esc(date_range_label), daterange_style))
            story.append(Paragraph(esc(PARISH_ADDRESS), address_style))
            story.append(HRFlowable(width='100%', thickness=1, color=GOLD, spaceAfter=10, spaceBefore=5))

        # Thin rule + navy day name
        story.append(HRFlowable(width='100%', thickness=0.75, color=colors.HexColor('#333333'),
                                spaceAfter=4, spaceBefore=10))
        story.append(Paragraph(esc(day['name']), day_hdr_style))

        # Intentions table
        rows = [[Paragraph('Time', b), Paragraph('Intentions', b)]]
        for slot in day['slots']:
            rows.append([Paragraph(esc(slot['time']), n), intentions_para(slot['intentions'])])

        ts = [
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('LINEABOVE',     (0, 0), (-1,  0), 0.5, colors.HexColor('#444444')),
            ('LINEBELOW',     (0, 0), (-1,  0), 0.5, colors.HexColor('#444444')),
            ('LINEBELOW',     (0, 1), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('TOPPADDING',    (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (1, 0), (1,  -1), 10),
        ]

        t = Table(rows, colWidths=[TIME_COL, INT_COL])
        t.setStyle(TableStyle(ts))
        story.append(t)

        if i < len(days_data) - 1:
            story.append(PageBreak())

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        rightMargin=inch, leftMargin=inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return buf.getvalue()


# ── Helpers ────────────────────────────────────────────────────────────────────
def format_date(d):
    return f"{d.strftime('%A')} {d.strftime('%B')} {d.day} {d.year}"


# ── Session state ──────────────────────────────────────────────────────────────
if 'days' not in st.session_state:
    st.session_state.days = []

TIME_OPTIONS  = ['7:00 AM', '12:15 PM', 'Custom…']
DEFAULT_SLOTS = ['7:00 AM', '12:15 PM']


# ── Callbacks ──────────────────────────────────────────────────────────────────
def add_day():
    if st.session_state.days:
        try:
            next_d = st.session_state.days[-1]['_date'] + timedelta(days=1)
        except Exception:
            next_d = date.today()
    else:
        next_d = date.today()
    st.session_state.days.append({
        '_date': next_d,
        'name': format_date(next_d),
        'slots': [{'time': t, 'intentions': []} for t in DEFAULT_SLOTS]
    })

def remove_day(di):
    st.session_state.days.pop(di)

def add_slot(di):
    st.session_state.days[di]['slots'].append({'time': '7:00 AM', 'intentions': []})

def remove_slot(di, si):
    st.session_state.days[di]['slots'].pop(si)

def add_intention(di, si):
    st.session_state.days[di]['slots'][si]['intentions'].append({'cross': True, 'name': ''})

def remove_intention(di, si, ii):
    st.session_state.days[di]['slots'][si]['intentions'].pop(ii)

def move_up(di, si, ii):
    lst = st.session_state.days[di]['slots'][si]['intentions']
    if ii > 0:
        lst[ii], lst[ii - 1] = lst[ii - 1], lst[ii]

def move_down(di, si, ii):
    lst = st.session_state.days[di]['slots'][si]['intentions']
    if ii < len(lst) - 1:
        lst[ii], lst[ii + 1] = lst[ii + 1], lst[ii]


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="olog-header">
    <div class="cross">✝</div>
    <h1>{PARISH_NAME}</h1>
</div>
<hr class="olog-gold-rule"/>
<div class="olog-subheader">
    <p class="subtitle">Weekday Mass Intentions</p>
    <p class="address">{PARISH_ADDRESS} &nbsp;·&nbsp; {PARISH_PHONE}</p>
</div>
""", unsafe_allow_html=True)


# ── Days ───────────────────────────────────────────────────────────────────────
for di, day in enumerate(st.session_state.days):

    col_date, col_del = st.columns([5, 1])
    with col_date:
        picked = st.date_input(
            "Date",
            value=day.get('_date', date.today()),
            key=f"day_{di}_date",
            label_visibility="collapsed",
            format="MM/DD/YYYY",
        )
        day['_date'] = picked
        day['name']  = format_date(picked)
    with col_del:
        st.button("🗑", key=f"del_day_{di}", on_click=remove_day, args=(di,), help="Remove day")

    st.markdown(f'<div class="day-header">✝ &nbsp;{day["name"]}</div>', unsafe_allow_html=True)

    for si, slot in enumerate(day['slots']):
        st.markdown(f'<div class="slot-label">⏰ {slot["time"]}</div>', unsafe_allow_html=True)

        tc1, tc2, tc3 = st.columns([2, 5, 0.7])
        with tc1:
            time_sel = st.selectbox(
                "Time", TIME_OPTIONS,
                index=TIME_OPTIONS.index(slot['time']) if slot['time'] in TIME_OPTIONS else len(TIME_OPTIONS) - 1,
                key=f"slot_{di}_{si}_sel",
                label_visibility="collapsed",
            )
            if time_sel == 'Custom…':
                slot['time'] = st.text_input(
                    "Custom time",
                    value=slot['time'] if slot['time'] not in TIME_OPTIONS else '',
                    key=f"slot_{di}_{si}_custom",
                    label_visibility="collapsed",
                    placeholder="e.g. 8:00 AM",
                )
            else:
                slot['time'] = time_sel
        with tc3:
            st.button("🗑", key=f"del_slot_{di}_{si}", on_click=remove_slot, args=(di, si), help="Remove slot")

        for ii, intention in enumerate(slot['intentions']):
            ic1, ic2, ic3, ic4, ic5 = st.columns([0.6, 3.8, 0.5, 0.5, 0.5])
            with ic1:
                intention['cross'] = st.checkbox(
                    "†", value=intention['cross'],
                    key=f"int_{di}_{si}_{ii}_cross",
                    help="Deceased (†)",
                )
            with ic2:
                intention['name'] = st.text_input(
                    "Name", value=intention['name'],
                    placeholder="Name or intention…",
                    key=f"int_{di}_{si}_{ii}_name",
                    label_visibility="collapsed",
                )
            with ic3:
                st.button("↑", key=f"up_{di}_{si}_{ii}", on_click=move_up,   args=(di, si, ii), disabled=(ii == 0))
            with ic4:
                st.button("↓", key=f"dn_{di}_{si}_{ii}", on_click=move_down, args=(di, si, ii), disabled=(ii == len(slot['intentions']) - 1))
            with ic5:
                st.button("✕", key=f"del_int_{di}_{si}_{ii}", on_click=remove_intention, args=(di, si, ii))

        if slot['intentions']:
            st.caption("☑ = deceased (†)  ·  unchecked = special intention")

        st.button(f"＋ Add intention", key=f"add_int_{di}_{si}", on_click=add_intention, args=(di, si))
        st.write("")

    st.button("＋ Add time slot", key=f"add_slot_{di}", on_click=add_slot, args=(di,))
    st.divider()

st.button("＋ Add day", on_click=add_day, type="secondary")
st.divider()


# ── Generate PDF ───────────────────────────────────────────────────────────────
def auto_filename():
    days = st.session_state.get('days', [])
    if not days:
        return "OLOG MASS INTENTIONS.pdf"
    dates = [d['_date'] for d in days if '_date' in d]
    if not dates:
        return "OLOG MASS INTENTIONS.pdf"
    first = min(dates)
    last  = max(dates)
    f = f"{first.strftime('%B')} {first.day}"
    l = f"{last.strftime('%B')} {last.day}"
    year = first.year
    if f == l:
        return f"OLOG MASS INTENTIONS_{f} {year}.pdf"
    return f"OLOG MASS INTENTIONS_{f} to {l} {year}.pdf"

filename = st.text_input("PDF filename", value=auto_filename())
if not filename.endswith('.pdf'):
    filename += '.pdf'

if st.button("📄 Generate PDF", type="primary", disabled=len(st.session_state.days) == 0):
    clean = []
    for d in st.session_state.days:
        slots = [
            {'time': s['time'], 'intentions': [i for i in s['intentions'] if i['name'].strip()]}
            for s in d['slots']
            if any(i['name'].strip() for i in s['intentions'])
        ]
        if slots:
            clean.append({'name': d['name'], 'slots': slots})

    if not clean:
        st.warning("Please add at least one day with intentions before generating.")
    else:
        with st.spinner("Generating PDF…"):
            try:
                all_dates = [d['_date'] for d in st.session_state.days if '_date' in d]
                if all_dates:
                    fd = min(all_dates); ld = max(all_dates)
                    fl = f"{fd.strftime('%B')} {fd.day}"
                    ll = f"{ld.strftime('%B')} {ld.day}, {ld.year}"
                    dr_label = fl if fd == ld else f"{fl} – {ll}"
                else:
                    dr_label = ''
                pdf_bytes = build_pdf_bytes(clean, date_range_label=dr_label)
                st.success("✅ PDF ready!")
                st.download_button(
                    "⬇ Download PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"Error: {e}")
                st.exception(e)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="olog-footer">
    {PARISH_NAME} &nbsp;·&nbsp; {PARISH_ADDRESS} &nbsp;·&nbsp; {PARISH_PHONE}<br/>
    <a href="https://www.guadalupedoral.org" target="_blank" style="color:#1B3A6B;">guadalupedoral.org</a>
</div>
""", unsafe_allow_html=True)
