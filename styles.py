"""Dark navy theme. Colors and spacing are tokens in :root; components use only the tokens.

Selectors rely on Streamlit's stable data-testid attributes and on our own class names
(and st.container keys), never on generated class names.
"""

APP_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

/* =============== 1. Tokens =============== */
:root {
    --bg: #0A1424;
    --surface: #0F1D33;
    --card: #12233D;
    --card-2: #172B4A;
    --line: #243B5E;
    --text: #E7EEF8;
    --muted: #8FA3BF;
    --cyan: #22D3EE;
    --cyan-hi: #67E8F9;
    --cyan-tint: rgba(34, 211, 238, .10);
    --violet: #8B7CF6;
    --ok: #34D399;
    --ok-tint: rgba(52, 211, 153, .12);
    --bad: #F87171;
    --bad-tint: rgba(248, 113, 113, .12);
    --ink: #06202B;
    --radius: 16px;
    --radius-sm: 12px;
    --shadow: 0 1px 0 rgba(255, 255, 255, .03) inset, 0 10px 30px rgba(0, 0, 0, .28);
    --font: "Manrope", "Segoe UI", system-ui, -apple-system, Roboto, Arial, sans-serif;
}

/* =============== 2. Page and Streamlit chrome =============== */
.stApp { background: var(--bg); color: var(--text); }
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp button, .stApp input, .stApp textarea, [data-baseweb="tab"] { font-family: var(--font); }
header[data-testid="stHeader"] { background: transparent; }
footer, #MainMenu { visibility: hidden; }
.block-container { max-width: 1180px; padding-top: 1.2rem; padding-bottom: 2rem; }
.stApp h3 { font-size: 1.25rem; font-weight: 700; letter-spacing: -.01em; color: var(--text); }
[data-testid="stCaptionContainer"] { color: var(--muted); }

/* =============== 3. Top bar =============== */
.topbar {
    display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;
    padding: .9rem 1.2rem; margin-bottom: 1.1rem;
    background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow);
}
.brand { display: flex; align-items: center; gap: .85rem; }
.logo { flex: none; display: block; }
.brand-name { font-size: 1.1rem; font-weight: 800; letter-spacing: -.01em; color: var(--text); line-height: 1.2; }
.brand-sub { font-size: .85rem; color: var(--muted); margin-top: .1rem; }
.topbar-status { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }

/* =============== 4. Cards and headings =============== */
[class*="st-key-card_"] {
    background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
    box-shadow: var(--shadow); padding: 1.3rem 1.4rem;
}
.card-title { font-size: 1rem; font-weight: 700; color: var(--text); }
.card-sub { color: var(--muted); font-size: .88rem; margin: .2rem 0 .4rem; line-height: 1.5; max-width: 64ch; }
.sec-head { margin: 1.6rem 0 .8rem; }
.sec-head h3 { margin: 0; padding: 0; }
.sec-head p { color: var(--muted); font-size: .92rem; margin: .25rem 0 0; }

/* =============== 5. Tabs (segmented) =============== */
.stTabs [data-baseweb="tab-list"] {
    gap: .25rem; padding: .3rem; width: fit-content; max-width: 100%; overflow-x: auto;
    background: var(--surface); border: 1px solid var(--line); border-radius: 14px;
}
.stTabs [data-baseweb="tab"] {
    height: auto; padding: .55rem 1rem; border-radius: 10px; color: var(--muted); font-weight: 600;
    transition: background .15s ease, color .15s ease;
}
.stTabs [data-baseweb="tab"]:hover { background: var(--card); color: var(--text); }
.stTabs [aria-selected="true"], .stTabs [aria-selected="true"] p { background: var(--cyan-tint); color: var(--cyan-hi); }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding-top: .6rem; }

/* =============== 6. Metric cards =============== */
.mgrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: .85rem; margin: .4rem 0 1rem; }
.mcard {
    background: var(--card); border: 1px solid var(--line); border-radius: var(--radius-sm);
    padding: 1rem 1.1rem; box-shadow: var(--shadow); transition: border-color .15s ease, transform .15s ease;
}
.mcard:hover { border-color: #35557F; }
.mcard-top { display: flex; align-items: center; gap: .55rem; color: var(--muted); }
.mcard-ico { display: inline-flex; color: var(--cyan); }
.mcard-label { font-size: .8rem; font-weight: 600; }
.mcard-value {
    margin-top: .55rem; font-size: 1.45rem; font-weight: 700; color: var(--text);
    font-variant-numeric: tabular-nums; overflow-wrap: anywhere;
}
.mcard.accent { background: var(--cyan-tint); border-color: rgba(34, 211, 238, .55); }
.mcard.accent .mcard-value { color: var(--cyan-hi); font-size: 1.7rem; }

/* =============== 7. Buttons =============== */
.stButton > button, .stDownloadButton > button {
    border-radius: var(--radius-sm); font-weight: 600; min-height: 2.8rem; padding: .6rem 1.3rem;
    transition: background .15s ease, border-color .15s ease, box-shadow .15s ease;
}
button[data-testid="stBaseButton-primary"] { background: var(--cyan); border: 1px solid var(--cyan); color: var(--ink); }
button[data-testid="stBaseButton-primary"] p { color: var(--ink); font-weight: 700; }
button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
    background: var(--cyan-hi); border-color: var(--cyan-hi); box-shadow: 0 6px 20px rgba(34, 211, 238, .25);
}
button[data-testid="stBaseButton-secondary"] { background: var(--card-2); border: 1px solid var(--line); color: var(--text); }
button[data-testid="stBaseButton-secondary"]:hover:not(:disabled) { border-color: var(--cyan); color: var(--cyan-hi); }
button:disabled { opacity: .4; }
button:focus-visible { outline: 3px solid rgba(34, 211, 238, .5); outline-offset: 2px; }

