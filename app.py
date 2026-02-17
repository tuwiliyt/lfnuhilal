import streamlit as st
import pandas as pd
import datetime
import time
import plotly.graph_objects as go
import math
import numpy as np
import streamlit.components.v1 as components

# Page Config
st.set_page_config(page_title="LFNU Gorontalo - Precision Engine", layout="wide")

# NU Visibility Criteria Constants (Standard 1447H)
ALTITUDE_THRESHOLD_IRNU = 3.0
ELONGATION_THRESHOLD_IRNU = 6.4
ELONGATION_THRESHOLD_QRNU = 9.9

# Advanced CSS for NU Gorontalo Theme (NU Green #006400 & Gold #D4AF37)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Orbitron:wght@400;700&display=swap');
    .stApp { background-color: #000000; color: #ffffff; font-family: 'Montserrat', sans-serif; }
    [data-testid='stSidebar'] { background-color: #002200; border-right: 2px solid #D4AF37; }
    .hilal-card { background: rgba(0, 40, 0, 0.8); padding: 25px; border-radius: 15px; border: 1px solid #D4AF37; box-shadow: 0 0 15px rgba(212, 175, 55, 0.3); margin-bottom: 20px; }
    .status-alert { padding: 20px; border-radius: 10px; text-align: center; font-family: 'Orbitron', sans-serif; border: 2px solid; }
    h1, h2, h3 { color: #D4AF37 !important; font-weight: 700; }
    .digital-clock { font-size: 24px; color: #D4AF37; font-weight: bold; font-family: 'Courier New', monospace; }
    div[data-testid='stMetricValue'] { color: #ffffff !important; font-family: 'Orbitron', sans-serif; }
    .sidebar-title { color: #D4AF37; font-size: 22px; font-weight: bold; text-align: center; margin-bottom: 20px; border-bottom: 1px solid #D4AF37; padding-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- ASTRONOMICAL ENGINE ---
LAT_GORONTALO = 0.5425734567096381
LON_GORONTALO = 123.0666501530012

def get_julian_day(dt_utc):
    y, m, d = dt_utc.year, dt_utc.month, dt_utc.day
    h, mn, s = dt_utc.hour, dt_utc.minute, dt_utc.second
    if m <= 2:
        y -= 1
        m += 12
    A = math.floor(y / 100)
    B = 2 - A + math.floor(A / 4)
    jd = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + B - 1524.5
    day_fraction = (h + mn/60 + s/3600) / 24
    return jd + day_fraction

def eq_to_horiz(ra, dec, lst, lat):
    ha = math.radians(lst - ra)
    dec_rad, lat_rad = math.radians(dec), math.radians(lat)
    alt = math.asin(math.sin(dec_rad)*math.sin(lat_rad) + math.cos(dec_rad)*math.cos(lat_rad)*math.cos(ha))
    az = math.atan2(-math.sin(ha)*math.cos(dec_rad), math.cos(lat_rad)*math.sin(dec_rad) - math.sin(lat_rad)*math.cos(dec_rad)*math.cos(ha))
    return math.degrees(az) % 360, math.degrees(alt)

def calculate_positions(custom_dt_utc=None):
    dt_utc = custom_dt_utc if custom_dt_utc else datetime.datetime.now(datetime.timezone.utc)
    jd = get_julian_day(dt_utc)
    d = jd - 2451545.0
    L = (280.460 + 0.9856474 * d) % 360
    g = math.radians((357.528 + 0.9856003 * d) % 360)
    ecl_long = math.radians(L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    eps = math.radians(23.439)
    ra_s = math.degrees(math.atan2(math.cos(eps) * math.sin(ecl_long), math.cos(ecl_long)))
    dec_s = math.degrees(math.asin(math.sin(eps) * math.sin(ecl_long)))
    L_m = (218.32 + 13.176396 * d) % 360
    M_m = math.radians((134.96 + 13.064993 * d) % 360)
    ra_m = L_m + 6.29 * math.sin(M_m)
    dec_m = math.degrees(math.radians(5.13 * math.sin(math.radians((93.27 + 13.22935 * d) % 360))))
    ut_hours = dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
    gmst = (100.4606184 + 0.9856473662862 * d + ut_hours * 15) % 360
    lst = (gmst + LON_GORONTALO) % 360
    az_s, alt_s = eq_to_horiz(ra_s, dec_s, lst, LAT_GORONTALO)
    az_m, alt_m = eq_to_horiz(ra_m, dec_m, lst, LAT_GORONTALO)
    r1, d1, r2, d2 = map(math.radians, [ra_s, dec_s, ra_m, dec_m])
    cos_e = math.sin(d1)*math.sin(d2) + math.cos(d1)*math.cos(d2)*math.cos(r1 - r2)
    elong = math.degrees(math.acos(max(-1, min(1, cos_e))))
    dt_wita = dt_utc + datetime.timedelta(hours=8)
    return {'sun': (az_s, alt_s), 'moon': (az_m, alt_m), 'elong': elong, 'time_wita': dt_wita.strftime('%Y-%m-%d %H:%M:%S'), 'jd': jd, 'lst': lst, 'utc': dt_utc.strftime('%H:%M:%S')}

def get_compliance(moon_alt, sun_alt, elong):
    if sun_alt > 0: return "ISTIHALAH", "#64748b", "☀️ Matahari masih di atas ufuk."
    if moon_alt <= 0: return "ISTIHALAH", "#ef4444", "🚫 Hilal di bawah ufuk."
    if elong >= ELONGATION_THRESHOLD_QRNU: return "QATH’I", "#10b981", "✅ Memenuhi kriteria Qath'i."
    if moon_alt >= ALTITUDE_THRESHOLD_IRNU and elong >= ELONGATION_THRESHOLD_IRNU: return "IMKAN", "#3b82f6", "🌓 Memenuhi kriteria Imkan."
    return "ISTIHALAH", "#f59e0b", "⚠️ Tidak memenuhi kriteria IRNU."

# --- UI SETUP ---
nu_logo = "https://upload.wikimedia.org/wikipedia/id/thumb/a/a2/Logo_Nahdlatul_Ulama.svg/1200px-Logo_Nahdlatul_Ulama.svg.png"
st.sidebar.image(nu_logo, width=150)
st.sidebar.markdown('<div class="sidebar-title">LFNU GORONTALO</div>', unsafe_allow_html=True)
mode = st.sidebar.selectbox("Mode Engine", ["Real-time", "Target Ghurub (17 Feb 2026)"])
clock_spot = st.sidebar.empty()
page = st.sidebar.radio('Pilih Menu', ['Gorontalo Hub', 'Observasi Barat', 'Peta Cuaca Gorontalo', 'Simulasi 3D'])
target_dt_utc = datetime.datetime(2026, 2, 17, 10, 5, 0, tzinfo=datetime.timezone.utc)
main_placeholder = st.empty()

while True:
    pos = calculate_positions(target_dt_utc if mode == "Target Ghurub (17 Feb 2026)" else None)
    clock_spot.markdown(f'<p class="digital-clock">{pos["time_wita"]} WITA</p>', unsafe_allow_html=True)
    with main_placeholder.container():
        if page == 'Gorontalo Hub':
            st.title('🌙 Lembaga Falakiyah NU Gorontalo')
            label, color, desc = get_compliance(pos['moon'][1], pos['sun'][1], pos['elong'])
            st.markdown(f'<div class="status-alert" style="border-color: {color}; color: {color}; background: {color}1A"><h2>STATUS VISIBILITAS: {label}</h2><p>{desc}</p></div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Moon Altitude", f"{pos['moon'][1]:.4f}°")
            c2.metric("Elongation", f"{pos['elong']:.4f}°")
            c3.metric("Sun Altitude", f"{pos['sun'][1]:.4f}°")
            st.write(f"**LFNU Engine Logs:** UTC={pos['utc']} | LST={pos['lst']:.4f}° | JD={pos['jd']:.5f}")
        elif page == 'Observasi Barat':
            st.title('🌅 Observasi Sektor Barat (Ghurub)')
            fig = go.Figure()
            fig.add_hline(y=0, line_width=3, line_color="#D4AF37", annotation_text="Ufuk")
            fig.add_hline(y=3, line_dash="dash", line_color="rgba(255,255,255,0.5)", annotation_text="IRNU (3°)")
            fig.add_trace(go.Scatter(x=[pos['sun'][0]], y=[pos['sun'][1]], mode='markers+text', 
                                     text=[f"SUN: {pos['sun'][1]:.2f}°"], textposition="bottom center",
                                     marker=dict(size=35, color='#FFD700', line=dict(width=2, color='white')), name='Sun'))
            fig.add_trace(go.Scatter(x=[pos['moon'][0]], y=[pos['moon'][1]], mode='markers+text', 
                                     text=[f"HILAL: {pos['moon'][1]:.2f}°"], textposition="top center",
                                     marker=dict(size=25, color='white', symbol='circle-open-dot'), name='Moon'))
            fig.update_layout(xaxis=dict(title='Azimuth (°)', range=[240, 300]), yaxis=dict(title='Altitude (°)', range=[-10, 20]), 
                              template="plotly_dark", uirevision='constant', height=600)
            st.plotly_chart(fig, use_container_width=True)
        elif page == 'Peta Cuaca Gorontalo':
            st.title('☁️ Peta Visibilitas Cuaca Gorontalo')
            windy_url = f"https://embed.windy.com/embed2.html?lat={LAT_GORONTALO}&lon={LON_GORONTALO}&zoom=11&overlay=clouds&marker=true"
            components.html(f'<iframe width="100%" height="600" src="{windy_url}" frameborder="0"></iframe>', height=600)
        elif page == 'Simulasi 3D':
            st.title('🔭 Simulasi Selestial 3D')
            fig = go.Figure()
            theta = np.linspace(0, 2*np.pi, 100)
            fig.add_trace(go.Scatter3d(x=np.cos(theta), y=np.sin(theta), z=np.zeros(100), mode='lines', line=dict(color='#D4AF37', width=6)))
            s_az, s_alt = math.radians(pos['sun'][0]), math.radians(pos['sun'][1])
            m_az, m_alt = math.radians(pos['moon'][0]), math.radians(pos['moon'][1])
            # Marker Sun 3D with label
            fig.add_trace(go.Scatter3d(x=[math.cos(s_alt)*math.cos(s_az)], y=[math.cos(s_alt)*math.sin(s_az)], z=[math.sin(s_alt)], 
                                       mode='markers+text', text=[f"SUN: {pos['sun'][1]:.2f}°"], 
                                       marker=dict(size=14, color='#FFD700'), name='Sun'))
            # Marker Moon 3D with label
            fig.add_trace(go.Scatter3d(x=[math.cos(m_alt)*math.cos(m_az)], y=[math.cos(m_alt)*math.sin(m_az)], z=[math.sin(m_alt)], 
                                       mode='markers+text', text=[f"HILAL: {pos['moon'][1]:.2f}°"], 
                                       marker=dict(size=12, color='#ffffff'), name='Moon'))
            fig.update_layout(scene=dict(bgcolor='#000000', xaxis_visible=False, yaxis_visible=False, zaxis_visible=False), 
                              paper_bgcolor='#000000', height=700, uirevision='constant')
            st.plotly_chart(fig, use_container_width=True)
    if mode == "Target Ghurub (17 Feb 2026)": break
    time.sleep(1)
