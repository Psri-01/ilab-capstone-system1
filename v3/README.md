# Decidr Coherence Engine - System 1 Setup Guide

## Overview
This is the System 1 interface for the Decidr Coherence Engine, now using Groq API for goal title extraction instead of local Ollama.

## Prerequisites
- Python 3.8 or higher
- Groq API key (get one at https://console.groq.com)

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:
```
GROQ_API_KEY=gsk_your_actual_api_key_here
```

### 3. Verify Required Files
Ensure you have these files in your project directory:
- `app.py` - Main Streamlit application
- `goal_extractor.py` - Goal extraction logic with Groq API
- `schemas.py` - Data models and validation (must be present)
- `.env` - Environment configuration with your API key
- `requirements.txt` - Python dependencies

### 4. Run the Application
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## How It Works

### Input Flow
1. **Structured Form**: Select organizational bucket (L1/L2/L3), define metric, targets, and scenario
2. **NL Goal Description**: Describe your goal in natural language
3. **Extract Goal Title**: Click "Extract Goal Title" to use Groq API for NLP extraction
4. **Confirm & Send**: Review and send to System 3

### Groq API Integration
- Model: `llama-3.3-70b-versatile` (default, configurable)
- Response format: JSON with structured output
- Fallback: If API fails, uses heuristic extraction
- Extracted fields: goal_title, metric_suggestion, unit_suggestion

### Output Flow
- Upload System 2 score JSON or use demo data
- View coherence scores across four dimensions
- Download full score report

## Troubleshooting

### API Key Not Found
If you see "No Groq API key found" warnings:
1. Verify `.env` file exists in the project root
2. Check the API key format: `GROQ_API_KEY=gsk_...`
3. Restart the Streamlit app after editing `.env`

### Import Error: schemas module
The app requires a `schemas.py` file with these classes:
- `GoalInput`
- `System3Payload`
- `System2ScoreResponse`
- Constants: `BUCKET_HIERARCHY`, `METRIC_UNITS`, `SCENARIOS`, `DIMENSIONS`, `DIMENSION_WEIGHTS`
- Helper functions: `hedged_summary()`, `risk_flag()`, `confidence_label()`

### Groq API Rate Limits
- Free tier: 30 requests/minute
- If rate limited, the app falls back to heuristic extraction
- Consider upgrading for production use

## Configuration Options

### Change Groq Model
In `goal_extractor.py`, modify the default model:
```python
GoalExtractor(model="llama-3.2-90b-text-preview")
```

Or set in `.env`:
```
GROQ_MODEL=llama-3.2-90b-text-preview
```

### Disable LLM Extraction
In `app.py`, change:
```python
return GoalExtractor(use_llm=False)
```

This uses pure heuristic extraction without API calls.

## File Structure
```
decidr-system1/
├── app.py                    # Main Streamlit application
├── goal_extractor.py         # Groq API integration
├── schemas.py                # Data models (not included, must be present)
├── .env                      # Environment variables (create from .env.example)
├── .env.example              # Template for environment variables
├── requirements.txt          # Python dependencies
├── outputs/                  # Generated goal JSON files (created automatically)
└── README.md                 # This file
```

## Next Steps
1. Ensure `schemas.py` is in the project directory
2. Get a Groq API key from https://console.groq.com
3. Configure `.env` with your API key
4. Run `streamlit run app.py`
5. Test goal extraction with sample inputs

## Support
For issues with the Decidr Coherence Engine, contact the project team.
For Groq API issues, see https://console.groq.com/docs
