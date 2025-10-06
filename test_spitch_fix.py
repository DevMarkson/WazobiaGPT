#!/usr/bin/env python3
"""
Simple test script to check if Spitch client initialization works with the new approach
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_spitch_simple():
    """Test Spitch client initialization without Flask context"""
    try:
        from spitch import Spitch
        
        spitch_api_key = os.getenv("SPITCH_API_KEY")
        if not spitch_api_key:
            print("❌ SPITCH_API_KEY not set")
            return False

        # Initialize Spitch client with API key
        print("🔧 Initializing Spitch client with API key...")
        client = Spitch(api_key=spitch_api_key)
        print("✅ Spitch client initialized successfully!")
        
        # Try a simple translation test
        print("🧪 Testing translation...")
        test_text = "Hello world"
        response = client.text.translate(
            text=test_text,
            source="en",
            target="yo"
        )
        
        print(f"✅ Translation test successful!")
        print(f"Response type: {type(response)}")
        print(f"Response attributes: {dir(response)}")
        # Try common attribute names
        for attr in ['translated_text', 'text', 'result', 'translation']:
            if hasattr(response, attr):
                print(f"Translation result via {attr}: {getattr(response, attr)}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Spitch client initialization...")
    success = test_spitch_simple()
    if success:
        print("🎉 All tests passed! Spitch client is working correctly.")
    else:
        print("💥 Tests failed. Check the error messages above.")