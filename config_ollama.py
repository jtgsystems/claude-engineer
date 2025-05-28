from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Ollama Configuration
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    MODEL = os.getenv('MODEL', 'devstral:latest')  # Using full model name
    MAX_TOKENS = 8000
    MAX_CONVERSATION_TOKENS = 200000
    
    # Remove Anthropic API requirement for Ollama
    ANTHROPIC_API_KEY = None  # Not needed for Ollama
    
    # Paths
    BASE_DIR = Path(__file__).parent
    TOOLS_DIR = BASE_DIR / "tools"
    PROMPTS_DIR = BASE_DIR / "prompts"

    # Assistant Configuration
    ENABLE_THINKING = True
    SHOW_TOOL_USAGE = True
    DEFAULT_TEMPERATURE = 0.7
