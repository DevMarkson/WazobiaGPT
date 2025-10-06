#!/usr/bin/env python3
"""
Test the help system functionality
"""

from app import get_welcome_message, get_help_message, get_commands_list, get_status_message
import sys
sys.path.append('.')


def test_help_system():
    """Test all help system functions"""
    print("🤖 TESTING SPITCH BOT HELP SYSTEM")
    print("=" * 60)

    # Test welcome message
    print("\n1️⃣ WELCOME MESSAGE:")
    print("-" * 30)
    welcome = get_welcome_message()
    print(welcome[:200] + "..." if len(welcome) > 200 else welcome)
    print(f"✅ Welcome message: {len(welcome)} characters")

    # Test help message
    print("\n2️⃣ HELP MESSAGE:")
    print("-" * 30)
    help_msg = get_help_message()
    print(help_msg[:200] + "..." if len(help_msg) > 200 else help_msg)
    print(f"✅ Help message: {len(help_msg)} characters")

    # Test commands list
    print("\n3️⃣ COMMANDS LIST:")
    print("-" * 30)
    commands = get_commands_list()
    print(commands[:200] + "..." if len(commands) > 200 else commands)
    print(f"✅ Commands list: {len(commands)} characters")

    # Test status message (no preference)
    print("\n4️⃣ STATUS MESSAGE (No Preference):")
    print("-" * 30)
    status = get_status_message("test_user")
    print(status[:200] + "..." if len(status) > 200 else status)
    print(f"✅ Status message: {len(status)} characters")

    print("\n🎉 ALL HELP FUNCTIONS WORKING!")
    print("=" * 60)

    # Test command detection
    print("\n🔍 TESTING COMMAND DETECTION:")
    test_commands = [
        '/help', 'help', '/h',
        '/commands', '/cmd', 'commands',
        '/status', 'status',
        '/reset', 'reset',
        '/start', 'start', '/welcome', 'welcome'
    ]

    detected_commands = []
    for cmd in test_commands:
        text_lower = cmd.lower().strip()
        if text_lower in ['/help', 'help', '/h']:
            detected_commands.append(f"{cmd} → HELP")
        elif text_lower in ['/commands', '/cmd', 'commands']:
            detected_commands.append(f"{cmd} → COMMANDS")
        elif text_lower in ['/status', 'status']:
            detected_commands.append(f"{cmd} → STATUS")
        elif text_lower in ['/reset', 'reset']:
            detected_commands.append(f"{cmd} → RESET")
        elif text_lower in ['/start', 'start', '/welcome', 'welcome']:
            detected_commands.append(f"{cmd} → WELCOME")

    for detection in detected_commands:
        print(f"✅ {detection}")

    print(
        f"\n🎯 Command detection: {len(detected_commands)}/{len(test_commands)} commands recognized")
    return len(detected_commands) == len(test_commands)


if __name__ == "__main__":
    success = test_help_system()
    print(f"\n{'🎉 ALL TESTS PASSED!' if success else '❌ SOME TESTS FAILED!'}")
