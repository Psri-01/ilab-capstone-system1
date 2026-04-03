import { useState, useCallback, useMemo } from "react";

// ── Real schema from v4 data ──────────────────────────────────────────────

const BUCKET_HIERARCHY = {
  "Marketing": {
    "Paid Acquisition": ["Google Ads - Search", "Google Ads - Display", "Social Media Ads"],
    "Content & SEO": ["Blog Content Production", "SEO Optimization", "Video Content"],
    "Partnerships": ["Partner Acquisition", "Co-Marketing Campaigns", "Channel Partnerships"],
    "Events & Community": ["Virtual Events", "In-Person Events", "Community Management"],
  },
  "Product": {
    "Core Platform": ["Backend Services", "Frontend Development", "APIs & Integrations"],
    "New Features": ["Feature Development", "A/B Testing", "Feature Launch"],
    "Technical Debt": ["Code Refactoring", "Infrastructure Upgrades"],
    "Research & Innovation": ["Proof of Concepts", "Innovation Labs"],
  },
  "Operations": {
    "Customer Success": ["Onboarding", "Support Tickets", "Account Management"],
    "Infrastructure & DevOps": ["Cloud Infrastructure", "CI/CD Pipeline"],
    "Data & Analytics": ["Data Engineering", "Analytics & Reporting"],
  },
  "G&A": {
    "Finance & Legal": ["Financial Planning", "Legal & Compliance"],
    "HR & Recruiting": ["Talent Acquisition", "Employee Development"],
    "General Admin": ["Office Operations", "Vendor Management"],
  },
};

const METRIC_UNITS = ["score", "percentage", "ratio", "count", "dollars", "visitors", "leads", "attendees", "ms", "seconds", "hours", "days", "projects"];
const SCENARIOS = ["optimal", "underfunded", "overfunded", "dynamic"];

// Mock System 2 response for demo
const MOCK_SYSTEM2_RESPONSE = {
  goal_id: 1,
  attainability: 0.6823, relevance: 0.7145, coherence: 0.5891, integrity: 0.6234,
  overall: 0.6523,
  gp_mean: 0.7012, gp_std: 0.0834, gp_weight: 0.706, llm_weight: 0.294,
  baseline: 0.6500, uncertain: false,
  reasoning: {
    attainability: "Trailing slope is positive at 0.042/period with 12 periods remaining. Current trajectory projects to 89% of target, within achievable range given allocation levels.",
    relevance: "Goal receives 5.6% of parent bucket allocation, sitting within the optimal band (5.1%-5.7%). Priority alignment is strong relative to sibling goals.",
    coherence: "L3 allocation is proportional to L2 parent share. Minor temporal drift detected in periods 8-10 but stabilised. No structural contradictions in the hierarchy.",
    integrity: "Delivered output quality score of 0.78 aligns with resource input levels. Needle movement ratio of 0.85 suggests assumptions are holding — metrics are responding to execution.",
  },
  ensemble_meta: {
    attainability: { gp_mean: 0.7012, gp_std: 0.0834, gp_weight: 0.706, llm_weight: 0.294, llm_mean: 0.6350, baseline: 0.6500, uncertain: false },
    relevance: { rule_weight: 0.528, llm_weight: 0.472, variance: 0.0021, llm_mean: 0.698, fallback: false },
    coherence: { rule_weight: 0.612, llm_weight: 0.388, variance: 0.0089, llm_mean: 0.561, fallback: false },
    integrity: { rule_weight: 0.491, llm_weight: 0.509, variance: 0.0015, llm_mean: 0.631, fallback: false },
  },
  n_llm_ok: 3, status: "ok",
};

