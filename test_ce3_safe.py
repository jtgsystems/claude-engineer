# Test CE3 Ollama - Windows Console Safe
import subprocess
import sys
import os

# Set environment
os.environ['PYTHONIOENCODING'] = 'utf-8'

def test_ce3_ollama():
    """Test ce3_ollama.py functionality"""
    try:
        print("Testing imports...")
        
        # Run a simple test command
        result = subprocess.run([
            sys.executable, '-c', 
            """
import sys
sys.path.insert(0, r'C:\\Users\\Owner\\Desktop\\Ai-working-on')
try:
    from config_ollama import Config
    print('Config loaded:', Config.MODEL)
    
    import ollama
    client = ollama.Client(host='http://localhost:11434')
    models = client.list()
    available = [m.model for m in models.models]
    print('Ollama connected, models:', len(available))
    
    if 'devstral:latest' in available:
        print('devstral model found')
    else:
        print('devstral not found')
        
    # Test chat
    response = client.chat(
        model='devstral:latest',
        messages=[{'role': 'user', 'content': 'Say hello'}]
    )
    print('Chat test:', response['message']['content'][:50] + '...')
    print('SUCCESS: All tests passed')
        
except Exception as e:
    print('ERROR:', str(e))
            """
        ], capture_output=True, text=True, cwd=r'C:\Users\Owner\Desktop\Ai-working-on')
        
        print("Test output:")
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
            
        return "SUCCESS" in result.stdout
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_ce3_ollama()
    print(f"\nResult: {'PASSED' if success else 'FAILED'}")
