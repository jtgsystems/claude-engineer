# Simple test runner that works in Windows environment
import os
import sys

# Set environment variables for Windows console
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '1'

if __name__ == "__main__":
    print("Testing simple console input...")
    try:
        user_input = input("Enter test message: ")
        print(f"You entered: {user_input}")
    except Exception as e:
        print(f"Input error: {e}")