/* =============== 8. Inputs and uploader =============== */
[data-baseweb="input"], [data-baseweb="select"] > div { border-radius: 10px; border-color: var(--line); }
[data-baseweb="input"]:focus-within, [data-baseweb="select"]:focus-within > div { border-color: var(--cyan); }
[data-testid="stRadio"] [role="radiogroup"] { gap: .5rem; }
[data-testid="stRadio"] label[data-baseweb="radio"] {
    border: 1px solid var(--line); border-radius: 10px; padding: .4rem .85rem; margin: 0; background: var(--surface);
    transition: border-color .15s ease, background .15s ease;
}
[data-testid="stRadio"] label[data-baseweb="radio"]:hover { border-color: var(--cyan); }
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) { border-color: var(--cyan); background: var(--cyan-tint); }
[data-testid="stFileUploaderDropzone"] {
    background: rgba(34, 211, 238, .04); border: 1.5px dashed rgba(34, 211, 238, .45);
    border-radius: 14px; padding: 1.3rem; transition: background .15s ease, border-color .15s ease;
}
[data-testid="stFileUploaderDropzone"]:hover { background: var(--cyan-tint); border-color: var(--cyan); }

/* =============== 9. Tags, pills, banners =============== */
.tag {
    display: inline-block; padding: .2rem .7rem; border-radius: 8px; margin-bottom: .5rem;
    font-size: .78rem; font-weight: 700; background: var(--card-2); color: var(--muted); border: 1px solid var(--line);
}
.tag.out { background: var(--cyan-tint); color: var(--cyan-hi); border-color: rgba(34, 211, 238, .45); }
.pill { display: inline-flex; align-items: center; gap: .45rem; padding: .32rem .8rem; border-radius: 999px; font-size: .82rem; font-weight: 700; }
.pill::before { content: ""; width: .5rem; height: .5rem; border-radius: 50%; background: currentColor; }
.pill.ok { background: var(--ok-tint); color: var(--ok); }
.pill.bad { background: var(--bad-tint); color: var(--bad); }
.pill.idle { background: var(--card-2); color: var(--muted); }
.status-detail { color: var(--muted); font-size: .85rem; font-weight: 500; }
.banner {
    display: flex; flex-wrap: wrap; align-items: baseline; gap: .6rem; padding: .7rem 1rem;
    border-radius: var(--radius-sm); margin-bottom: .9rem; border: 1px solid var(--line);
}
.banner.ok { background: var(--ok-tint); border-color: rgba(52, 211, 153, .4); }
.banner-title { font-weight: 700; color: var(--ok); }
.banner-detail { color: var(--muted); font-size: .88rem; overflow-wrap: anywhere; }

/* =============== 10. Steps, glossary, empty states =============== */
.steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: .85rem; }
.step { display: flex; gap: .85rem; padding: 1rem 1.1rem; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius-sm); }
.step-n {
    flex: none; width: 1.7rem; height: 1.7rem; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
    font-size: .85rem; font-weight: 800; color: var(--ink); background: var(--cyan);
}
.step-t { font-weight: 700; color: var(--text); }
.step-d { color: var(--muted); font-size: .88rem; margin-top: .2rem; line-height: 1.5; }
.gloss-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: .85rem; }
.gloss { padding: .9rem 1rem; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-sm); }
.gloss-t { font-weight: 700; color: var(--cyan-hi); }
.gloss-d { color: var(--muted); font-size: .88rem; margin-top: .25rem; line-height: 1.55; }
.empty {
    text-align: center; padding: 2.2rem 1.2rem; border: 1.5px dashed var(--line); border-radius: var(--radius);
    background: var(--surface);
}
.empty-ico { display: inline-flex; color: var(--cyan); margin-bottom: .6rem; }
.empty-title { font-weight: 700; color: var(--text); }
.empty-text { color: var(--muted); font-size: .9rem; margin: .3rem auto 0; max-width: 52ch; line-height: 1.55; }

/* =============== 11. Media, tables, status, expanders =============== */
[data-testid="stImage"] img { border-radius: var(--radius-sm); border: 1px solid var(--line); }
[data-testid="stImageCaption"] { color: var(--muted); }
video { border-radius: var(--radius-sm); }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: var(--radius-sm); overflow: hidden; }
[data-testid="stAlert"] { border-radius: var(--radius-sm); }
[data-testid="stStatus"], [data-testid="stExpander"] { border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--surface); }

/* =============== 12. Footer =============== */
.app-foot { margin-top: 2.5rem; padding: 1.2rem 0 .5rem; border-top: 1px solid var(--line); text-align: center; }
.foot-name { color: var(--text); font-weight: 600; font-size: .9rem; }
.foot-tag { color: var(--muted); font-size: .82rem; margin-top: .25rem; }

/* =============== 13. Small screens and motion =============== */
@media (max-width: 640px) {
    .block-container { padding: .8rem .8rem 2rem; }
    .topbar { padding: .8rem 1rem; }
    .brand-name { font-size: 1rem; }
    .stButton > button, .stDownloadButton > button { width: 100%; }
    [class*="st-key-card_"] { padding: 1rem; }
    .stTabs [data-baseweb="tab"] { padding: .5rem .7rem; font-size: .85rem; }
    .mcard-value { font-size: 1.25rem; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""
