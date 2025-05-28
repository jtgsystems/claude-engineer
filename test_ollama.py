import ollama

# Test basic connection and model interaction
client = ollama.Client(host='http://localhost:11434')

try:
    print("Testing devstral model...")
    response = client.chat(
        model='devstral:latest',
        messages=[{'role': 'user', 'content': 'Hello, respond with just "Connection successful!"'}]
    )
    print("Response:", response['message']['content'])
    print("Test successful!")
except Exception as e:
    print(f"Error: {e}")
