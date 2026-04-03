"""
Decidr Coherence Engine — System 1 Streamlit App (v2)

Revised scope per client + lead feedback:
  INPUT:  Structured form fields (bucket, metric, target, scenario)
          + NL textbox → extract goal title only via NLP
          → user confirms → JSON to System 3

  OUTPUT: Present System 2 score payload with confidence hedging
          Uses reasoning strings from System 2 (no re-calling LLMs)

Run:  streamlit run app.py
"""

import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from schemas import (
    GoalInput, System3Payload, System2ScoreResponse,
    BUCKET_HIERARCHY, METRIC_UNITS, SCENARIOS, DIMENSIONS,
    DIMENSION_WEIGHTS, hedged_summary, risk_flag, confidence_label,
)
from goal_extractor import GoalExtractor


# ── Page Config ────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Decidr · System 1",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .step-badge { display:inline-block; padding:4px 12px; border-radius:6px;
        background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.2);
        font-size:12px; font-weight:600; color:#6366f1; margin-bottom:8px; }
    .dim-card { background:#f8fafc; padding:16px; border-radius:10px;
        border:1px solid #e2e8f0; margin-bottom:8px; }
</style>
""", unsafe_allow_html=True)


# ── Session State ──────────────────────────────────────────────────────────

defaults = {
    "page": "input",  # input | output
    "step": 1,        # 1=form, 2=confirm, 3=sent
    "nl_input": "",
    "extracted_goal": "",
    "l1": "", "l2": "", "l3": "",
    "metric_name": "", "metric_unit": "score",
    "target_value": "", "initial_value": "",
    "periods": 24, "scenario": "optimal",
    "payload_json": None,
    "score_result": None,
    "history": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Parser ─────────────────────────────────────────────────────────────────

@st.cache_resource
def get_extractor():
    return GoalExtractor(use_llm=True)  # flip True when Ollama available

extractor = get_extractor()

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Sidebar nav ────────────────────────────────────────────────────────────

page = st.sidebar.radio(
    "View", ["🎯 Goal Input", "📊 Score Output"],
    index=0 if st.session_state.page == "input" else 1,
)
st.session_state.page = "input" if "Input" in page else "output"


# ═══════════════════════════════════════════════════════════════════════════
# INPUT PAGE
# ═══════════════════════════════════════════════════════════════════════════

if st.session_state.page == "input":

    step = st.session_state.step

    # Progress
    cols = st.columns(3)
    for i, (c, lab) in enumerate(zip(cols, ["Define", "Confirm", "Sent"]), 1):
        with c:
            st.progress(1.0 if i <= step else 0.0)
            st.caption(f"**{i}.** {lab}")
    st.divider()

    # ── STEP 1: Structured Form + NL Goal ──────────────────────────────────

    if step == 1:
        st.markdown('<div class="step-badge">STEP 01 · Define Goal</div>', unsafe_allow_html=True)
        st.header("Set up your goal")
        st.caption("Select bucket, define metric, then describe your goal in natural language.")

        # Bucket cascade
        st.subheader("Organisational Bucket")
        c1, c2, c3 = st.columns(3)
        with c1:
            l1_options = list(BUCKET_HIERARCHY.keys())
            l1 = st.selectbox("L1 Division", [""] + l1_options,
                              index=(l1_options.index(st.session_state.l1) + 1) if st.session_state.l1 in l1_options else 0)
            st.session_state.l1 = l1
        with c2:
            l2_options = list(BUCKET_HIERARCHY.get(l1, {}).keys()) if l1 else []
            if st.session_state.l2 not in l2_options:
                st.session_state.l2 = ""
            l2 = st.selectbox("L2 Department", [""] + l2_options,
                              index=(l2_options.index(st.session_state.l2) + 1) if st.session_state.l2 in l2_options else 0)
            st.session_state.l2 = l2
        with c3:
            l3_options = BUCKET_HIERARCHY.get(l1, {}).get(l2, []) if l1 and l2 else []
            if st.session_state.l3 not in l3_options:
                st.session_state.l3 = ""
            l3 = st.selectbox("L3 Function", [""] + l3_options,
                              index=(l3_options.index(st.session_state.l3) + 1) if st.session_state.l3 in l3_options else 0)
            st.session_state.l3 = l3

        # Metric & targets
        st.subheader("Metric & Targets")
        mc1, mc2 = st.columns([2, 1])
        with mc1:
            st.session_state.metric_name = st.text_input(
                "Metric Name", value=st.session_state.metric_name,
                placeholder="e.g. NPS Score, Organic Traffic")
        with mc2:
            unit_idx = METRIC_UNITS.index(st.session_state.metric_unit) if st.session_state.metric_unit in METRIC_UNITS else 0
            st.session_state.metric_unit = st.selectbox("Unit", METRIC_UNITS, index=unit_idx)

        tc1, tc2, tc3, tc4 = st.columns(4)
        with tc1:
            st.session_state.initial_value = st.text_input("Initial Value", value=st.session_state.initial_value, placeholder="e.g. 60")
        with tc2:
            st.session_state.target_value = st.text_input("Target Value", value=st.session_state.target_value, placeholder="e.g. 85")
        with tc3:
            st.session_state.periods = st.number_input("Periods", value=st.session_state.periods, min_value=1, max_value=48)
        with tc4:
            sc_idx = SCENARIOS.index(st.session_state.scenario) if st.session_state.scenario in SCENARIOS else 0
            st.session_state.scenario = st.selectbox("Scenario", SCENARIOS, index=sc_idx)

        # NL goal input — THE ONLY NLP FIELD
        st.subheader("Goal Description (Natural Language)")
        st.caption("This is the only field parsed by NLP — we extract the goal title from your description.")

        st.session_state.nl_input = st.text_area(
            "Describe your goal",
            value=st.session_state.nl_input,
            height=120,
            placeholder="e.g. I want to improve our NPS score from 60 to 85 over 24 months by investing in onboarding and faster ticket resolution.",
        )

        if st.button("🔍 Extract Goal Title", disabled=not st.session_state.nl_input.strip()):
            with st.spinner("Extracting goal..."):
                result = extractor.extract(st.session_state.nl_input)
                st.session_state.extracted_goal = result["goal_title"]
                if result["metric_suggestion"] and not st.session_state.metric_name:
                    st.session_state.metric_name = result["metric_suggestion"]
                if result["unit_suggestion"]:
                    st.session_state.metric_unit = result["unit_suggestion"]
                st.rerun()

        if st.session_state.extracted_goal:
            st.session_state.extracted_goal = st.text_input(
                "✅ Extracted Goal Title (editable)",
                value=st.session_state.extracted_goal,
            )

        # Validate and proceed
        ready = all([st.session_state.extracted_goal, st.session_state.l3, st.session_state.metric_name])
        if st.button("Review Before Sending →", type="primary", use_container_width=True, disabled=not ready):
            st.session_state.step = 2
            st.rerun()

        if not ready:
            missing = []
            if not st.session_state.extracted_goal: missing.append("goal title (extract from NL)")
            if not st.session_state.l3: missing.append("L3 bucket")
            if not st.session_state.metric_name: missing.append("metric name")
            if missing:
                st.info(f"Still needed: {', '.join(missing)}")

    # ── STEP 2: Confirm ────────────────────────────────────────────────────

    elif step == 2:
        st.markdown('<div class="step-badge">STEP 02 · Confirm</div>', unsafe_allow_html=True)
        st.header("Confirm goal details")
        st.caption("This is what will be sent to System 3. System 2 will then score it.")

        st.subheader(st.session_state.extracted_goal)

        c1, c2 = st.columns(2)
        c1.metric("Bucket Path", f"{st.session_state.l1} → {st.session_state.l2} → {st.session_state.l3}")
        c2.metric("Metric", f"{st.session_state.metric_name} ({st.session_state.metric_unit})")

        c3, c4, c5 = st.columns(3)
        c3.metric("Range", f"{st.session_state.initial_value or '?'} → {st.session_state.target_value or '?'}")
        c4.metric("Periods", st.session_state.periods)
        c5.metric("Scenario", st.session_state.scenario)

        # Build payload
        goal = GoalInput(
            goal_title=st.session_state.extracted_goal,
            bucket_l1=st.session_state.l1,
            bucket_l2=st.session_state.l2,
            bucket_l3=st.session_state.l3,
            metric_name=st.session_state.metric_name,
            metric_unit=st.session_state.metric_unit,
            target_value=float(st.session_state.target_value) if st.session_state.target_value else None,
            initial_value=float(st.session_state.initial_value) if st.session_state.initial_value else None,
            periods=st.session_state.periods,
            scenario_story=st.session_state.scenario,
        )
        payload = System3Payload(goal=goal, raw_nl_input=st.session_state.nl_input)

        with st.expander("View full JSON payload"):
            st.json(json.loads(payload.to_json()))

        bc1, bc2 = st.columns([1, 3])
        with bc1:
            if st.button("← Edit"):
                st.session_state.step = 1
                st.rerun()
        with bc2:
            if st.button("✓ Send to System 3", type="primary", use_container_width=True):
                # Save locally
                ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                fpath = OUTPUT_DIR / f"goal_{ts}.json"
                fpath.write_text(payload.to_json())
                st.session_state.payload_json = payload.to_json()
                st.session_state.history.append({
                    "file": str(fpath),
                    "title": st.session_state.extracted_goal,
                    "time": ts,
                })
                st.session_state.step = 3
                st.rerun()

    # ── STEP 3: Sent ──────────────────────────────────────────────────────

    elif step == 3:
        st.markdown('<div class="step-badge">STEP 03 · Submitted</div>', unsafe_allow_html=True)
        st.success(f"✓ Goal **{st.session_state.extracted_goal}** sent to System 3.")
        st.caption("In production, System 3 stores this and triggers System 2 scoring.")

        st.download_button(
            "⬇ Download JSON",
            data=st.session_state.payload_json,
            file_name=f"goal_{st.session_state.extracted_goal.replace(' ', '_')}.json",
            mime="application/json",
            use_container_width=True,
        )

        if st.button("+ New Goal", use_container_width=True):
            for k in ["nl_input", "extracted_goal", "l1", "l2", "l3",
                       "metric_name", "target_value", "initial_value"]:
                st.session_state[k] = ""
            st.session_state.metric_unit = "score"
            st.session_state.step = 1
            st.rerun()

        if len(st.session_state.history) > 1:
            st.divider()
            st.subheader(f"Session Goals ({len(st.session_state.history)})")
            for i, h in enumerate(st.session_state.history):
                st.caption(f"**{i+1}.** {h['title']} · `{h['file']}`")


# ═══════════════════════════════════════════════════════════════════════════
# OUTPUT PAGE — Confidence-hedged score presentation
# ═══════════════════════════════════════════════════════════════════════════

elif st.session_state.page == "output":

    st.markdown('<div class="step-badge">SCORE OUTPUT</div>', unsafe_allow_html=True)
    st.header("Coherence Score Report")

    # Load a score result (in production: fetched from System 3)
    uploaded = st.file_uploader("Upload System 2 score JSON", type="json")

    if uploaded:
        try:
            data = json.loads(uploaded.read())
            score = System2ScoreResponse(**data)
            st.session_state.score_result = score
        except Exception as e:
            st.error(f"Invalid score JSON: {e}")

    # Demo mode
    if not st.session_state.score_result:
        st.info("No score loaded. Upload a System 2 JSON result, or use demo data.")
        if st.button("Load Demo Score"):
            demo = {
                "goal_id": 1,
                "attainability": 0.6823, "relevance": 0.7145,
                "coherence": 0.5891, "integrity": 0.6234,
                "overall": 0.6523,
                "gp_mean": 0.7012, "gp_std": 0.0834,
                "gp_weight": 0.706, "llm_weight": 0.294,
                "baseline": 0.6500, "uncertain": False,
                "reasoning": {
                    "attainability": "Trailing slope is positive at 0.042/period. Current trajectory projects to 89% of target within achievable range.",
                    "relevance": "Goal receives 5.6% of parent allocation, within optimal band. Priority alignment is strong relative to siblings.",
                    "coherence": "L3 allocation proportional to L2 parent. Minor temporal drift in periods 8-10 but stabilised. No structural contradictions.",
                    "integrity": "Output quality score 0.78 aligns with inputs. Needle movement ratio 0.85 suggests assumptions are holding.",
                },
                "ensemble_meta": {
                    "attainability": {"gp_mean": 0.7012, "gp_std": 0.0834, "gp_weight": 0.706, "llm_weight": 0.294, "llm_mean": 0.635, "baseline": 0.65, "uncertain": False},
                    "relevance": {"rule_weight": 0.528, "llm_weight": 0.472, "variance": 0.0021},
                    "coherence": {"rule_weight": 0.612, "llm_weight": 0.388, "variance": 0.0089},
                    "integrity": {"rule_weight": 0.491, "llm_weight": 0.509, "variance": 0.0015},
                },
                "n_llm_ok": 3, "status": "ok",
            }
            st.session_state.score_result = System2ScoreResponse(**demo)
            st.rerun()

    score = st.session_state.score_result
    if score:
        # NL summary with confidence hedging
        st.info(hedged_summary(score))

        # Composite hero
        risk = risk_flag(score.overall)
        color = {"on_track": "🟢", "at_risk": "🟡", "critical": "🔴"}[risk]
        st.metric(
            f"{color} Composite Coherence",
            f"{score.overall:.1%}",
            delta=confidence_label(score),
        )

        # Dimension scores
        st.subheader("Dimension Breakdown")
        dim_defs = {
            "coherence": "Are decisions consistent across levels, goals, and time?",
            "attainability": "Is the goal realistically achievable given constraints?",
            "relevance": "Is the allocation justified against stated goals?",
            "integrity": "Are assumptions transparent, robust, and auditable?",
        }

        for dim in DIMENSIONS:
            val = getattr(score, dim)
            weight = DIMENSION_WEIGHTS[dim]
            reasoning = score.reasoning.get(dim, "")
            meta = score.ensemble_meta.get(dim, {})

            with st.container():
                st.markdown(f'<div class="dim-card">', unsafe_allow_html=True)
                dc1, dc2 = st.columns([3, 1])
                with dc1:
                    st.markdown(f"**{dim.capitalize()}** ({weight:.0%} weight)")
                    st.caption(dim_defs.get(dim, ""))
                with dc2:
                    dim_color = "🟢" if val >= 0.65 else "🟡" if val >= 0.35 else "🔴"
                    st.metric(dim_color, f"{val:.1%}")

                st.progress(val)
                if reasoning:
                    st.write(reasoning)

                # Ensemble metadata
                meta_parts = []
                if "gp_weight" in meta:
                    meta_parts.append(f"GP: {meta['gp_weight']:.0%}")
                if "rule_weight" in meta:
                    meta_parts.append(f"Rule: {meta['rule_weight']:.1%}")
                if "llm_weight" in meta:
                    meta_parts.append(f"LLM: {meta['llm_weight']:.1%}")
                if "variance" in meta:
                    meta_parts.append(f"var: {meta['variance']:.4f}")
                if meta_parts:
                    st.caption(" · ".join(meta_parts))

                st.markdown('</div>', unsafe_allow_html=True)

        # Download full report
        st.divider()
        st.download_button(
            "⬇ Download Full Score JSON",
            data=score.model_dump_json(indent=2),
            file_name=f"coherence_score_goal_{score.goal_id}.json",
            mime="application/json",
            use_container_width=True,
        )
