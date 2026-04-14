"""Decidr — Goal Extractor (v4). Groq API with full bucket hierarchy context."""
import json, os, logging, re
from typing import Optional
import requests
from dotenv import load_dotenv
from schemas import BUCKET_HIERARCHY
load_dotenv()
logger = logging.getLogger(__name__)

def _hier_str():
    lines = []
    for l1, l2s in BUCKET_HIERARCHY.items():
        lines.append(f"L1: {l1}")
        for l2, l3s in l2s.items():
            lines.append(f"  L2: {l2}")
            for l3 in l3s: lines.append(f"    L3: {l3}")
    return "\n".join(lines)

PROMPT = f"""You are a goal parser for the Decidr Coherence Engine.

Organisation hierarchy:
{_hier_str()}

SCOPE: "goal" if specific function, "l2_bucket" if department-level ("all channels", "across paid"), "l1_bucket" if division ("all of marketing").

Return ONLY JSON:
{{"goal_title":"max 8 words","scope":"goal|l2_bucket|l1_bucket","bucket_l1":"","bucket_l2":"","bucket_l3":"or null","target_value":null,"initial_value":null,"metric_suggestion":"","unit_suggestion":""}}"""

class GoalExtractor:
    def __init__(self, api_key=None, model="llama-3.3-70b-versatile", use_llm=True):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.use_llm = use_llm
        if self.use_llm and not self.api_key:
            logger.warning("No GROQ_API_KEY. Falling back to heuristics.")
            self.use_llm = False

    def extract(self, nl):
        if self.use_llm:
            try: return self._llm(nl)
            except Exception as e: logger.warning(f"LLM failed: {e}")
        return self._heuristic(nl)

    def _llm(self, nl):
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"},
            json={"model":self.model,"messages":[{"role":"system","content":PROMPT},{"role":"user","content":nl}],
                  "temperature":0.1,"response_format":{"type":"json_object"}}, timeout=20)
        r.raise_for_status()
        d = json.loads(r.json()["choices"][0]["message"]["content"].strip())
        l1,l2,l3 = d.get("bucket_l1",""),d.get("bucket_l2",""),d.get("bucket_l3")
        if l1 and l1 not in BUCKET_HIERARCHY: l1=""
        if l2 and l1 and l2 not in BUCKET_HIERARCHY.get(l1,{}): l2=""
        if l3 and l1 and l2 and l3 not in BUCKET_HIERARCHY.get(l1,{}).get(l2,[]): l3=None
        scope = d.get("scope","goal")
        if scope not in ("goal","l2_bucket","l1_bucket"): scope="goal"
        if not l3 and l2 and scope=="goal": scope="l2_bucket"
        return {"goal_title":d.get("goal_title","")[:80],"scope":scope,
            "bucket_l1":l1,"bucket_l2":l2,"bucket_l3":l3,
            "target_value":d.get("target_value"),"initial_value":d.get("initial_value"),
            "metric_suggestion":d.get("metric_suggestion",""),"unit_suggestion":d.get("unit_suggestion","")}

    def _heuristic(self, nl):
        t = nl.strip()
        for sep in [".",","," by "," through "]:
            parts = nl.split(sep)
            if len(parts)>1: t=parts[0].strip(); break
        for p in ["I want to","We need to","Our goal is to","We want to"]:
            if t.lower().startswith(p.lower()): t=t[len(p):]; break
        t = " ".join(t.split()[:8])
        tl = nl.lower()
        scope = "goal"
        if any(s in tl for s in ["all channels","across","all of","entire"]): scope="l2_bucket"
        l1=l2=l3_match=""
        for l1k,l2s in BUCKET_HIERARCHY.items():
            if l1k.lower() in tl:
                l1=l1k
                for l2k,l3s in l2s.items():
                    if l2k.lower() in tl:
                        l2=l2k
                        for l3v in l3s:
                            if l3v.lower() in tl: l3_match=l3v; break
                        break
                break
        tv=iv=None
        m = re.search(r"from\s+(\d+\.?\d*)\s+to\s+(\d+\.?\d*)", tl)
        if m: iv=float(m.group(1)); tv=float(m.group(2))
        unit=""
        for u,kws in {"percentage":["%","percent","rate"],"score":["score"],"ratio":["ratio","roas"],"visitors":["visitor","traffic"],"dollars":["$","revenue"]}.items():
            if any(k in tl for k in kws): unit=u; break
        return {"goal_title":t.capitalize() if t else "","scope":scope,"bucket_l1":l1,"bucket_l2":l2,
            "bucket_l3":l3_match or None,"target_value":tv,"initial_value":iv,"metric_suggestion":"","unit_suggestion":unit}
