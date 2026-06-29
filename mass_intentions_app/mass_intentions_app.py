"""
Mass Intentions PDF Generator
Run with: streamlit run mass_intentions_app.py
"""

import streamlit as st
import tempfile
import os
import xml.sax.saxutils as saxutils

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mass Intentions PDF",
    page_icon="✝",
    layout="centered",
)

st.markdown("""
<style>
    .block-container { max-width: 780px; padding-top: 2rem; }
    .stButton > button { border-radius: 6px; }
    .day-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }
    .slot-card {
        background: #ffffff;
        border: 1px solid #e9ecef;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
    }
    h3 { color: #343a40; }
</style>
""", unsafe_allow_html=True)


# ── PDF generation (self-contained, no external skill needed) ─────────────────
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
        # macOS system fonts
        ('/Library/Fonts/Arial.ttf',
         '/Library/Fonts/Arial Bold.ttf',
         'Arial', 'Arial-Bold'),
        ('/System/Library/Fonts/Helvetica.ttc',
         '/System/Library/Fonts/Helvetica.ttc',
         None, None),  # skip ttc for simplicity
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
    import io

    reg_path, bold_path, reg_alias, bold_alias = find_font()
    if reg_path:
        pdfmetrics.registerFont(TTFont(reg_alias,  reg_path))
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

    def esc(t):
        return saxutils.escape(str(t))

    def intentions_para(items):
        lines = []
        for item in items:
            name = esc(item['name'].strip())
            if not name:
                continue
            if item['cross']:
                lines.append(f'{BULLET} {CROSS} {name}')
            else:
                lines.append(f'{BULLET} {name}')
        return Paragraph('<br/>'.join(lines) if lines else '&nbsp;', n)

    story = []
    for i, day in enumerate(days_data):
        story.append(HRFlowable(
            width='100%', thickness=0.5, color=colors.black,
            spaceAfter=3, spaceBefore=0
        ))
        story.append(Paragraph(esc(day['name']), b))

        rows = [[Paragraph('Time', b), Paragraph('Intentions', b)]]
        for slot in day['slots']:
            rows.append([
                Paragraph(esc(slot['time']), n),
                intentions_para(slot['intentions']),
            ])

        t = Table(rows, colWidths=[TIME_COL, INT_COL])
        t.setStyle(TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('LINEABOVE',     (0, 0), (-1,  0), 0.5, colors.black),
            ('LINEBELOW',     (0, 0), (-1,  0), 0.5, colors.black),
            ('LINEBELOW',     (0, 1), (-1, -1), 0.5, colors.black),
            ('TOPPADDING',    (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1),  8),
            ('LEFTPADDING',   (0, 0), (-1, -1),  0),
            ('RIGHTPADDING',  (0, 0), (-1, -1),  0),
            ('LEFTPADDING',   (1, 0), (1,  -1),  8),
        ]))
        story.append(t)
        if i < len(days_data) - 1:
            story.append(PageBreak())

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        rightMargin=inch, leftMargin=inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    doc.build(story)
    return buf.getvalue()


# ── Session state init ────────────────────────────────────────────────────────
def init():
    if 'days' not in st.session_state:
        st.session_state.days = []          # list of {name, slots:[{time, intentions:[{cross,name}]}]}

init()

# ── Callbacks ─────────────────────────────────────────────────────────────────
def add_day():
    st.session_state.days.append({'name': '', 'slots': []})

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

def move_intention_up(di, si, ii):
    lst = st.session_state.days[di]['slots'][si]['intentions']
    if ii > 0:
        lst[ii], lst[ii-1] = lst[ii-1], lst[ii]

def move_intention_down(di, si, ii):
    lst = st.session_state.days[di]['slots'][si]['intentions']
    if ii < len(lst) - 1:
        lst[ii], lst[ii+1] = lst[ii+1], lst[ii]


# ── UI ────────────────────────────────────────────────────────────────────────
st.title("✝ Mass Intentions PDF")
st.caption("Fill in the intentions below, then click **Generate PDF** to download.")

st.divider()

TIME_OPTIONS = ['7:00 AM', '12:15 N', '8:00 AM', '9:00 AM', '11:00 AM', '5:00 PM', 'Custom…']

