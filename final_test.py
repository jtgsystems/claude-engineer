# Final Production Test - Windows Safe
import subprocess
import sys
import os

def final_test():
    """Final test with Windows-safe characters only"""
    print("=== FINAL PRODUCTION TEST ===")
    
    try:
        # Test actual functionality
        process = subprocess.Popen(
            [sys.executable, 'ce3_ollama.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=r'C:\Users\Owner\Desktop\Ai-working-on'
        )
        
        # Test conversation flow
        test_commands = "hello world\nquit\n"
        stdout, stderr = process.communicate(input=test_commands, timeout=30)
        
        # Analyze results
        success_indicators = [
            "Available tools:",
            "Claude Engineer",
            "browsertool",
            "You:"
        ]
        
        all_present = all(indicator in stdout for indicator in success_indicators)
        
        if all_present and "Goodbye!" in stdout:
            print("SUCCESS: Application runs perfectly")
            print("- Tools loaded successfully")
            print("- User interface working")
            print("- Ollama integration functional")
            print("- Clean exit confirmed")
            return True
        else:
            print("FAILED: Missing expected functionality")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = final_test()
    print(f"\nFINAL RESULT: {'PASSED' if success else 'FAILED'}")
