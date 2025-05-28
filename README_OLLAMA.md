# Claude Engineer v3 - Ollama Integration Setup

## Setup Instructions

### Prerequisites
1. **Ollama Installation**: Install Ollama from https://ollama.ai
2. **devstral Model**: Install the devstral model
   ```bash
   ollama pull devstral
   ```

### Installation
1. Navigate to the project directory
2. Install dependencies:
   ```bash
   pip install -r requirements_ollama.txt
   ```
3. Configure environment:
   - Copy `.env` file and adjust settings if needed
   - Ensure Ollama is running: `ollama serve`

### Running the Application
```bash
# Ollama CLI version
python ce3_ollama.py

# Original Anthropic version (requires API key)
python ce3.py
```

## File Structure
- `ce3_ollama.py` - Modified CLI for Ollama integration
- `config_ollama.py` - Ollama-specific configuration
- `requirements_ollama.txt` - Dependencies for Ollama version
- `.env` - Environment configuration

## Key Modifications
- Replaced Anthropic API with Ollama client
- Tool calling via prompt injection format
- Simplified token estimation
- Maintained all original tool functionality

## Troubleshooting
- Ensure Ollama service is running: `curl http://localhost:11434/api/tags`
- Verify devstral model: `ollama list`
- Check logs if tools fail to load

## Features Retained
- Dynamic tool loading
- Rich console interface
- Token usage tracking (estimated)
- Tool creation capabilities
- Conversation management
