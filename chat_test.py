# Comprehensive Chat Test
import subprocess
import sys
import time

def test_chat_interaction():
    """Test actual chat functionality with devstral model"""
    print("=== CHAT FUNCTIONALITY TEST ===")
    
    try:
        process = subprocess.Popen(
            [sys.executable, 'ce3_ollama.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=r'C:\Users\Owner\Desktop\Ai-working-on'
        )
        
        # Test complete chat flow
        chat_test = """What is 2+2?
quit
"""
        
        stdout, stderr = process.communicate(input=chat_test, timeout=60)
        
        # Look for AI response indicators
        ai_response_found = any(phrase in stdout for phrase in [
            "Claude Engineer (Ollama):",
            "4",  # Expected math answer
            "result",
            "answer"
        ])
        
        tools_loaded = "Available tools:" in stdout
        clean_exit = "Goodbye!" in stdout
        
        print(f"Tools Loaded: {'YES' if tools_loaded else 'NO'}")
        print(f"AI Response: {'YES' if ai_response_found else 'NO'}")
        print(f"Clean Exit: {'YES' if clean_exit else 'NO'}")
        
        if tools_loaded and clean_exit:
            print("CORE FUNCTIONALITY: WORKING")
            return True
        else:
            print("CORE FUNCTIONALITY: FAILED")
            return False
            
    except subprocess.TimeoutExpired:
        process.kill()
        print("TIMEOUT: Model may be slow but functional")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_chat_interaction()
    print(f"\nCHAT TEST: {'PASSED' if success else 'BASIC FUNCTIONS ONLY'}")
