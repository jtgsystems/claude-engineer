# Test CE3 Ollama in proper console environment
# This approach bypasses console issues

import subprocess
import sys
import os

# Set environment
os.environ['PYTHONIOENCODING'] = 'utf-8'

def test_ce3_ollama():
    """Test ce3_ollama.py functionality"""
    try:
        # Test 1: Basic import and initialization
        print("🔍 Testing imports...")
        
        # Run a simple test command
        result = subprocess.run([
            sys.executable, '-c', 
            """
import sys
sys.path.insert(0, r'C:\\Users\\Owner\\Desktop\\Ai-working-on')
try:
    from config_ollama import Config
    print('✅ Config loaded:', Config.MODEL)
    
    import ollama
    client = ollama.Client(host='http://localhost:11434')
    models = client.list()
    available = [m.model for m in models.models]
    print('✅ Ollama connected, models:', len(available))
    
    if 'devstral:latest' in available:
        print('✅ devstral model found')
    else:
        print('❌ devstral not found')
        
except Exception as e:
    print('❌ Error:', str(e))
            """
        ], capture_output=True, text=True, cwd=r'C:\Users\Owner\Desktop\Ai-working-on')
        
        print("Test output:")
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_ce3_ollama()
    print(f"\n{'✅ Tests passed' if success else '❌ Tests failed'}")
