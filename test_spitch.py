#!/usr/bin/env python3
"""
Test script to verify Spitch API functionality
Run this locally and on Railway to compare results
"""

import os
from dotenv import load_dotenv
from spitch import Spitch

def test_spitch_api():
    print("Testing Spitch API...")
    
    # Load environment variables
    load_dotenv()
    
    # Check if API key is available
    api_key = os.getenv("SPITCH_API_KEY")
    if not api_key:
        print("❌ SPITCH_API_KEY not found in environment variables")
        return False
    
    print(f"✅ SPITCH_API_KEY found: {api_key[:10]}...")
    
    try:
        # Initialize Spitch client
        os.environ["SPITCH_API_KEY"] = api_key
        client = Spitch()
        print("✅ Spitch client initialized successfully")
        
        # Test translation
        test_text = "Bawo ni"  # "How are you" in Yoruba
        print(f"Testing translation: '{test_text}' (Yoruba -> English)")
        
        response = client.text.translate(
            text=test_text,
            source="yo",
            target="en"
        )
        
        translation = response.text.strip()
        print(f"✅ Translation successful: '{translation}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Translation failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_spitch_api()
    exit_code = 0 if success else 1
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    exit(exit_code)