for di, day in enumerate(st.session_state.days):
    with st.container():
        st.markdown('<div class="day-card">', unsafe_allow_html=True)

        col_name, col_del = st.columns([5, 1])
        with col_name:
            day['name'] = st.text_input(
                "Day & Date",
                value=day['name'],
                placeholder="e.g. Monday June 29 2026",
                key=f"day_{di}_name",
                label_visibility="collapsed",
            )
        with col_del:
            st.button("🗑", key=f"del_day_{di}",
                      on_click=remove_day, args=(di,),
                      help="Remove this day")

        for si, slot in enumerate(day['slots']):
            with st.container():
                st.markdown('<div class="slot-card">', unsafe_allow_html=True)

                tc1, tc2, tc3 = st.columns([2, 5, 0.6])
                with tc1:
                    time_sel = st.selectbox(
                        "Time",
                        TIME_OPTIONS,
                        index=TIME_OPTIONS.index(slot['time']) if slot['time'] in TIME_OPTIONS else len(TIME_OPTIONS)-1,
                        key=f"slot_{di}_{si}_sel",
                        label_visibility="collapsed",
                    )
                    if time_sel == 'Custom…':
                        slot['time'] = st.text_input("Custom time", value=slot['time'] if slot['time'] not in TIME_OPTIONS else '', key=f"slot_{di}_{si}_custom", label_visibility="collapsed")
                    else:
                        slot['time'] = time_sel

                with tc3:
                    st.button("🗑", key=f"del_slot_{di}_{si}",
                              on_click=remove_slot, args=(di, si),
                              help="Remove this slot")

                # Intentions
                for ii, intention in enumerate(slot['intentions']):
                    ic1, ic2, ic3, ic4, ic5 = st.columns([0.5, 3.5, 0.6, 0.6, 0.6])
                    with ic1:
                        intention['cross'] = st.checkbox(
                            "†",
                            value=intention['cross'],
                            key=f"int_{di}_{si}_{ii}_cross",
                            help="Check for deceased (†)",
                        )
                    with ic2:
                        intention['name'] = st.text_input(
                            "Name",
                            value=intention['name'],
                            placeholder="Name or intention…",
                            key=f"int_{di}_{si}_{ii}_name",
                            label_visibility="collapsed",
                        )
                    with ic3:
                        st.button("↑", key=f"up_{di}_{si}_{ii}",
                                  on_click=move_intention_up, args=(di, si, ii),
                                  disabled=(ii == 0))
                    with ic4:
                        st.button("↓", key=f"dn_{di}_{si}_{ii}",
                                  on_click=move_intention_down, args=(di, si, ii),
                                  disabled=(ii == len(slot['intentions'])-1))
                    with ic5:
                        st.button("✕", key=f"del_int_{di}_{si}_{ii}",
                                  on_click=remove_intention, args=(di, si, ii))

                if slot['intentions']:
                    st.caption("☑ = deceased (†)  |  unchecked = special intention")

                st.button(f"+ Add intention", key=f"add_int_{di}_{si}",
                          on_click=add_intention, args=(di, si))
                st.markdown('</div>', unsafe_allow_html=True)

        st.button("+ Add time slot", key=f"add_slot_{di}",
                  on_click=add_slot, args=(di,))
        st.markdown('</div>', unsafe_allow_html=True)

st.button("＋ Add day", on_click=add_day, type="secondary")

st.divider()

# Filename
filename = st.text_input(
    "PDF filename",
    value="WEEKDAY MASS INTENTIONS.pdf",
    help="What to name the downloaded file",
)
if not filename.endswith('.pdf'):
    filename += '.pdf'

# Generate
if st.button("📄 Generate PDF", type="primary", disabled=len(st.session_state.days) == 0):
    days_data = st.session_state.days
    # Filter out empty entries
    clean = []
    for d in days_data:
        if not d['name'].strip():
            continue
        slots = []
        for s in d['slots']:
            ints = [i for i in s['intentions'] if i['name'].strip()]
            if ints:
                slots.append({'time': s['time'], 'intentions': ints})
        if slots:
            clean.append({'name': d['name'].strip(), 'slots': slots})

    if not clean:
        st.warning("Please add at least one day with intentions before generating.")
    else:
        with st.spinner("Generating PDF…"):
            try:
                pdf_bytes = build_pdf_bytes(clean)
                st.success("PDF ready!")
                st.download_button(
                    label="⬇ Download PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"Error generating PDF: {e}")
                st.exception(e)
