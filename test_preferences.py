#!/usr/bin/env python3
"""
Test the updated user preference logic with persistent storage
"""

import os
import json
import tempfile

# Mock the user preferences functionality


def load_user_preferences(preferences_file):
    """Load user preferences from file"""
    try:
        if os.path.exists(preferences_file):
            with open(preferences_file, 'r') as f:
                preferences = json.load(f)
                print(f"Loaded {len(preferences)} user preferences from file")
                return preferences
    except Exception as e:
        print(f"Error loading preferences: {e}")
    return {}


def save_user_preferences(preferences, preferences_file):
    """Save user preferences to file"""
    try:
        with open(preferences_file, 'w') as f:
            json.dump(preferences, f)
            print(f"Saved {len(preferences)} user preferences to file")
    except Exception as e:
        print(f"Error saving preferences: {e}")


def test_persistent_preferences():
    """Test persistent user preferences"""
    print("Testing persistent user preferences...")

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        preferences_file = f.name

    try:
        # Test 1: Load empty preferences
        print("\n--- Test 1: Load empty preferences ---")
        preferences = load_user_preferences(preferences_file)
        print(f"Initial preferences: {preferences}")

        # Test 2: Set and save a preference
        print("\n--- Test 2: Set and save preference ---")
        sender = "2348143703868"
        preferences[sender] = "ig"
        save_user_preferences(preferences, preferences_file)
        print(f"Preferences after setting: {preferences}")

        # Test 3: Load preferences from file (simulating app restart)
        print("\n--- Test 3: Load preferences after restart ---")
        new_preferences = load_user_preferences(preferences_file)
        print(f"Loaded preferences: {new_preferences}")

        # Test 4: Check if preference is maintained
        stored_preference = new_preferences.get(sender)
        print(f"Stored preference for {sender}: {stored_preference}")

        if stored_preference == "ig":
            print("✅ Preference persistence works!")
        else:
            print("❌ Preference persistence failed!")

        return stored_preference == "ig"

    finally:
        # Clean up
        try:
            os.unlink(preferences_file)
        except:
            pass


if __name__ == "__main__":
    success = test_persistent_preferences()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
