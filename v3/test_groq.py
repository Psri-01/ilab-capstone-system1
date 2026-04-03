#!/usr/bin/env python3
"""
Test script for Groq API integration in Goal Extractor
Run this to verify your API key and connection are working.
"""

import os
from dotenv import load_dotenv
from goal_extractor import GoalExtractor

def test_extractor():
    """Test the goal extractor with sample inputs."""
    
    # Load environment variables
    load_dotenv()
    
    # Check if API key is set
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not found in environment")
        print("Please create a .env file with your API key")
        return False
    
    print(f"✓ API key found: {api_key[:20]}...")
    
    # Test cases
    test_inputs = [
        "I want to improve our NPS score from 60 to 85 over 24 months",
        "Increase website traffic by 40% through SEO improvements",
        "Reduce customer churn rate from 8% to 3% in Q3",
        "We need to cut operational costs by $2M this year",
    ]
    
    # Initialize extractor with LLM enabled
    extractor = GoalExtractor(use_llm=True)
    
    print("\nTesting Groq API with sample inputs...\n")
    
    for i, nl_input in enumerate(test_inputs, 1):
        print(f"Test {i}: {nl_input}")
        try:
            result = extractor.extract(nl_input)
            print(f"  ✓ Goal Title: {result['goal_title']}")
            if result['metric_suggestion']:
                print(f"    Metric: {result['metric_suggestion']}")
            if result['unit_suggestion']:
                print(f"    Unit: {result['unit_suggestion']}")
            print()
        except Exception as e:
            print(f"  ❌ Error: {e}")
            print()
            return False
    
    print("✓ All tests passed! Groq API integration is working correctly.")
    return True

def test_fallback():
    """Test heuristic fallback when LLM is disabled."""
    print("\nTesting heuristic fallback (LLM disabled)...\n")
    
    extractor = GoalExtractor(use_llm=False)
    nl_input = "I want to improve our NPS score from 60 to 85"
    
    result = extractor.extract(nl_input)
    print(f"Input: {nl_input}")
    print(f"  ✓ Goal Title: {result['goal_title']}")
    print(f"  ✓ Unit: {result['unit_suggestion']}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("Decidr System 1 - Groq API Integration Test")
    print("=" * 60)
    print()
    
    # Test API integration
    api_ok = test_extractor()
    
    # Test fallback
    test_fallback()
    
    if api_ok:
        print("\n" + "=" * 60)
        print("✓ Setup complete! You can now run:")
        print("  streamlit run app.py")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠ Please fix the issues above before running the app")
        print("=" * 60)
