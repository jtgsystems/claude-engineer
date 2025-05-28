import ollama
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from typing import List, Dict, Any
import importlib
import inspect
import pkgutil
import os
import json
import sys
import logging

from config_ollama import Config
from tools.base import BaseTool
def get_user_input(prompt_text="You: "):
    """Windows-compatible input function"""
    print(prompt_text, end="", flush=True)
    return input()
from prompts.system_prompts import SystemPrompts

# Configure logging to only show ERROR level and above
logging.basicConfig(
    level=logging.ERROR,
    format='%(levelname)s: %(message)s'
)

class Assistant:
    """
    Modified Assistant class for Ollama integration with devstral model
    """

    def __init__(self):
        # Initialize Ollama client
        self.client = ollama.Client(host=Config.OLLAMA_BASE_URL)
        
        # Verify devstral model is available
        try:
            models = self.client.list()
            available_models = [model.model for model in models.models]
            
            if Config.MODEL not in available_models:
                raise ValueError(f"Model '{Config.MODEL}' not found. Available: {available_models}")
        except Exception as e:
            raise ValueError(f"Cannot connect to Ollama: {e}")

        self.conversation_history: List[Dict[str, Any]] = []
        self.console = Console()

        self.thinking_enabled = getattr(Config, 'ENABLE_THINKING', False)
        self.temperature = getattr(Config, 'DEFAULT_TEMPERATURE', 0.7)
        self.total_tokens_used = 0

        self.tools = self._load_tools()

    def _execute_uv_install(self, package_name: str) -> bool:
        """Execute uvpackagemanager tool to install missing packages."""
        class ToolUseMock:
            name = "uvpackagemanager"
            input = {
                "command": "install",
                "packages": [package_name]
            }

        result = self._execute_tool(ToolUseMock())
        if "Error" not in result and "failed" not in result.lower():
            self.console.print("[green]Package installed successfully.[/green]")
            return True
        else:
            self.console.print(f"[red]Failed to install {package_name}. Output:[/red] {result}")
            return False

    def _load_tools(self) -> List[Dict[str, Any]]:
        """Dynamically load all tool classes from the tools directory."""
        tools = []
        tools_path = getattr(Config, 'TOOLS_DIR', None)

        if tools_path is None:
            self.console.print("[red]TOOLS_DIR not set in Config[/red]")
            return tools

        # Clear cached tool modules for fresh import
        for module_name in list(sys.modules.keys()):
            if module_name.startswith('tools.') and module_name != 'tools.base':
                del sys.modules[module_name]

        try:
            for module_info in pkgutil.iter_modules([str(tools_path)]):
                if module_info.name == 'base':
                    continue

                try:
                    module = importlib.import_module(f'tools.{module_info.name}')
                    self._extract_tools_from_module(module, tools)
                except ImportError as e:
                    missing_module = self._parse_missing_dependency(str(e))
                    self.console.print(f"\n[yellow]Missing dependency:[/yellow] {missing_module} for tool {module_info.name}")
                    user_response = input(f"Install {missing_module}? (y/n): ").lower()

                    if user_response == 'y':
                        success = self._execute_uv_install(missing_module)
                        if success:
                            try:
                                module = importlib.import_module(f'tools.{module_info.name}')
                                self._extract_tools_from_module(module, tools)
                            except Exception as retry_err:
                                self.console.print(f"[red]Failed to load tool after installation: {str(retry_err)}[/red]")
                        else:
                            self.console.print(f"[red]Installation of {missing_module} failed. Skipping this tool.[/red]")
                    else:
                        self.console.print(f"[yellow]Skipping tool {module_info.name} due to missing dependency[/yellow]")
                except Exception as mod_err:
                    self.console.print(f"[red]Error loading module {module_info.name}:[/red] {str(mod_err)}")
        except Exception as overall_err:
            self.console.print(f"[red]Error in tool loading process:[/red] {str(overall_err)}")

        return tools

    def _parse_missing_dependency(self, error_str: str) -> str:
        """Parse the missing dependency name from an ImportError string."""
        if "No module named" in error_str:
            parts = error_str.split("No module named")
            missing_module = parts[-1].strip(" '\"")
        else:
            missing_module = error_str
        return missing_module

    def _extract_tools_from_module(self, module, tools: List[Dict[str, Any]]) -> None:
        """Find and instantiate all tool classes from a module."""
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and issubclass(obj, BaseTool) and obj != BaseTool):
                try:
                    tool_instance = obj()
                    tools.append({
                        "name": tool_instance.name,
                        "description": tool_instance.description,
                        "input_schema": tool_instance.input_schema
                    })
                    self.console.print(f"[green]Loaded tool:[/green] {tool_instance.name}")
                except Exception as tool_init_err:
                    self.console.print(f"[red]Error initializing tool {name}:[/red] {str(tool_init_err)}")

    def refresh_tools(self):
        """Refresh the list of tools and show newly discovered tools."""
        current_tool_names = {tool['name'] for tool in self.tools}
        self.tools = self._load_tools()
        new_tool_names = {tool['name'] for tool in self.tools}
        new_tools = new_tool_names - current_tool_names

        if new_tools:
            self.console.print("\n")
            for tool_name in new_tools:
                tool_info = next((t for t in self.tools if t['name'] == tool_name), None)
                if tool_info:
                    description_lines = tool_info['description'].strip().split('\n')
                    formatted_description = '\n    '.join(line.strip() for line in description_lines)
                    self.console.print(f"[bold green]NEW[/bold green] 🔧 [cyan]{tool_name}[/cyan]:\n    {formatted_description}")
        else:
            self.console.print("\n[yellow]No new tools found[/yellow]")

    def display_available_tools(self):
        """Print a list of currently loaded tools."""
        self.console.print("\n[bold cyan]Available tools:[/bold cyan]")
        tool_names = [tool['name'] for tool in self.tools]
        if tool_names:
            formatted_tools = ", ".join([f"[cyan]{name}[/cyan]" for name in tool_names])
        else:
            formatted_tools = "No tools available."
        self.console.print(formatted_tools)
        self.console.print("\n---")

    def _display_tool_usage(self, tool_name: str, input_data: Dict, result: str):
        """Display tool usage if enabled."""
        if not getattr(Config, 'SHOW_TOOL_USAGE', False):
            return

        cleaned_input = self._clean_data_for_display(input_data)
        cleaned_result = self._clean_data_for_display(result)

        tool_info = f"""[cyan]📥 Input:[/cyan] {json.dumps(cleaned_input, indent=2)}
[cyan]📤 Result:[/cyan] {cleaned_result}"""
        
        panel = Panel(
            tool_info,
            title=f"Tool used: {tool_name}",
            title_align="left",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)

    def _clean_data_for_display(self, data):
        """Clean data for display by handling various data types."""
        if isinstance(data, str):
            try:
                parsed_data = json.loads(data)
                return self._clean_parsed_data(parsed_data)
            except json.JSONDecodeError:
                if len(data) > 1000 and ';base64,' in data:
                    return "[base64 data omitted]"
                return data
        elif isinstance(data, dict):
            return self._clean_parsed_data(data)
        else:
            return data

    def _clean_parsed_data(self, data):
        """Recursively clean parsed JSON/dict data."""
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if key in ['data', 'image', 'source'] and isinstance(value, str):
                    if len(value) > 1000 and (';base64,' in value or value.startswith('data:')):
                        cleaned[key] = "[base64 data omitted]"
                    else:
                        cleaned[key] = value
                else:
                    cleaned[key] = self._clean_parsed_data(value)
            return cleaned
        elif isinstance(data, list):
            return [self._clean_parsed_data(item) for item in data]
        elif isinstance(data, str) and len(data) > 1000 and ';base64,' in data:
            return "[base64 data omitted]"
        return data

    def _execute_tool(self, tool_use):
        """Execute a tool dynamically."""
        tool_name = tool_use.name
        tool_input = tool_use.input or {}
        tool_result = None

        try:
            module = importlib.import_module(f'tools.{tool_name}')
            tool_instance = self._find_tool_instance_in_module(module, tool_name)

            if not tool_instance:
                tool_result = f"Tool not found: {tool_name}"
            else:
                try:
                    result = tool_instance.execute(**tool_input)
                    tool_result = result
                except Exception as exec_err:
                    tool_result = f"Error executing tool '{tool_name}': {str(exec_err)}"
        except ImportError:
            tool_result = f"Failed to import tool: {tool_name}"
        except Exception as e:
            tool_result = f"Error executing tool: {str(e)}"

        self._display_tool_usage(tool_name, tool_input, 
            json.dumps(tool_result) if not isinstance(tool_result, str) else tool_result)
        return tool_result

    def _find_tool_instance_in_module(self, module, tool_name: str):
        """Find a tool instance in a module by name."""
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and issubclass(obj, BaseTool) and obj != BaseTool):
                candidate_tool = obj()
                if candidate_tool.name == tool_name:
                    return candidate_tool
        return None

    def _display_token_usage(self, used_tokens: int = 0):
        """Display token usage visualization."""
        self.total_tokens_used += used_tokens
        used_percentage = (self.total_tokens_used / Config.MAX_CONVERSATION_TOKENS) * 100
        remaining_tokens = max(0, Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used)

        self.console.print(f"\nTotal used: {self.total_tokens_used:,} / {Config.MAX_CONVERSATION_TOKENS:,}")

        bar_width = 40
        filled = int(used_percentage / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        color = "green"
        if used_percentage > 75:
            color = "yellow"
        if used_percentage > 90:
            color = "red"

        self.console.print(f"[{color}][{bar}] {used_percentage:.1f}%[/{color}]")

        if remaining_tokens < 20000:
            self.console.print(f"[bold red]Warning: Only {remaining_tokens:,} tokens remaining![/bold red]")

        self.console.print("---")

    def _format_tools_for_ollama(self) -> str:
        """Format tools for Ollama prompt injection."""
        if not self.tools:
            return "No tools available."
        
        tool_descriptions = []
        for tool in self.tools:
            tool_desc = f"Tool: {tool['name']}\nDescription: {tool['description']}\nSchema: {json.dumps(tool['input_schema'], indent=2)}"
            tool_descriptions.append(tool_desc)
        
        return "\n\n".join(tool_descriptions)

    def _get_completion(self):
        """Get completion from Ollama."""
        try:
            # Format conversation for Ollama
            messages = []
            for msg in self.conversation_history:
                if msg['role'] == 'user':
                    messages.append({
                        'role': 'user',
                        'content': msg['content'] if isinstance(msg['content'], str) else str(msg['content'])
                    })
                elif msg['role'] == 'assistant':
                    messages.append({
                        'role': 'assistant',
                        'content': msg['content'] if isinstance(msg['content'], str) else str(msg['content'])
                    })

            # Add system prompt with tools
            system_prompt = f"""{SystemPrompts.DEFAULT}

Available Tools:
{self._format_tools_for_ollama()}

You can call tools by responding in this format:
TOOL_CALL: tool_name
TOOL_INPUT: {{"param": "value"}}

{SystemPrompts.TOOL_USAGE}"""

            # Create system message as first message instead of system parameter
            system_message = {
                'role': 'system',
                'content': system_prompt
            }
            
            # Combine system + conversation messages
            all_messages = [system_message] + messages

            response = self.client.chat(
                model=Config.MODEL,
                messages=all_messages,
                options={
                    'temperature': self.temperature,
                    'num_ctx': min(Config.MAX_TOKENS, Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used)
                }
            )

            response_text = response['message']['content']
            
            # Estimate token usage (rough approximation)
            estimated_tokens = len(response_text.split()) * 1.3
            self._display_token_usage(int(estimated_tokens))

            # Check for tool calls in response
            if "TOOL_CALL:" in response_text and "TOOL_INPUT:" in response_text:
                return self._handle_tool_call(response_text)
            
            # Add response to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })
            
            return response_text

        except Exception as e:
            logging.error(f"Error in _get_completion: {str(e)}")
            return f"Error: {str(e)}"

    def _handle_tool_call(self, response_text: str):
        """Parse and execute tool calls from Ollama response."""
        try:
            lines = response_text.split('\n')
            tool_name = None
            tool_input = None
            
            for i, line in enumerate(lines):
                if line.startswith('TOOL_CALL:'):
                    tool_name = line.replace('TOOL_CALL:', '').strip()
                elif line.startswith('TOOL_INPUT:'):
                    input_text = line.replace('TOOL_INPUT:', '').strip()
                    try:
                        tool_input = json.loads(input_text)
                    except json.JSONDecodeError:
                        tool_input = {}

            if tool_name:
                self.console.print(f"\n[bold yellow]Executing tool: {tool_name}[/bold yellow]\n")
                
                # Create mock tool use object
                class ToolUseMock:
                    def __init__(self, name, input_data):
                        self.name = name
                        self.input = input_data
                
                tool_result = self._execute_tool(ToolUseMock(tool_name, tool_input))
                
                # Add tool execution to conversation
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": response_text
                })
                self.conversation_history.append({
                    "role": "user",
                    "content": f"Tool result: {tool_result}"
                })
                
                # Get follow-up response
                return self._get_completion()
            
            return response_text
            
        except Exception as e:
            return f"Error handling tool call: {str(e)}"

    def chat(self, user_input):
        """Process a chat message from the user."""
        if isinstance(user_input, str):
            if user_input.lower() == 'refresh':
                self.refresh_tools()
                return "Tools refreshed successfully!"
            elif user_input.lower() == 'reset':
                self.reset()
                return "Conversation reset!"
            elif user_input.lower() == 'quit':
                return "Goodbye!"

        try:
            # Add user message to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })

            # Show thinking indicator if enabled
            if self.thinking_enabled:
                with Live(Spinner('dots', text='Thinking...', style="cyan"), 
                         refresh_per_second=10, transient=True):
                    response = self._get_completion()
            else:
                response = self._get_completion()

            return response

        except Exception as e:
            logging.error(f"Error in chat: {str(e)}")
            return f"Error: {str(e)}"

    def reset(self):
        """Reset the assistant's memory and token usage."""
        self.conversation_history = []
        self.total_tokens_used = 0
        self.console.print("\nAssistant memory has been reset!")

        welcome_text = """
# Claude Engineer v3 with Ollama + devstral

Type 'refresh' to reload available tools
Type 'reset' to clear conversation history  
Type 'quit' to exit

Available tools:
"""
        self.console.print(Markdown(welcome_text))
        self.display_available_tools()


def main():
    """Entry point for the assistant CLI loop."""
    console = Console()

    try:
        assistant = Assistant()
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        console.print("Please ensure Ollama is running and devstral model is installed.")
        return

    welcome_text = """
# Claude Engineer v3 with Ollama + devstral

Type 'refresh' to reload available tools
Type 'reset' to clear conversation history
Type 'quit' to exit

Available tools:
"""
    console.print(Markdown(welcome_text))
    assistant.display_available_tools()

    while True:
        try:
            user_input = get_user_input().strip()

            if user_input.lower() == 'quit':
                console.print("\nGoodbye!")
                break
            elif user_input.lower() == 'reset':
                assistant.reset()
                continue

            response = assistant.chat(user_input)
            console.print("\n[bold purple]Claude Engineer (Ollama):[/bold purple]")
            if isinstance(response, str):
                safe_response = response.replace('[', '\\[').replace(']', '\\]')
                console.print(safe_response)
            else:
                console.print(str(response))

        except KeyboardInterrupt:
            continue
        except EOFError:
            break


if __name__ == "__main__":
    main()
