"""Decidr Coherence Engine — System 1 (v4). streamlit run app.py"""
import json, time, os
from datetime import datetime
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
from schemas import (GoalInput, System3Payload, BUCKET_HIERARCHY, METRIC_UNITS,
    SCENARIOS, DIMS, WEIGHTS, get_l2_for_l1, get_l3_for_l2)
from goal_extractor import GoalExtractor

st.set_page_config(page_title="Decidr · Coherence Engine", page_icon="⚙️",
    layout="wide", initial_sidebar_state="expanded")

# ═══ THEME ═══════════════════════════════════════════════════════════════════
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
.stApp{font-family:'Outfit',sans-serif;background:linear-gradient(170deg,#0c0a09,#1c1917 50%,#0f0e0d)}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#1c1917,#0c0a09);border-right:1px solid rgba(217,158,60,.08)}
#MainMenu,.stDeployButton{visibility:hidden}
html,body,[class*="css"]{cursor:default}
a,button,[role="button"],select,.stButton>button,.stDownloadButton>button{cursor:pointer!important}
input,textarea{cursor:text!important}
/* cards */
.gc{background:rgba(28,25,23,.92);border:1px solid rgba(217,158,60,.12);border-radius:14px;padding:20px;margin-bottom:12px}
.gc-glow{background:linear-gradient(135deg,rgba(217,158,60,.06),rgba(28,25,23,.95));border:1px solid rgba(217,158,60,.25);border-radius:14px;padding:20px;margin-bottom:12px}
.gc-hl{background:linear-gradient(135deg,rgba(217,158,60,.1),rgba(28,25,23,.92));border:2px solid rgba(217,158,60,.35);border-radius:14px;padding:20px;margin-bottom:12px}
.gc-kpi{background:rgba(28,25,23,.92);border:1px solid rgba(217,158,60,.12);border-radius:14px;padding:16px;text-align:center}
/* badges */
.badge{display:inline-block;padding:5px 16px;border-radius:20px;background:rgba(217,158,60,.08);border:1px solid rgba(217,158,60,.2);font-size:11px;font-weight:600;color:#d9a03c;font-family:'JetBrains Mono',monospace;letter-spacing:.08em;margin-bottom:14px}
.sb{display:inline-block;padding:3px 11px;border-radius:12px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.05em}
.sb-goal{background:rgba(59,130,246,.12);color:#60a5fa;border:1px solid rgba(59,130,246,.2)}
.sb-l2{background:rgba(217,158,60,.12);color:#d9a03c;border:1px solid rgba(217,158,60,.2)}
.sb-l1{background:rgba(244,114,182,.12);color:#f472b6;border:1px solid rgba(244,114,182,.2)}
/* utility */
.wc{text-align:right;font-size:11px;color:#78716c;font-family:'JetBrains Mono',monospace;margin-top:-6px}
.sl{font-size:11px;font-weight:600;color:#78716c;text-transform:uppercase;letter-spacing:.08em;margin:20px 0 10px}
.bar-w{height:6px;background:rgba(120,113,108,.15);border-radius:3px;overflow:hidden;margin:8px 0}
.bar-f{height:6px;border-radius:3px}
@keyframes pulse{0%,100%{opacity:.3}50%{opacity:1}}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;background:#d9a03c;margin:0 4px}
.dot:nth-child(1){animation:pulse 1.4s infinite 0s}
.dot:nth-child(2){animation:pulse 1.4s infinite .2s}
.dot:nth-child(3){animation:pulse 1.4s infinite .4s}
/* override streamlit widgets */
.stProgress>div>div{background:rgba(120,113,108,.15)!important}
.stProgress>div>div>div{background:linear-gradient(90deg,#d9a03c,#b45309)!important}
div[data-testid="stMetricValue"]{font-family:'Outfit',sans-serif}
div[data-testid="stMetricLabel"]{color:#78716c!important}
</style>""", unsafe_allow_html=True)

# ═══ STATE ═══════════════════════════════════════════════════════════════════
for k,v in {"page":"input","nl_input":"","extracted":None,"show_fields":False,
    "show_preview":False,"l1":"","l2":"","l3":"","metric_name":"","metric_unit":"score",
    "target_value":"","initial_value":"","periods":24,"scenario":"optimal","scope":"goal",
    "payload_json":None,"goal_history":[],"score_result":None,"feedback":None}.items():
    if k not in st.session_state: st.session_state[k]=v

@st.cache_resource
def _ext(): return GoalExtractor(use_llm=True)
extractor=_ext()
OUT=Path("outputs"); OUT.mkdir(exist_ok=True)

def _sc(s): return "#4ade80" if s>=.5 else "#fbbf24" if s>=.35 else "#f87171"
def _rl(s): return "Critical" if s<.2 else "At Risk" if s<.35 else "On Track"
def _bp():
    p=st.session_state.l1
    if st.session_state.l2: p+=f" → {st.session_state.l2}"
    if st.session_state.l3: p+=f" → {st.session_state.l3}"
    return p
def _payload():
    ext=st.session_state.extracted or {}
    g=GoalInput(goal_title=ext.get("goal_title",""),scope=st.session_state.scope,
        bucket_l1=st.session_state.l1,bucket_l2=st.session_state.l2,
        bucket_l3=st.session_state.l3 or None,metric_name=st.session_state.metric_name,
        metric_unit=st.session_state.metric_unit,
        target_value=float(st.session_state.target_value) if st.session_state.target_value else None,
        initial_value=float(st.session_state.initial_value) if st.session_state.initial_value else None,
        periods=st.session_state.periods,scenario_story=st.session_state.scenario)
    return System3Payload(goal=g,scope=st.session_state.scope,raw_nl_input=st.session_state.nl_input)
def _reset():
    for k in ["nl_input","l1","l2","l3","metric_name","target_value","initial_value"]: st.session_state[k]=""
    st.session_state.update(metric_unit="score",periods=24,scenario="optimal",scope="goal",
        extracted=None,show_fields=False,show_preview=False,payload_json=None,score_result=None,feedback=None,page="input")

@st.cache_data
def _load_csv():
    dfs={}
    for key,fn in {"composite":"composite_scores_poc.csv","portfolio":"portfolio_summary_poc.csv",
        "projection":"forward_projection_poc.csv","timeseries":"coherence_timeseries_poc.csv",
        "goals":"goals.csv","buckets":"buckets.csv"}.items():
        for d in ["data",".",".."]:
            p=os.path.join(d,fn)
            if os.path.exists(p):
                try: dfs[key]=pd.read_csv(p)
                except: pass
                break
    return dfs

DEMO={"goal_id":1,"attainability":.6823,"relevance":.7145,"coherence":.5891,"integrity":.6234,
    "overall":.6523,"gp_mean":.7012,"gp_std":.0834,"gp_weight":.706,"llm_weight":.294,"baseline":.65,"uncertain":False,
    "reasoning":{"attainability":"Trailing slope positive at 0.042/period. Projects to 89% of target.",
        "relevance":"5.6% of parent allocation, within optimal band. Strong priority alignment.",
        "coherence":"L3 proportional to L2 parent. Minor drift periods 8-10 but stabilised.",
        "integrity":"Output quality 0.78 aligns with inputs. Needle move ratio 0.85."},
    "ensemble_meta":{"attainability":{"gp_weight":.706,"llm_weight":.294,"gp_std":.0834},
        "relevance":{"rule_weight":.528,"llm_weight":.472,"variance":.0021},
        "coherence":{"rule_weight":.612,"llm_weight":.388,"variance":.0089},
        "integrity":{"rule_weight":.491,"llm_weight":.509,"variance":.0015}},
    "n_llm_ok":3,"status":"ok"}

# ═══ SIDEBAR (FIXED: only sets page when in input/portfolio) ═════════════════
with st.sidebar:
    st.markdown('<div style="padding:8px 0"><span style="font-size:18px;font-weight:700;color:#d9a03c">⚙️</span> <span style="font-size:15px;font-weight:600;color:#fafaf9">Coherence Engine</span></div>',unsafe_allow_html=True)
    st.caption("System 1 · Team 14-02")
    st.divider()
    if st.session_state.page in ("input","portfolio"):
        nav=st.radio("Nav",["🎯 Goal Input","📊 Portfolio"],label_visibility="collapsed",
            index=0 if st.session_state.page=="input" else 1)
        if "Input" in nav and st.session_state.page!="input": st.session_state.page="input"; st.rerun()
        if "Portfolio" in nav and st.session_state.page!="portfolio": st.session_state.page="portfolio"; st.rerun()
    elif st.session_state.page=="processing":
        st.info("⏳ Scoring in progress...")
    elif st.session_state.page=="output":
        st.success("✓ Score ready")
        if st.button("← New Goal",use_container_width=True): _reset(); st.rerun()
    if st.session_state.goal_history:
        st.divider()
        st.caption(f"**{len(st.session_state.goal_history)}** goals submitted")

# ═══ PAGE: INPUT ═════════════════════════════════════════════════════════════
if st.session_state.page=="input":
    st.markdown('<div class="badge">◆ GOAL INPUT</div>',unsafe_allow_html=True)
    st.markdown('<h1 style="font-weight:700;letter-spacing:-.02em">Score a Goal</h1>',unsafe_allow_html=True)
    st.caption("Describe your goal, review, then submit for coherence scoring.")
    st.markdown('<div class="sl">1 · Describe your goal</div>',unsafe_allow_html=True)
    nl=st.text_area("g",value=st.session_state.nl_input,height=130,max_chars=1600,
        placeholder="Describe your goal in plain English.\n\nExamples:\n• Improve NPS score from 60 to 85 over 24 months\n• Increase organic traffic across all Content & SEO channels by 40%\n• How are paid acquisition channels performing?",
        label_visibility="collapsed",key="nlw")
    st.session_state.nl_input=nl
    wc=len(nl.split()) if nl.strip() else 0
    st.markdown(f'<div class="wc" style="color:{"#f87171" if wc>200 else "#78716c"}">{wc}/200</div>',unsafe_allow_html=True)

    if st.button("Extract Goal Details",type="primary",use_container_width=True,disabled=not nl.strip() or wc>200):
        with st.spinner("Parsing with AI..."):
            r=extractor.extract(nl)
            st.session_state.extracted=r; st.session_state.show_fields=True; st.session_state.show_preview=False
            for k in ["scope","bucket_l1","bucket_l2"]:
                if r.get(k): st.session_state[k.replace("bucket_","")]=r[k]
            st.session_state.l3=r.get("bucket_l3") or ""
            if r.get("target_value") is not None: st.session_state.target_value=str(r["target_value"])
            if r.get("initial_value") is not None: st.session_state.initial_value=str(r["initial_value"])
            if r.get("metric_suggestion"): st.session_state.metric_name=r["metric_suggestion"]
            if r.get("unit_suggestion"): st.session_state.metric_unit=r["unit_suggestion"]
            st.rerun()

    if st.session_state.show_fields and st.session_state.extracted:
        ext=st.session_state.extracted
        st.markdown('<div class="sl">2 · Review extracted details</div>',unsafe_allow_html=True)
        nt=st.text_input("Goal Title",value=ext.get("goal_title",""),key="ti")
        st.session_state.extracted["goal_title"]=nt
        scope=st.session_state.scope
        scls={"goal":"sb-goal","l2_bucket":"sb-l2","l1_bucket":"sb-l1"}.get(scope,"sb-goal")
        slab={"goal":"Single Goal","l2_bucket":"Department Group","l1_bucket":"Division Group"}.get(scope,"Goal")
        st.markdown(f'<span class="sb {scls}">{slab}</span>',unsafe_allow_html=True)

        st.markdown("**Organisational Bucket**")
        b1,b2,b3=st.columns(3)
        with b1:
            lo=list(BUCKET_HIERARCHY.keys()); li=(lo.index(st.session_state.l1)+1) if st.session_state.l1 in lo else 0
            v=st.selectbox("L1 Division",["— Select —"]+lo,index=li,key="l1s")
            v="" if v.startswith("—") else v
            if v!=st.session_state.l1: st.session_state.l2=""; st.session_state.l3=""
            st.session_state.l1=v
        with b2:
            if st.session_state.l1:
                l2o=get_l2_for_l1(st.session_state.l1)
                l2i=(l2o.index(st.session_state.l2)+1) if st.session_state.l2 in l2o else 0
                v2=st.selectbox("L2 Department",["— Select —"]+l2o,index=l2i,key="l2s")
                v2="" if v2.startswith("—") else v2
                if v2!=st.session_state.l2: st.session_state.l3=""
                st.session_state.l2=v2
            else: st.selectbox("L2",["— Select L1 —"],disabled=True,key="l2d"); st.session_state.l2=""
        with b3:
            if st.session_state.l1 and st.session_state.l2:
                l3o=get_l3_for_l2(st.session_state.l1,st.session_state.l2)
                l3v=st.session_state.l3
                l3i=(l3o.index(l3v)+1) if l3v and l3v in l3o else 0
                v3=st.selectbox("L3 Function (optional)",["— All —"]+l3o,index=l3i,key="l3s")
                st.session_state.l3="" if v3.startswith("—") else v3
            else: st.selectbox("L3",["— Select L2 —"],disabled=True,key="l3d"); st.session_state.l3=""
        if st.session_state.l3: st.session_state.scope="goal"
        elif st.session_state.l2: st.session_state.scope="l2_bucket"
        elif st.session_state.l1: st.session_state.scope="l1_bucket"

        st.markdown("**Metric & Targets**")
        st.session_state.metric_name=st.text_input("Metric Name",value=st.session_state.metric_name,key="mn")
        c1,c2,c3=st.columns(3)
        with c1: st.session_state.initial_value=st.text_input("Initial Value",value=st.session_state.initial_value,key="iv")
        with c2: st.session_state.target_value=st.text_input("Target Value",value=st.session_state.target_value,key="tv")
        with c3: st.session_state.periods=st.number_input("Periods",value=st.session_state.periods,min_value=1,max_value=48,key="pr")
        u1,u2=st.columns(2)
        with u1: st.session_state.metric_unit=st.selectbox("Unit",METRIC_UNITS,index=METRIC_UNITS.index(st.session_state.metric_unit) if st.session_state.metric_unit in METRIC_UNITS else 0,key="un")
        with u2: st.session_state.scenario=st.selectbox("Scenario",SCENARIOS,index=SCENARIOS.index(st.session_state.scenario) if st.session_state.scenario in SCENARIOS else 0,key="scn")

        rdy=bool(ext.get("goal_title") and st.session_state.l1 and st.session_state.l2 and st.session_state.metric_name)
        if st.button("Review Goal",type="primary",use_container_width=True,disabled=not rdy):
            st.session_state.show_preview=True; st.rerun()

    if st.session_state.show_preview and st.session_state.extracted:
        ext=st.session_state.extracted
        st.markdown('<div class="sl">3 · Goal Preview</div>',unsafe_allow_html=True)
        scope=st.session_state.scope
        scls={"goal":"sb-goal","l2_bucket":"sb-l2","l1_bucket":"sb-l1"}.get(scope,"sb-goal")
        slab={"goal":"Single Goal","l2_bucket":"Department Group","l1_bucket":"Division Group"}.get(scope,"Goal")
        bp=_bp()
        st.markdown(f'<div class="gc-glow"><div style="font-size:22px;font-weight:700;color:#fafaf9;margin-bottom:6px">{ext["goal_title"]} <span class="sb {scls}" style="vertical-align:middle;margin-left:8px">{slab}</span></div><div style="font-size:13px;color:#a8a29e;margin-bottom:12px">{bp}</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><div><span style="font-size:11px;color:#78716c">Metric</span><br><span style="color:#d6d3d1">{st.session_state.metric_name} ({st.session_state.metric_unit})</span></div><div><span style="font-size:11px;color:#78716c">Range</span><br><span style="color:#d6d3d1">{st.session_state.initial_value or "?"} → {st.session_state.target_value or "?"}</span></div><div><span style="font-size:11px;color:#78716c">Timeline</span><br><span style="color:#d6d3d1">{st.session_state.periods} periods</span></div><div><span style="font-size:11px;color:#78716c">Scenario</span><br><span style="color:#d6d3d1">{st.session_state.scenario}</span></div></div></div>',unsafe_allow_html=True)
        with st.expander("View JSON"): st.json(json.loads(_payload().to_json()))
        a1,a2=st.columns([1,2])
        with a1:
            if st.button("✏️ Edit",use_container_width=True): st.session_state.show_preview=False; st.rerun()
        with a2:
            if st.button("Submit for Scoring →",type="primary",use_container_width=True):
                pl=_payload(); ts=datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                (OUT/f"goal_{ts}.json").write_text(pl.to_json())
                st.session_state.payload_json=pl.to_json()
                st.session_state.goal_history.append({"title":ext["goal_title"],"scope":scope,"bucket":bp,"time":ts})
                st.session_state.page="processing"; st.rerun()

# ═══ PAGE: PROCESSING ════════════════════════════════════════════════════════
elif st.session_state.page=="processing":
    title=st.session_state.extracted["goal_title"] if st.session_state.extracted else "Goal"
    _,cc,_=st.columns([1,2,1])
    with cc:
        st.markdown('<div style="text-align:center;padding:60px 0 16px"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>',unsafe_allow_html=True)
        st.markdown(f'<h2 style="text-align:center;font-weight:600">Scoring in progress</h2>',unsafe_allow_html=True)
        st.markdown(f'<p style="text-align:center;color:#a8a29e">Analysing <strong style="color:#d9a03c">{title}</strong></p>',unsafe_allow_html=True)
        bar=st.progress(0); status=st.empty()
        for i,msg in enumerate(["Sending to engine...","Computing features...","Dimension analysis...","Ensemble blending...","Generating report..."]):
            status.caption(f"⏳ {msg}"); bar.progress((i+1)/5); time.sleep(.5)
        status.caption("✓ Complete")
    demo=DEMO.copy(); demo["goal_title"]=title; demo["bucket_path"]=_bp()
    st.session_state.score_result=demo
    st.session_state["query"]=st.session_state.nl_input
    time.sleep(.3); st.session_state.page="output"; st.rerun()

# ═══ PAGE: OUTPUT ════════════════════════════════════════════════════════════
elif st.session_state.page=="output":
    s=st.session_state.score_result
    if not s: st.warning("No data."); st.stop()
    title=s.get("goal_title","Goal"); bp=s.get("bucket_path","")
    st.markdown('<div class="badge">◆ COHERENCE REPORT</div>',unsafe_allow_html=True)
    st.markdown(f'<h1 style="font-weight:700;letter-spacing:-.02em">{title}</h1>',unsafe_allow_html=True)
    if bp: st.markdown(f'<p style="color:#a8a29e;font-size:13px">{bp} · {st.session_state.metric_name} · {st.session_state.scenario}</p>',unsafe_allow_html=True)
    st.markdown("---")
    ov=s["overall"]; c=_sc(ov)
    st.markdown(f'<div class="gc-hl"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px"><div><div style="font-size:11px;color:#78716c;text-transform:uppercase;letter-spacing:.06em">Composite Coherence</div><div style="font-size:48px;font-weight:700;color:{c};line-height:1">{ov:.1%}</div><div style="font-size:12px;color:#a8a29e;margin-top:4px">{"High Confidence" if not s["uncertain"] else "⚠️ Elevated Uncertainty"} · σ={s["gp_std"]:.4f}</div></div><div style="text-align:right"><div style="font-size:11px;color:#78716c">Status</div><div style="font-size:22px;font-weight:600;color:{c}">{_rl(ov)}</div><div style="font-size:12px;color:#78716c;margin-top:4px">LLMs: {s["n_llm_ok"]}/3</div></div></div></div>',unsafe_allow_html=True)

    st.markdown('<div class="sl">Dimension Comparison</div>',unsafe_allow_html=True)
    cols=st.columns(4)
    for i,d in enumerate(DIMS):
        v=s[d]; c2=_sc(v)
        with cols[i]:
            st.markdown(f'<div class="gc-kpi"><div style="font-size:12px;color:#a8a29e">{d.capitalize()}</div><div style="font-size:28px;font-weight:700;color:{c2}">{v:.1%}</div><div class="bar-w"><div class="bar-f" style="width:{v*100:.0f}%;background:{c2}"></div></div><div style="font-size:10px;color:#78716c">{WEIGHTS[d]:.0%} weight</div></div>',unsafe_allow_html=True)

    st.markdown('<div class="sl">Dimension Analysis</div>',unsafe_allow_html=True)
    dd={"coherence":"Are decisions consistent across levels, goals, and time?","attainability":"Is the goal realistically achievable?","relevance":"Is allocation justified against stated goals?","integrity":"Are assumptions transparent and auditable?"}
    for d in DIMS:
        v=s[d]; c2=_sc(v); rsn=s["reasoning"].get(d,""); meta=s["ensemble_meta"].get(d,{})
        mp=[]
        if "gp_weight" in meta: mp.append(f"GP:{meta['gp_weight']:.0%}")
        if "rule_weight" in meta: mp.append(f"Rule:{meta['rule_weight']:.1%}")
        if "llm_weight" in meta: mp.append(f"LLM:{meta['llm_weight']:.1%}")
        if "variance" in meta: mp.append(f"Var:{meta['variance']:.4f}")
        ms=" · ".join(mp)
        cls="gc-hl" if d=="coherence" else "gc"
        st.markdown(f'<div class="{cls}"><div style="display:flex;justify-content:space-between;align-items:baseline"><div><span style="font-size:15px;font-weight:600;color:#fafaf9">{d.capitalize()}</span> <span style="font-size:12px;color:#78716c">— {dd.get(d,"")}</span></div><span style="font-size:22px;font-weight:700;color:{c2}">{v:.1%}</span></div><div class="bar-w"><div class="bar-f" style="width:{v*100:.0f}%;background:{c2}"></div></div><div style="font-size:13px;color:#d6d3d1;line-height:1.6;margin:10px 0 6px;border-left:3px solid {c2};padding-left:12px">{rsn}</div><div style="font-size:11px;color:#78716c">{ms}</div></div>',unsafe_allow_html=True)

    st.markdown('<div class="sl">Confidence</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="gc"><div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;text-align:center"><div><div style="font-size:11px;color:#78716c">Baseline</div><div style="font-size:22px;font-weight:600;color:#d6d3d1">{s["baseline"]:.1%}</div></div><div><div style="font-size:11px;color:#78716c">GP Mean</div><div style="font-size:22px;font-weight:600;color:#d6d3d1">{s["gp_mean"]:.1%}</div></div><div><div style="font-size:11px;color:#78716c">GP Weight</div><div style="font-size:22px;font-weight:600;color:#d6d3d1">{s["gp_weight"]:.0%}</div></div><div><div style="font-size:11px;color:#78716c">GP σ</div><div style="font-size:22px;font-weight:600;color:#d6d3d1">{s["gp_std"]:.4f}</div></div></div></div>',unsafe_allow_html=True)

    st.markdown('<div class="sl">Feedback</div>',unsafe_allow_html=True)
    f1,f2,f3=st.columns(3)
    with f1:
        if st.button("👍 Looks Right",use_container_width=True): st.session_state.feedback="positive"
    with f2:
        if st.button("🤔 Not Sure",use_container_width=True): st.session_state.feedback="neutral"
    with f3:
        if st.button("👎 Seems Off",use_container_width=True): st.session_state.feedback="negative"
    if st.session_state.feedback:
        st.caption({"positive":"Thanks! Recorded.","neutral":"Noted.","negative":"Thanks for flagging."}.get(st.session_state.feedback,""))

    st.markdown("---")
    d1,d2=st.columns(2)
    with d1: st.download_button("⬇ Score Report",data=json.dumps(s,indent=2),file_name=f"report_{title.replace(' ','_')}.json",mime="application/json",use_container_width=True)
    with d2:
        if st.session_state.payload_json: st.download_button("⬇ Input Payload",data=st.session_state.payload_json,file_name=f"input_{title.replace(' ','_')}.json",mime="application/json",use_container_width=True)
    st.markdown("---")
    a1,a2=st.columns(2)
    with a1:
        if st.button("+ New Goal",type="primary",use_container_width=True): _reset(); st.rerun()
    with a2:
        if st.button("🔄 Re-run",use_container_width=True): st.session_state.page="processing"; st.rerun()

# ═══ PAGE: PORTFOLIO ═════════════════════════════════════════════════════════
elif st.session_state.page=="portfolio":
    st.markdown('<div class="badge">◆ PORTFOLIO DASHBOARD</div>',unsafe_allow_html=True)
    st.markdown('<h1 style="font-weight:700;letter-spacing:-.02em">Portfolio Coherence</h1>',unsafe_allow_html=True)
    st.caption("Dataset health across all 35 goals · System 2 outputs")
    dfs=_load_csv(); comp=dfs.get("composite")
    if comp is None:
        st.markdown('<div class="gc" style="border-color:rgba(251,191,36,.3)"><div style="color:#fbbf24;font-weight:600;margin-bottom:8px">CSV files not found</div><div style="color:#a8a29e;font-size:13px">Place System 2 outputs in <code>data/</code> folder alongside app.py</div></div>',unsafe_allow_html=True)
        st.stop()
    goals=dfs.get("goals"); port=dfs.get("portfolio"); proj=dfs.get("projection"); ts=dfs.get("timeseries")
    scol="composite" if "composite" in comp.columns else comp.columns[5]
    total=len(comp); avg=comp[scol].mean(); ont=int((comp[scol]>=.35).sum()); ret=ont/total*100
    crit=int((comp[scol]<.2).sum()); risk=total-ont

    # ── KPIs (client criteria) ────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="sl">Portfolio Health</div>',unsafe_allow_html=True)
    k1,k2,k3,k4=st.columns(4)
    for col,label,val,sub in [(k1,"Portfolio Coherence",f"{avg:.1%}","across all dimensions"),(k2,"Goal Retention",f"{ret:.0f}%",f"{ont}/{total} on track"),(k3,"At Risk",str(risk),"below threshold"),(k4,"Critical",str(crit),"need action")]:
        with col: st.markdown(f'<div class="gc-kpi"><div style="font-size:11px;color:#78716c">{label}</div><div style="font-size:28px;font-weight:700;color:#fafaf9">{val}</div><div style="font-size:10px;color:#78716c">{sub}</div></div>',unsafe_allow_html=True)

    # Benchmark
    if ret>=88: st.markdown('<div class="gc" style="border-left:4px solid #4ade80"><span style="color:#4ade80;font-weight:600">Exceptional.</span> <span style="color:#a8a29e">Retention exceeds 86–88% benchmark.</span></div>',unsafe_allow_html=True)
    elif ret>=86: st.markdown('<div class="gc" style="border-left:4px solid #60a5fa"><span style="color:#60a5fa;font-weight:600">On target.</span> <span style="color:#a8a29e">Retention meets 86–88% benchmark.</span></div>',unsafe_allow_html=True)
    else: st.markdown(f'<div class="gc" style="border-left:4px solid #fbbf24"><span style="color:#fbbf24;font-weight:600">Below benchmark.</span> <span style="color:#a8a29e">Retention ({ret:.0f}%) is below the 86–88% target.</span></div>',unsafe_allow_html=True)

    # ── Dimension Averages ────────────────────────────────────────────────
    da={d:comp[d].mean() for d in DIMS if d in comp.columns}
    if da:
        st.markdown('<div class="sl">Average Dimension Scores</div>',unsafe_allow_html=True)
        dc=st.columns(4)
        for i,(d,av) in enumerate(da.items()):
            with dc[i]: st.markdown(f'<div class="gc-kpi"><div style="font-size:12px;color:#a8a29e">{d.capitalize()} ({WEIGHTS.get(d,.25):.0%})</div><div style="font-size:28px;font-weight:700;color:{_sc(av)}">{av:.1%}</div></div>',unsafe_allow_html=True)

    # ── Coherence Over Time ───────────────────────────────────────────────
    if ts is not None:
        st.markdown('<div class="sl">Coherence Over Time</div>',unsafe_allow_html=True)
        import streamlit.components.v1 as components
        labels=ts["period_id"].tolist()
        vals=[round(v,3) for v in ts["avg_composite"].tolist()]
        ar_vals=ts["at_risk_count"].tolist()
        components.html(f"""
        <div style="height:260px"><canvas id="ts"></canvas></div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
        <script>new Chart(document.getElementById('ts'),{{type:'line',data:{{labels:{json.dumps(labels)},datasets:[
        {{label:'Avg Composite',data:{json.dumps(vals)},borderColor:'#d9a03c',backgroundColor:'rgba(217,158,60,.08)',fill:true,tension:.3,pointRadius:3,borderWidth:2}},
        {{label:'Risk Threshold',data:{json.dumps([.35]*24)},borderColor:'#f87171',borderDash:[5,5],pointRadius:0,borderWidth:1.5,fill:false}}
        ]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#a8a29e',font:{{size:10}}}}}}}},
        scales:{{y:{{min:0,max:1,ticks:{{color:'#78716c',stepSize:.25}},grid:{{color:'rgba(120,113,108,.1)'}}}},
        x:{{ticks:{{color:'#78716c'}},grid:{{display:false}}}}}}}}}})</script>
        <div style="font-size:11px;color:#78716c;margin-top:4px">Periods 10-12: budget shock · Period 14: market shock</div>
        """, height=300)

    # ── Shock Analysis (client criteria) ──────────────────────────────────
    if ts is not None and len(ts)>=17:
        st.markdown('<div class="sl">Shock Analysis & Recovery</div>',unsafe_allow_html=True)
        pre = ts[(ts["period_id"]>=7)&(ts["period_id"]<=9)]["avg_composite"].mean()
        during = ts[(ts["period_id"]>=10)&(ts["period_id"]<=12)]["avg_composite"].mean()
        post = ts[(ts["period_id"]>=13)&(ts["period_id"]<=17)]["avg_composite"].mean()
        drop_pct = (pre-during)/pre*100 if pre else 0
        recovery_pct = (post-during)/(pre-during)*100 if (pre-during) else 0
        # Recovery speed: how many periods to get back to pre-shock level
        recovered_at = None
        for _,r in ts[ts["period_id"]>=13].iterrows():
            if r["avg_composite"]>=pre*.95:
                recovered_at=int(r["period_id"]); break
        rec_speed = f"{recovered_at-12} periods" if recovered_at else "Not yet recovered"

        s1,s2,s3,s4=st.columns(4)
        for col,label,val in [(s1,"Pre-Shock (P7-9)",f"{pre:.1%}"),(s2,"During Shock (P10-12)",f"{during:.1%}"),(s3,"Post-Shock (P13-17)",f"{post:.1%}"),(s4,"Recovery Speed",rec_speed)]:
            with col: st.markdown(f'<div class="gc-kpi"><div style="font-size:11px;color:#78716c">{label}</div><div style="font-size:22px;font-weight:600;color:#fafaf9">{val}</div></div>',unsafe_allow_html=True)

        st.markdown(f'<div class="gc"><div style="font-size:13px;color:#d6d3d1;line-height:1.6"><strong style="color:#fbbf24">Internal shock</strong> (20% budget drop, P10-12): Coherence dropped <strong>{drop_pct:.1f}%</strong> from pre-shock levels. Focus on reallocation — protect high-priority goals, reduce allocation to overfunded ones.<br><br><strong style="color:#f87171">External shock</strong> (P14): Requires restructuring goal bands. Recovery is {recovery_pct:.0f}% complete by P17. There\'s no single right answer — clear reasoning is key.</div></div>',unsafe_allow_html=True)

    # ── At-Risk Goals ─────────────────────────────────────────────────────
    st.markdown('<div class="sl">At-Risk Goals</div>',unsafe_allow_html=True)
    ard=comp[comp[scol]<.35].copy()
    if len(ard)>0:
        dcols=[c for c in ["goal_id","metric_name",scol]+DIMS+["scenario","weakest_dim"] if c in ard.columns]
        st.dataframe(ard[dcols].style.format(precision=3),use_container_width=True)
    else: st.markdown('<div class="gc" style="border-left:4px solid #4ade80"><span style="color:#4ade80">No goals at risk.</span></div>',unsafe_allow_html=True)

    # ── Portfolio by Department ────────────────────────────────────────────
    if port is not None:
        st.markdown('<div class="sl">Portfolio by Department</div>',unsafe_allow_html=True)
        st.dataframe(port.style.format(precision=3),use_container_width=True)

    # ── Forward Projection (client criteria) ──────────────────────────────
    if proj is not None:
        st.markdown('<div class="sl">Forward Projection</div>',unsafe_allow_html=True)
        if "improving_p6" in proj.columns:
            imp=int(proj["improving_p6"].sum()); deg=int(proj["degrading_p6"].sum()); stb=len(proj)-imp-deg
            p1,p2,p3=st.columns(3)
            for col,lb,vl,clr in [(p1,"Improving",f"{imp} goals","#4ade80"),(p2,"Stable",f"{stb} goals","#a8a29e"),(p3,"Degrading",f"{deg} goals","#f87171")]:
                with col: st.markdown(f'<div class="gc-kpi"><div style="font-size:11px;color:#78716c">{lb}</div><div style="font-size:22px;font-weight:600;color:{clr}">{vl}</div></div>',unsafe_allow_html=True)
        pcols=[c for c in ["goal_id","metric_name","composite_now","composite_p6","composite_p12","improving_p6","degrading_p6"] if c in proj.columns]
        st.dataframe(proj[pcols].style.format(precision=3),use_container_width=True)

    # ── Scenario Distribution ─────────────────────────────────────────────
    if goals is not None and "scenario_story" in goals.columns:
        st.markdown('<div class="sl">Scenario Distribution</div>',unsafe_allow_html=True)
        scc=goals["scenario_story"].value_counts()
        colors={"optimal":"#4ade80","underfunded":"#f87171","overfunded":"#fbbf24","dynamic":"#60a5fa"}
        scols=st.columns(len(scc))
        for i,(sn,cnt) in enumerate(scc.items()):
            with scols[i]: st.markdown(f'<div class="gc" style="border-left:4px solid {colors.get(sn,"#a8a29e")}"><div style="font-size:12px;color:#a8a29e">{sn}</div><div style="font-size:28px;font-weight:700;color:#fafaf9">{cnt}</div><div style="font-size:10px;color:#78716c">goals</div></div>',unsafe_allow_html=True)
