# Decidr Coherence Engine — System 1 (v4)

## Setup
```bash
pip install -r requirements.txt
# Edit .env and .streamlit/secrets.toml with your Groq API key
streamlit run app.py
```

## Structure
```
v4/
├── app.py                  ← Entry point (input + portfolio dashboard)
├── goal_extractor.py       ← NL parsing via Groq API
├── schemas.py              ← Data models
├── pages/dashboard.py      ← Subhan's output dashboard
├── data/                   ← System 2 output CSVs (pre-generated)
├── .streamlit/secrets.toml ← Groq key for dashboard
├── .env                    ← Groq key for extractor
└── outputs/                ← Saved goal JSONs
```

## Client Success Criteria (all implemented in Portfolio Dashboard)
- Portfolio coherence score across all 4 dimensions
- Goal retention rate vs 86-88% benchmark
- Shock analysis (internal budget cut + external market shock)
- Recovery speed (periods to stabilise)
- Forward projection (+6/+12 periods)
