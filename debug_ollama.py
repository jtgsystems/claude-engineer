import ollama
import json

# Debug Ollama client response structure
client = ollama.Client(host='http://localhost:11434')

try:
    models = client.list()
    print("Raw response type:", type(models))
    print("Raw response:", json.dumps(models, indent=2, default=str))
    
    # Check structure
    if hasattr(models, 'models'):
        print("Has .models attribute")
        print("Models:", [model['name'] for model in models.models])
    elif isinstance(models, dict) and 'models' in models:
        print("Is dict with 'models' key")
        print("Models:", [model['name'] for model in models['models']])
    else:
        print("Unknown structure")
        
except Exception as e:
    print(f"Error: {e}")
