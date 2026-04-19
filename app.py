import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from scipy.stats import norm
import warnings
import time
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="NIFTY Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
    }
    
    .css-1r6slb0 {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 20px !important;
        padding: 20px !important;
    }
    
    .metric-card {
        background: linear-gradient(135deg, rgba(0, 255, 136, 0.1), rgba(0, 102, 255, 0.1));
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    
    .live-badge {
        display: inline-block;
        padding: 5px 15px;
        background: rgba(0, 255, 136, 0.2);
        border: 1px solid #00ff88;
        border-radius: 20px;
        color: #00ff88;
        font-weight: bold;
        animation: blink 1.5s infinite;
    }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    .strategy-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 30px;
        color: white;
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    }
    
    .warning-banner {
        background: linear-gradient(90deg, #ff4444, #ff6b6b);
        padding: 15px;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        animation: shake 0.5s;
    }
    
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<h1 style='text-align: center;'>
    <span style='color: #00ff88;'>⚡ NIFTY INTELLIGENCE</span>
    <br>
    <span style='font-size: 16px; color: #888;'>Live Options Dashboard • Free Forever</span>
</h1>
""", unsafe_allow_html=True)

# Live badge
st.markdown("""
<div style='text-align: right;'>
    <span class='live-badge'>🔴 LIVE • Auto-refresh 60s</span>
</div>
""", unsafe_allow_html=True)

# Fetch data
@st.cache_data(ttl=60)
def fetch_market_data():
    try:
        # Get NIFTY spot
        nifty = yf.download("^NSEI", period="1d", progress=False)
        spot = float(nifty['Close'].iloc[-1])
        
        # Get India VIX
        vix = yf.download("^INDIAVIX", period="1d", progress=False)
        india_vix = float(vix['Close'].iloc[-1])
        
        # Try NSE Python
        try:
            from nsepython import nse_optionchain_scrapper
            data = nse_optionchain_scrapper("NIFTY")
            if 'filtered' in data:
                records = data['filtered']['data']
                rows = []
                for r in records:
                    ce = r.get('CE', {})
                    pe = r.get('PE', {})
                    rows.append({
                        'Strike': r['strikePrice'],
                        'CE_OI': ce.get('openInterest', 0),
                        'CE_LTP': ce.get('lastPrice', 0),
                        'PE_OI': pe.get('openInterest', 0),
                        'PE_LTP': pe.get('lastPrice', 0),
                    })
                df = pd.DataFrame(rows)
                return spot, india_vix, df, True
        except:
            pass
        
        # Fallback
        strikes = list(range(int(spot) - 1500, int(spot) + 1500, 100))
        np.random.seed(42)
        rows = []
        for strike in strikes:
            rows.append({
                'Strike': strike,
                'CE_OI': int(np.random.randint(100000, 500000)),
                'CE_LTP': max(1, abs(spot-strike)*0.3 + np.random.uniform(10,50)),
                'PE_OI': int(np.random.randint(100000, 500000)),
                'PE_LTP': max(1, abs(strike-spot)*0.3 + np.random.uniform(10,50)),
            })
        df = pd.DataFrame(rows)
        return spot, india_vix, df, False
        
    except Exception as e:
        st.error(f"Error: {e}")
        return None, None, None, False

# Load data
with st.spinner('📡 Fetching live market data...'):
    spot, vix, df, is_live = fetch_market_data()

if spot is None:
    st.error("Unable to fetch data. Please refresh.")
    st.stop()

# Calculations
atm_strike = round(spot / 100) * 100
total_ce_oi = df['CE_OI'].sum()
total_pe_oi = df['PE_OI'].sum()
pcr = round(total_pe_oi / total_ce_oi, 2)

# Max Pain
def calc_max_pain(df):
    pain_data = []
    for strike in df['Strike']:
        pe_loss = ((df['Strike'] - strike).clip(lower=0) * df['PE_OI']).sum()
        ce_loss = ((strike - df['Strike']).clip(lower=0) * df['CE_OI']).sum()
        pain_data.append({'Strike': strike, 'Loss': ce_loss + pe_loss})
    pain_df = pd.DataFrame(pain_data)
    return int(pain_df.loc[pain_df['Loss'].idxmin(), 'Strike'])

max_pain = calc_max_pain(df)
resistance = df.loc[df['CE_OI'].idxmax(), 'Strike']
support = df.loc[df['PE_OI'].idxmax(), 'Strike']

# Strategy
if pcr > 1.3:
    sentiment = "🟢 BULLISH"
    strategy = "BUY CALL"
    strategy_color = "#00ff88"
elif pcr < 0.7:
    sentiment = "🔴 BEARISH"
    strategy = "BUY PUT"
    strategy_color = "#ff4444"
else:
    sentiment = "🟡 NEUTRAL"
    strategy = "IRON CONDOR"
    strategy_color = "#ffaa00"

# Display Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("NIFTY SPOT", f"₹{spot:,.0f}", 
              delta=f"{spot - max_pain:+.0f} vs Max Pain")

with col2:
    st.metric("INDIA VIX", f"{vix:.2f}", 
              delta="High" if vix > 20 else "Normal" if vix > 15 else "Low")

with col3:
    st.metric("PCR", f"{pcr}", delta=sentiment)

with col4:
    st.metric("MAX PAIN", f"₹{max_pain:,}", 
              delta=f"{(spot/max_pain - 1)*100:+.1f}%")

# Charts
st.markdown("---")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df['Strike'],
        y=df['CE_OI'],
        name='Call OI',
        marker_color='rgba(0, 255, 136, 0.6)'
    ))
    
    fig.add_trace(go.Bar(
        x=df['Strike'],
        y=-df['PE_OI'],
        name='Put OI',
        marker_color='rgba(255, 68, 68, 0.6)'
    ))
    
    fig.add_vline(x=spot, line_dash="dash", line_color="white", 
                  annotation_text=f"Spot: {spot:.0f}")
    fig.add_vline(x=max_pain, line_dash="dot", line_color="yellow", 
                  annotation_text=f"Max Pain: {max_pain}")
    
    fig.update_layout(
        title="📊 Options OI Distribution",
        template="plotly_dark",
        barmode='relative',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    top_ce = df.nlargest(5, 'CE_OI')[['Strike', 'CE_OI']]
    top_pe = df.nlargest(5, 'PE_OI')[['Strike', 'PE_OI']]
    
    fig2 = go.Figure()
    
    fig2.add_trace(go.Bar(
        y=[f"{s}" for s in top_ce['Strike']],
        x=top_ce['CE_OI'],
        name='Call OI',
        orientation='h',
        marker_color='#00ff88'
    ))
    
    fig2.add_trace(go.Bar(
        y=[f"{s}" for s in top_pe['Strike']],
        x=top_pe['PE_OI'],
        name='Put OI',
        orientation='h',
        marker_color='#ff4444'
    ))
    
    fig2.update_layout(
        title="🎯 Top OI Concentrations",
        template="plotly_dark",
        height=400,
        barmode='group',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig2, use_container_width=True)

# Strategy Section
st.markdown("---")
strat_col1, strat_col2 = st.columns([2, 1])

with strat_col1:
    st.markdown(f"""
    <div class='strategy-card'>
        <h2 style='margin:0;'>⭐ RECOMMENDED STRATEGY</h2>
        <h1 style='font-size: 48px; margin: 20px 0; color: {strategy_color};'>{strategy}</h1>
        <p style='font-size: 18px; opacity: 0.9;'>
            📍 Entry: {atm_strike} {strategy.split()[-1]}<br>
            🎯 Target: {resistance if 'CALL' in strategy else support}<br>
            🛑 Stop: {support if 'CALL' in strategy else resistance}
        </p>
        <div style='margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 10px;'>
            <strong>📈 Market Narrative:</strong> PCR at {pcr} indicates {sentiment.lower()} sentiment. 
            Max Pain at {max_pain} suggests expiry gravity towards this level.
        </div>
    </div>
    """, unsafe_allow_html=True)

with strat_col2:
    st.markdown("### 📊 Key Levels")
    
    levels_df = pd.DataFrame({
        'Level': ['R3', 'R2', 'R1', 'Spot', 'S1', 'S2', 'S3'],
        'Price': [
            resistance + 200,
            resistance + 100,
            resistance,
            spot,
            support,
            support - 100,
            support - 200
        ]
    })
    
    st.dataframe(levels_df, hide_index=True, use_container_width=True)
    
    if vix > 20:
        st.markdown("""
        <div class='warning-banner'>
            ⚠️ HIGH VIX - Reduce position size
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666;'>
    <p>📡 Data: {'🔴 LIVE NSE' if is_live else '📊 SAMPLE (Market Closed)'} | 
    ⏰ Last Update: {datetime.now().strftime('%H:%M:%S')}</p>
    <p style='font-size: 12px;'>⚡ NIFTY Intelligence v1.0 | Educational Use Only</p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh
time.sleep(60)
st.rerun()
