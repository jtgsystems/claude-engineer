# Test Claude Engineer v3 + Ollama
import subprocess
import sys
import os

def test_ce3_complete():
    """Complete test of ce3_ollama.py functionality"""
    print("=== Claude Engineer v3 + Ollama Test ===\n")
    
    # Test 1: Basic functionality
    print("Test 1: Starting ce3_ollama.py...")
    
    try:
        # Run with test input
        process = subprocess.Popen(
            [sys.executable, 'ce3_ollama.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=r'C:\Users\Owner\Desktop\Ai-working-on'
        )
        
        # Send test commands
        test_input = "hello\nquit\n"
        stdout, stderr = process.communicate(input=test_input, timeout=30)
        
        print("STDOUT:")
        print(stdout)
        
        if stderr:
            print("STDERR:")
            print(stderr)
            
        if "Available tools:" in stdout and "Claude Engineer" in stdout:
            print("✅ Test PASSED: Application loaded successfully")
            print("✅ Tools loaded successfully")
            return True
        else:
            print("❌ Test FAILED: Expected output not found")
            return False
            
    except subprocess.TimeoutExpired:
        process.kill()
        print("❌ Test FAILED: Timeout")
        return False
    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        return False

if __name__ == "__main__":
    success = test_ce3_complete()
    print(f"\nResult: {'PASSED' if success else 'FAILED'}")