export default function System1Revised() {
  const [view, setView] = useState("input"); // input | output
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);

  // Input state — structured fields
  const [l1, setL1] = useState("");
  const [l2, setL2] = useState("");
  const [l3, setL3] = useState("");
  const [metricName, setMetricName] = useState("");
  const [metricUnit, setMetricUnit] = useState("score");
  const [targetValue, setTargetValue] = useState("");
  const [initialValue, setInitialValue] = useState("");
  const [periods, setPeriods] = useState("24");
  const [scenario, setScenario] = useState("optimal");
  const [nlGoal, setNlGoal] = useState("");
  const [extractedGoal, setExtractedGoal] = useState("");

  // Output state
  const [scoreResult, setScoreResult] = useState(null);

  const l2Options = useMemo(() => l1 ? Object.keys(BUCKET_HIERARCHY[l1] || {}) : [], [l1]);
  const l3Options = useMemo(() => (l1 && l2) ? (BUCKET_HIERARCHY[l1]?.[l2] || []) : [], [l1, l2]);

  const extractGoal = useCallback(async () => {
    if (!nlGoal.trim()) return;
    setLoading(true);
    try {
      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          system: `Extract the core goal from the user's natural language input. Return ONLY a JSON object with no markdown or backticks:
{"goal_title": "concise goal title, max 8 words", "metric_suggestion": "suggested metric name if detectable, else empty string", "unit_suggestion": "one of: score, percentage, ratio, count, dollars, visitors, leads, attendees, ms, seconds, hours, days, projects — or empty string"}`,
          messages: [{ role: "user", content: nlGoal }],
        }),
      });
      const data = await response.json();
      const text = data.content?.map(i => i.text || "").join("") || "";
      const parsed = JSON.parse(text.replace(/```json|```/g, "").trim());
      setExtractedGoal(parsed.goal_title || "");
      if (parsed.metric_suggestion && !metricName) setMetricName(parsed.metric_suggestion);
      if (parsed.unit_suggestion && parsed.unit_suggestion !== "") setMetricUnit(parsed.unit_suggestion);
    } catch (e) {
      console.error(e);
      const words = nlGoal.split(/\s+/).slice(0, 8).join(" ");
      setExtractedGoal(words);
    }
    setLoading(false);
  }, [nlGoal, metricName]);

  const buildPayload = () => ({
    timestamp: new Date().toISOString(),
    goal: {
      goal_title: extractedGoal,
      bucket_l1: l1, bucket_l2: l2, bucket_l3: l3,
      metric_name: metricName, metric_unit: metricUnit,
      target_value: parseFloat(targetValue) || null,
      initial_value: parseFloat(initialValue) || null,
      periods: parseInt(periods) || 24,
      scenario_story: scenario,
    },
    raw_nl_input: nlGoal,
    metadata: { source: "system_1", version: "0.2.0", destination: "system_3" },
  });

  const handleConfirm = () => {
    setStep(3);
    // In production: POST to System 3 API
    // Simulate System 2 scoring after a delay
    setLoading(true);
    setTimeout(() => {
      setScoreResult(MOCK_SYSTEM2_RESPONSE);
      setLoading(false);
    }, 1500);
  };

  const reset = () => {
    setStep(1); setView("input"); setNlGoal(""); setExtractedGoal("");
    setL1(""); setL2(""); setL3(""); setMetricName(""); setMetricUnit("score");
    setTargetValue(""); setInitialValue(""); setScoreResult(null);
  };

  return (
    <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", background: "#0b1120", color: "#e2e8f0", minHeight: "100vh" }}>
      {/* Nav */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 28px", borderBottom: "1px solid rgba(148,163,184,0.08)", background: "rgba(15,23,42,0.7)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius: 7, background: "linear-gradient(135deg, #6366f1, #06b6d4)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 800, color: "#fff" }}>D</div>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9" }}>Decidr Coherence Engine</span>
          <span style={{ fontSize: 11, color: "#475569", fontWeight: 500, marginLeft: 4 }}>System 1</span>
        </div>
        <div style={{ display: "flex", gap: 2, background: "rgba(30,41,59,0.6)", borderRadius: 8, padding: 3 }}>
          {["input", "output"].map(v => (
            <button key={v} onClick={() => { if (v === "output" && scoreResult) setView("output"); else if (v === "input") setView("input"); }}
              style={{ padding: "6px 16px", borderRadius: 6, border: "none", fontSize: 12, fontWeight: 600, cursor: v === "output" && !scoreResult ? "not-allowed" : "pointer",
                background: view === v ? "rgba(99,102,241,0.2)" : "transparent",
                color: view === v ? "#a5b4fc" : "#64748b",
                opacity: v === "output" && !scoreResult ? 0.4 : 1,
              }}>{v === "input" ? "Goal Input" : "Score Output"}</button>
          ))}
        </div>
      </div>

      <div style={{ maxWidth: 680, margin: "0 auto", padding: "28px 20px" }}>

        {/* ═══ INPUT VIEW ═══ */}
        {view === "input" && (
          <>
            {/* Step 1: Structured fields + NL */}
            {step === 1 && (
              <div style={fadeIn}>
                <Badge num="01" label="Define Goal" />
                <h2 style={h2}>Set up your goal</h2>
                <p style={sub}>Select the bucket, define the metric, then describe your goal in natural language.</p>

                {/* Bucket cascade */}
                <SectionLabel text="Organisational Bucket" />
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 20 }}>
                  <Select label="L1 Division" value={l1} onChange={v => { setL1(v); setL2(""); setL3(""); }}
                    options={Object.keys(BUCKET_HIERARCHY)} />
                  <Select label="L2 Department" value={l2} onChange={v => { setL2(v); setL3(""); }}
                    options={l2Options} disabled={!l1} />
                  <Select label="L3 Function" value={l3} onChange={setL3}
                    options={l3Options} disabled={!l2} />
                </div>

                {/* Metric definition */}
                <SectionLabel text="Metric & Targets" />
                <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 10, marginBottom: 10 }}>
                  <Input label="Metric Name" value={metricName} onChange={setMetricName} placeholder="e.g. NPS Score" />
                  <Select label="Unit" value={metricUnit} onChange={setMetricUnit} options={METRIC_UNITS} />
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 10, marginBottom: 20 }}>
                  <Input label="Initial Value" value={initialValue} onChange={setInitialValue} placeholder="e.g. 60" type="number" />
                  <Input label="Target Value" value={targetValue} onChange={setTargetValue} placeholder="e.g. 85" type="number" />
                  <Input label="Periods" value={periods} onChange={setPeriods} placeholder="24" type="number" />
                  <Select label="Scenario" value={scenario} onChange={setScenario} options={SCENARIOS} />
                </div>

                {/* NL goal input — the ONE field that uses NLP extraction */}
                <SectionLabel text="Goal Description (Natural Language)" />
                <div style={{ position: "relative" }}>
                  <textarea value={nlGoal} onChange={e => setNlGoal(e.target.value)}
                    placeholder="Describe your goal in plain English. This is the only field parsed by NLP — everything above is structured input.&#10;&#10;e.g. I want to improve our NPS score from 60 to 85 over 24 months by investing in onboarding improvements and faster ticket resolution."
                    style={{ ...inputBase, minHeight: 110, resize: "vertical", paddingRight: 100 }}
                    onFocus={e => e.target.style.borderColor = "rgba(99,102,241,0.4)"}
                    onBlur={e => e.target.style.borderColor = "rgba(148,163,184,0.1)"} />
                  {nlGoal.trim() && (
                    <button onClick={extractGoal} disabled={loading}
                      style={{ position: "absolute", right: 10, bottom: 12, padding: "6px 14px", borderRadius: 6, border: "none", background: "rgba(99,102,241,0.2)", color: "#a5b4fc", fontSize: 11, fontWeight: 600, cursor: loading ? "wait" : "pointer" }}>
                      {loading ? "..." : "Extract →"}
                    </button>
                  )}
                </div>

                {extractedGoal && (
                  <div style={{ marginTop: 10, padding: "10px 14px", borderRadius: 8, background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.15)" }}>
                    <div style={{ fontSize: 10, color: "#818cf8", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>Extracted Goal Title</div>
                    <input value={extractedGoal} onChange={e => setExtractedGoal(e.target.value)}
                      style={{ ...inputBase, background: "transparent", border: "1px dashed rgba(99,102,241,0.25)", fontSize: 15, fontWeight: 600, color: "#c7d2fe" }} />
                  </div>
                )}

                <button onClick={() => setStep(2)} disabled={!extractedGoal || !l3 || !metricName}
                  style={{ ...btnPrimary, marginTop: 20, opacity: (!extractedGoal || !l3 || !metricName) ? 0.4 : 1 }}>
                  Review Before Sending →
                </button>
              </div>
            )}

            {/* Step 2: Confirmation */}
            {step === 2 && (
              <div style={fadeIn}>
                <Badge num="02" label="Confirm" />
                <h2 style={h2}>Confirm goal details</h2>
                <p style={sub}>This is what will be sent to System 3 for storage. System 2 will then score it.</p>

                <div style={{ ...cardStyle, marginTop: 20 }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#e0e7ff", marginBottom: 14 }}>{extractedGoal}</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    <KV label="Bucket" value={`${l1} → ${l2} → ${l3}`} />
                    <KV label="Metric" value={`${metricName} (${metricUnit})`} />
                    <KV label="Range" value={`${initialValue || "?"} → ${targetValue || "?"}`} />
                    <KV label="Timeline" value={`${periods} periods`} />
                    <KV label="Scenario" value={scenario} />
                    <KV label="NL Input" value={nlGoal.slice(0, 80) + (nlGoal.length > 80 ? "..." : "")} />
                  </div>
                </div>

                <details style={{ marginTop: 16 }}>
                  <summary style={{ fontSize: 12, color: "#64748b", cursor: "pointer" }}>View full JSON payload</summary>
                  <pre style={{ marginTop: 8, fontSize: 11, color: "#818cf8", lineHeight: 1.5, background: "rgba(30,41,59,0.5)", padding: 14, borderRadius: 8, overflow: "auto", maxHeight: 250 }}>
                    {JSON.stringify(buildPayload(), null, 2)}
                  </pre>
                </details>

                <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
                  <button onClick={() => setStep(1)} style={btnSecondary}>← Edit</button>
                  <button onClick={handleConfirm} style={{ ...btnPrimary, flex: 1, background: "linear-gradient(135deg, #059669, #06b6d4)" }}>
                    ✓ Send to System 3
                  </button>
                </div>
              </div>
            )}

            {/* Step 3: Sent + waiting for score */}
            {step === 3 && (
              <div style={fadeIn}>
                <Badge num="03" label="Submitted" />
                {loading ? (
                  <div style={{ textAlign: "center", padding: "48px 0" }}>
                    <div style={{ width: 48, height: 48, border: "3px solid rgba(99,102,241,0.2)", borderTopColor: "#6366f1", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 16px" }} />
                    <p style={{ ...sub, color: "#94a3b8" }}>Sent to System 3. Waiting for System 2 scores...</p>
                  </div>
                ) : (
                  <div style={{ textAlign: "center", padding: "32px 0" }}>
                    <div style={{ width: 52, height: 52, borderRadius: "50%", background: "rgba(5,150,105,0.12)", border: "2px solid rgba(5,150,105,0.3)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 14px", fontSize: 22 }}>✓</div>
                    <h2 style={{ ...h2, marginBottom: 8 }}>Goal scored</h2>
                    <p style={sub}>System 2 returned dimension scores. View the results below.</p>
                    <button onClick={() => setView("output")} style={{ ...btnPrimary, marginTop: 16, display: "inline-block", width: "auto", padding: "12px 32px" }}>
                      View Coherence Score →
                    </button>
                    <div style={{ marginTop: 12 }}>
                      <button onClick={reset} style={{ ...btnSecondary, display: "inline-block", width: "auto" }}>+ New Goal</button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* ═══ OUTPUT VIEW — Confidence-hedged score presentation ═══ */}
        {view === "output" && scoreResult && (
          <div style={fadeIn}>
            <Badge num="—" label="Coherence Report" />
            <h2 style={h2}>{extractedGoal}</h2>
            <p style={sub}>{l1} → {l2} → {l3} · {metricName} · {scenario}</p>

            {/* Composite score hero */}
            <div style={{ textAlign: "center", padding: "28px 0 20px" }}>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#64748b", fontWeight: 600, marginBottom: 6 }}>Composite Coherence</div>
              <div style={{ fontSize: 56, fontWeight: 800, letterSpacing: "-0.04em",
                color: scoreResult.overall >= 0.65 ? "#4ade80" : scoreResult.overall >= 0.35 ? "#fbbf24" : "#f87171",
              }}>{(scoreResult.overall * 100).toFixed(1)}%</div>
              <ConfidenceBadge uncertain={scoreResult.uncertain} gpStd={scoreResult.gp_std} />
            </div>

            {/* 4 dimension cards */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 8 }}>
              {["coherence", "attainability", "relevance", "integrity"].map(dim => {
                const score = scoreResult[dim];
                const weight = { coherence: 35, attainability: 25, relevance: 20, integrity: 20 }[dim];
                const defs = {
                  coherence: "Are decisions consistent across levels?",
                  attainability: "Is the goal realistically achievable?",
                  relevance: "Is the allocation justified?",
                  integrity: "Are assumptions transparent & robust?",
                };
                return (
                  <div key={dim} style={{ ...cardStyle, padding: "16px 18px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: "#e0e7ff", textTransform: "capitalize" }}>{dim}</div>
                      <div style={{ fontSize: 10, color: "#475569" }}>{weight}% weight</div>
                    </div>
                    <div style={{ fontSize: 11, color: "#64748b", marginTop: 2, marginBottom: 10 }}>{defs[dim]}</div>
                    <ScoreBar score={score} />
                    <div style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.5, marginTop: 10 }}>
                      {scoreResult.reasoning[dim]}
                    </div>
                    {/* Ensemble metadata */}
                    <div style={{ marginTop: 8, fontSize: 10, color: "#475569", display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {dim === "attainability" ? (
                        <>
                          <Tag text={`GP: ${(scoreResult.ensemble_meta.attainability.gp_weight * 100).toFixed(0)}%`} />
                          <Tag text={`LLM: ${(scoreResult.ensemble_meta.attainability.llm_weight * 100).toFixed(0)}%`} />
                          <Tag text={`σ = ${scoreResult.gp_std.toFixed(3)}`} />
                        </>
                      ) : (
                        scoreResult.ensemble_meta[dim] && <>
                          <Tag text={`Rule: ${(scoreResult.ensemble_meta[dim].rule_weight * 100).toFixed(0)}%`} />
                          <Tag text={`LLM: ${(scoreResult.ensemble_meta[dim].llm_weight * 100).toFixed(0)}%`} />
                          <Tag text={`var: ${scoreResult.ensemble_meta[dim].variance?.toFixed(4)}`} />
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Confidence section */}
            <div style={{ ...cardStyle, marginTop: 14, background: scoreResult.uncertain ? "rgba(251,191,36,0.04)" : "rgba(74,222,128,0.04)", borderColor: scoreResult.uncertain ? "rgba(251,191,36,0.15)" : "rgba(74,222,128,0.1)" }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#e0e7ff", marginBottom: 8 }}>Confidence Assessment</div>
              <div style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.6 }}>
                {scoreResult.uncertain
                  ? `⚠ GP uncertainty is elevated (σ = ${scoreResult.gp_std.toFixed(4)}). The attainability score has wider error bounds — treat it as directional rather than precise. The composite score has been penalised by 10% to reflect this uncertainty.`
                  : `GP uncertainty is within normal bounds (σ = ${scoreResult.gp_std.toFixed(4)}). The Gaussian Process model is confident in its attainability estimate. ${scoreResult.n_llm_ok}/3 LLM models returned valid scores, providing good ensemble coverage.`
                }
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
                <Tag text={`Baseline: ${(scoreResult.baseline * 100).toFixed(1)}%`} />
                <Tag text={`GP mean: ${(scoreResult.gp_mean * 100).toFixed(1)}%`} />
                <Tag text={`GP weight: ${(scoreResult.gp_weight * 100).toFixed(0)}%`} />
                <Tag text={`LLMs OK: ${scoreResult.n_llm_ok}/3`} />
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
              <button onClick={() => setView("input")} style={btnSecondary}>← Back to Input</button>
              <button onClick={reset} style={{ ...btnSecondary, flex: 1 }}>+ New Goal</button>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes spin { to { transform: rotate(360deg); } }
        select { appearance: auto; }
        details summary { list-style: none; } details summary::-webkit-details-marker { display: none; }
        textarea::-webkit-scrollbar { width: 5px; } textarea::-webkit-scrollbar-thumb { background: rgba(100,116,139,0.25); border-radius: 3px; }
      `}</style>
    </div>
  );
}

// ── Components ────────────────────────────────────────────────────────────

function Badge({ num, label }) {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 7, padding: "4px 11px 4px 7px", borderRadius: 6, background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.12)", marginBottom: 14 }}>
      <span style={{ fontSize: 11, fontWeight: 700, color: "#6366f1", fontFamily: "'JetBrains Mono', monospace" }}>STEP {num}</span>
      <span style={{ fontSize: 11, color: "#64748b", fontWeight: 500 }}>{label}</span>
    </div>
  );
}

function SectionLabel({ text }) {
  return <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8, marginTop: 20 }}>{text}</div>;
}

function Input({ label, value, onChange, placeholder, type = "text" }) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        style={inputBase}
        onFocus={e => e.target.style.borderColor = "rgba(99,102,241,0.4)"}
        onBlur={e => e.target.style.borderColor = "rgba(148,163,184,0.1)"} />
    </div>
  );
}

function Select({ label, value, onChange, options, disabled }) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <select value={value} onChange={e => onChange(e.target.value)} disabled={disabled}
        style={{ ...inputBase, cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.4 : 1 }}>
        <option value="">—</option>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}

function KV({ label, value }) {
  return (
    <div style={{ padding: "8px 10px", background: "rgba(15,23,42,0.4)", borderRadius: 6 }}>
      <div style={{ fontSize: 10, color: "#475569", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</div>
      <div style={{ fontSize: 13, color: "#cbd5e1", marginTop: 2 }}>{value}</div>
    </div>
  );
}

function ScoreBar({ score }) {
  const pct = (score * 100).toFixed(1);
  const color = score >= 0.65 ? "#4ade80" : score >= 0.35 ? "#fbbf24" : "#f87171";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ flex: 1, height: 6, background: "rgba(30,41,59,0.8)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 3, transition: "width 0.6s ease" }} />
      </div>
      <div style={{ fontSize: 15, fontWeight: 700, color, fontFamily: "'JetBrains Mono', monospace", minWidth: 48, textAlign: "right" }}>{pct}%</div>
    </div>
  );
}

function ConfidenceBadge({ uncertain, gpStd }) {
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 5, padding: "4px 12px", borderRadius: 20, marginTop: 6, fontSize: 11, fontWeight: 600,
      background: uncertain ? "rgba(251,191,36,0.1)" : "rgba(74,222,128,0.08)",
      color: uncertain ? "#fbbf24" : "#4ade80",
      border: `1px solid ${uncertain ? "rgba(251,191,36,0.2)" : "rgba(74,222,128,0.15)"}`,
    }}>
      {uncertain ? "⚠ Elevated Uncertainty" : "✓ High Confidence"} · σ = {gpStd.toFixed(4)}
    </div>
  );
}

function Tag({ text }) {
  return (
    <span style={{ padding: "2px 8px", borderRadius: 4, background: "rgba(30,41,59,0.6)", border: "1px solid rgba(148,163,184,0.08)", fontSize: 10, color: "#64748b", fontFamily: "'JetBrains Mono', monospace" }}>
      {text}
    </span>
  );
}

// ── Shared Styles ─────────────────────────────────────────────────────────

const fadeIn = { animation: "fadeIn 0.35s ease" };
const h2 = { fontSize: 22, fontWeight: 800, color: "#f1f5f9", letterSpacing: "-0.02em", marginBottom: 4, lineHeight: 1.2 };
const sub = { fontSize: 13, color: "#64748b", lineHeight: 1.5, marginBottom: 0 };
const labelStyle = { display: "block", fontSize: 11, fontWeight: 600, color: "#94a3b8", marginBottom: 5 };
const inputBase = { width: "100%", padding: "9px 12px", background: "rgba(30,41,59,0.6)", border: "1px solid rgba(148,163,184,0.1)", borderRadius: 7, color: "#e2e8f0", fontSize: 13, fontFamily: "inherit", outline: "none", boxSizing: "border-box", transition: "border-color 0.2s" };
const cardStyle = { padding: "18px 20px", borderRadius: 10, background: "rgba(30,41,59,0.45)", border: "1px solid rgba(148,163,184,0.07)" };
const btnPrimary = { display: "block", width: "100%", padding: "12px 20px", background: "linear-gradient(135deg, #6366f1, #06b6d4)", color: "#fff", border: "none", borderRadius: 9, fontSize: 13, fontWeight: 700, cursor: "pointer", fontFamily: "inherit" };
const btnSecondary = { padding: "12px 18px", background: "rgba(30,41,59,0.6)", color: "#94a3b8", border: "1px solid rgba(148,163,184,0.1)", borderRadius: 9, fontSize: 13, fontWeight: 500, cursor: "pointer", fontFamily: "inherit" };
