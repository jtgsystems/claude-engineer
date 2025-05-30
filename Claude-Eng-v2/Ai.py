import os
from dotenv import load_dotenv
import json
from tavily import TavilyClient
import re
import openai
import asyncio
import difflib
import time
import logging
from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
import asyncio
import aiohttp
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
import subprocess
import sys

def get_user_input(prompt_text="You: "):
    """Simple input function without prompt_toolkit dependencies"""
    try:
        return input(prompt_text)
    except (EOFError, KeyboardInterrupt):
        return "exit"
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import datetime
# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize the Tavily client (optional)
tavily_api_key = os.getenv("TAVILY_API_KEY", "fake_key_for_development")
try:
    from tavily import TavilyClient
    tavily = TavilyClient(api_key=tavily_api_key)
except ImportError:
    print("Tavily not installed. Web search will be disabled.")
    tavily = None

console = Console()



# Set up the conversation memory (maintains context for MAINMODEL)
conversation_history = []

# Store file contents (part of the context for MAINMODEL)
file_contents = {}

# Code editor memory (maintains some context for CODEEDITORMODEL between calls)
code_editor_memory = []

# Files already present in code editor's context
code_editor_files = set()

# automode flag
automode = False

# Store file contents
file_contents = {}

# Global dictionary to store running processes
running_processes = {}

# Constants
CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"
MAX_CONTINUATION_ITERATIONS = 25
MAX_CONTEXT_TOKENS = 200000  # Reduced to 200k tokens for context window

# Models - Updated for OpenAI GPT-4.1
MAINMODEL = "gpt-4.1"  # Maintains conversation history and file contents
TOOLCHECKERMODEL = "gpt-4.1"
CODEEDITORMODEL = "gpt-4.1"

# System prompts
BASE_SYSTEM_PROMPT = """
You are AI Engineer, an AI assistant powered by OpenAI's GPT-4.1 model, specialized in software development with access to a variety of tools and the ability to instruct and direct a coding agent and a code execution one. Your capabilities include:

1. Creating and managing project structures
2. Writing, debugging, and improving code across multiple languages
3. Providing architectural insights and applying design patterns
4. Staying current with the latest technologies and best practices
5. Analyzing and manipulating files within the project directory
6. Performing web searches for up-to-date information
7. Executing code and analyzing its output within an isolated 'code_execution_env' virtual environment
8. Managing and stopping running processes started within the 'code_execution_env'

Available tools and their optimal use cases:

1. create_folder: Create new directories in the project structure.
2. create_file: Generate new files with specified content. Strive to make the file as complete and useful as possible.
3. edit_and_apply: Examine and modify existing files by instructing a separate AI coding agent. You are responsible for providing clear, detailed instructions to this agent. When using this tool:
   - Provide comprehensive context about the project, including recent changes, new variables or functions, and how files are interconnected.
   - Clearly state the specific changes or improvements needed, explaining the reasoning behind each modification.
   - Include ALL the snippets of code to change, along with the desired modifications.
   - Specify coding standards, naming conventions, or architectural patterns to be followed.
   - Anticipate potential issues or conflicts that might arise from the changes and provide guidance on how to handle them.
4. execute_code: Run Python code exclusively in the 'code_execution_env' virtual environment and analyze its output. Use this when you need to test code functionality or diagnose issues. Remember that all code execution happens in this isolated environment. This tool now returns a process ID for long-running processes.
5. stop_process: Stop a running process by its ID. Use this when you need to terminate a long-running process started by the execute_code tool.
6. read_file: Read the contents of an existing file.
7. read_multiple_files: Read the contents of multiple existing files at once. Use this when you need to examine or work with multiple files simultaneously.
8. list_files: List all files and directories in a specified folder.
9. tavily_search: Perform a web search using the Tavily API for up-to-date information.

Tool Usage Guidelines:
- Always use the most appropriate tool for the task at hand.
- Provide detailed and clear instructions when using tools, especially for edit_and_apply.
- After making changes, always review the output to ensure accuracy and alignment with intentions.
- Use execute_code to run and test code within the 'code_execution_env' virtual environment, then analyze the results.
- For long-running processes, use the process ID returned by execute_code to stop them later if needed.
- Proactively use tavily_search when you need up-to-date information or additional context.
- When working with multiple files, consider using read_multiple_files for efficiency.

Error Handling and Recovery:
- If a tool operation fails, carefully analyze the error message and attempt to resolve the issue.
- For file-related errors, double-check file paths and permissions before retrying.
- If a search fails, try rephrasing the query or breaking it into smaller, more specific searches.
- If code execution fails, analyze the error output and suggest potential fixes, considering the isolated nature of the environment.
- If a process fails to stop, consider potential reasons and suggest alternative approaches.

Project Creation and Management:
1. Start by creating a root folder for new projects.
2. Create necessary subdirectories and files within the root folder.
3. Organize the project structure logically, following best practices for the specific project type.

Always strive for accuracy, clarity, and efficiency in your responses and actions. Your instructions must be precise and comprehensive. If uncertain, use the tavily_search tool or admit your limitations. When executing code, always remember that it runs in the isolated 'code_execution_env' virtual environment. Be aware of any long-running processes you start and manage them appropriately, including stopping them when they are no longer needed.

When using tools:
1. Carefully consider if a tool is necessary before using it.
2. Ensure all required parameters are provided and valid.
3. Handle both successful results and errors gracefully.
4. Provide clear explanations of tool usage and results to the user.

Remember, you are an AI assistant, and your primary goal is to help the user accomplish their tasks effectively and efficiently while maintaining the integrity and security of their development environment.
"""

AUTOMODE_SYSTEM_PROMPT = """
You are currently in automode. Follow these guidelines:

1. Goal Setting:
   - Set clear, achievable goals based on the user's request.
   - Break down complex tasks into smaller, manageable goals.

2. Goal Execution:
   - Work through goals systematically, using appropriate tools for each task.
   - Utilize file operations, code writing, and web searches as needed.
   - Always read a file before editing and review changes after editing.

3. Progress Tracking:
   - Provide regular updates on goal completion and overall progress.
   - Use the iteration information to pace your work effectively.

4. Tool Usage:
   - Leverage all available tools to accomplish your goals efficiently.
   - Prefer edit_and_apply for file modifications, applying changes in chunks for large edits.
   - Use tavily_search proactively for up-to-date information.

5. Error Handling:
   - If a tool operation fails, analyze the error and attempt to resolve the issue.
   - For persistent errors, consider alternative approaches to achieve the goal.

6. Automode Completion:
   - When all goals are completed, respond with "AUTOMODE_COMPLETE" to exit automode.
   - Do not ask for additional tasks or modifications once goals are achieved.

7. Iteration Awareness:
   - You have access to this {iteration_info}.
   - Use this information to prioritize tasks and manage time effectively.

Remember: Focus on completing the established goals efficiently and effectively. Avoid unnecessary conversations or requests for additional tasks.
"""


def update_system_prompt(current_iteration: Optional[int] = None, max_iterations: Optional[int] = None) -> str:
    global file_contents
    chain_of_thought_prompt = """
    Answer the user's request using relevant tools (if they are available). Before calling a tool, do some analysis within <thinking></thinking> tags. First, think about which of the provided tools is the relevant tool to answer the user's request. Second, go through each of the required parameters of the relevant tool and determine if the user has directly provided or given enough information to infer a value. When deciding if the parameter can be inferred, carefully consider all the context to see if it supports a specific value. If all of the required parameters are present or can be reasonably inferred, close the thinking tag and proceed with the tool call. BUT, if one of the values for a required parameter is missing, DO NOT invoke the function (not even with fillers for the missing params) and instead, ask the user to provide the missing parameters. DO NOT ask for more information on optional parameters if it is not provided.

    Do not reflect on the quality of the returned search results in your response.
    """
    
    file_contents_prompt = "\n\nFile Contents:\n"
    for path, content in file_contents.items():
        file_contents_prompt += f"\n--- {path} ---\n{content}\n"
    
    if automode:
        iteration_info = ""
        if current_iteration is not None and max_iterations is not None:
            iteration_info = f"You are currently on iteration {current_iteration} out of {max_iterations} in automode."
        return BASE_SYSTEM_PROMPT + file_contents_prompt + "\n\n" + AUTOMODE_SYSTEM_PROMPT.format(iteration_info=iteration_info) + "\n\n" + chain_of_thought_prompt
    else:
        return BASE_SYSTEM_PROMPT + file_contents_prompt + "\n\n" + chain_of_thought_prompt

def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder created: {path}"
    except Exception as e:
        return f"Error creating folder: {str(e)}"

def create_file(path, content=""):
    global file_contents
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        file_contents[path] = content
        return f"File created and added to system prompt: {path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"

def highlight_diff(diff_text):
    return Syntax(diff_text, "diff", theme="monokai", line_numbers=True)

def generate_and_apply_diff(original_content, new_content, path):
    diff = list(difflib.unified_diff(
        original_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=3
    ))

    if not diff:
        return "No changes detected."

    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(new_content)

        diff_text = ''.join(diff)
        highlighted_diff = highlight_diff(diff_text)

        diff_panel = Panel(
            highlighted_diff,
            title=f"Changes in {path}",
            expand=False,
            border_style="cyan"
        )

        console.print(diff_panel)

        added_lines = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        removed_lines = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

        summary = f"Changes applied to {path}:\n"
        summary += f"  Lines added: {added_lines}\n"
        summary += f"  Lines removed: {removed_lines}\n"

        return summary

    except Exception as e:
        error_panel = Panel(
            f"Error: {str(e)}",
            title="Error Applying Changes",
            style="bold red"
        )
        console.print(error_panel)
        return f"Error applying changes: {str(e)}"


async def generate_edit_instructions(file_path, file_content, instructions, project_context, full_file_contents):
    global code_editor_tokens, code_editor_memory, code_editor_files
    try:
        # Prepare memory context (this is the only part that maintains some context between calls)
        memory_context = "\n".join([f"Memory {i+1}:\n{mem}" for i, mem in enumerate(code_editor_memory)])

        # Prepare full file contents context, excluding the file being edited if it's already in code_editor_files
        full_file_contents_context = "\n\n".join([
            f"--- {path} ---\n{content}" for path, content in full_file_contents.items()
            if path != file_path or path not in code_editor_files
        ])

        system_prompt = f"""
        You are an AI coding agent that generates edit instructions for code files. Your task is to analyze the provided code and generate SEARCH/REPLACE blocks for necessary changes. Follow these steps:

        1. Review the entire file content to understand the context:
        {file_content}

        2. Carefully analyze the specific instructions:
        {instructions}

        3. Take into account the overall project context:
        {project_context}

        4. Consider the memory of previous edits:
        {memory_context}

        5. Consider the full context of all files in the project:
        {full_file_contents_context}

        6. Generate SEARCH/REPLACE blocks for each necessary change. Each block should:
           - Include enough context to uniquely identify the code to be changed
           - Provide the exact replacement code, maintaining correct indentation and formatting
           - Focus on specific, targeted changes rather than large, sweeping modifications

        7. Ensure that your SEARCH/REPLACE blocks:
           - Address all relevant aspects of the instructions
           - Maintain or enhance code readability and efficiency
           - Consider the overall structure and purpose of the code
           - Follow best practices and coding standards for the language
           - Maintain consistency with the project context and previous edits
           - Take into account the full context of all files in the project

        IMPORTANT: RETURN ONLY THE SEARCH/REPLACE BLOCKS. NO EXPLANATIONS OR COMMENTS.
        USE THE FOLLOWING FORMAT FOR EACH BLOCK:

        <SEARCH>
        Code to be replaced
        </SEARCH>
        <REPLACE>
        New code to insert
        </REPLACE>

        If no changes are needed, return an empty list.
        """        # Make the API call to CODEEDITORMODEL (context is not maintained except for code_editor_memory)
        response = await client.chat.completions.create(
            model=CODEEDITORMODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate SEARCH/REPLACE blocks for the necessary changes."}
            ],
            stream=False
        )
        
        # Process response - OpenAI returns ChatCompletion object
        response_content = ""
        if response.choices and response.choices[0].message:
            response_content = response.choices[0].message.content or ""

        # Parse the response to extract SEARCH/REPLACE blocks
        edit_instructions = parse_search_replace_blocks(response_content)

        # Update code editor memory (this is the only part that maintains some context between calls)
        code_editor_memory.append(f"Edit Instructions for {file_path}:\n{response_content}")

        # Add the file to code_editor_files set
        code_editor_files.add(file_path)

        return edit_instructions

    except Exception as e:
        console.print(f"Error in generating edit instructions: {str(e)}", style="bold red")
        return []  # Return empty list if any exception occurs



def parse_search_replace_blocks(response_text):
    blocks = []
    pattern = r'<SEARCH>\n(.*?)\n</SEARCH>\n<REPLACE>\n(.*?)\n</REPLACE>'
    matches = re.findall(pattern, response_text, re.DOTALL)
    
    for search, replace in matches:
        blocks.append({
            'search': search.strip(),
            'replace': replace.strip()
        })
    
    return json.dumps(blocks)  # Keep returning JSON string


async def edit_and_apply(path, instructions, project_context, is_automode=False, max_retries=3):
    global file_contents
    try:
        original_content = file_contents.get(path, "")        if not original_content:
            with open(path, 'r', encoding='utf-8') as file:
                original_content = file.read()
            file_contents[path] = original_content

        for attempt in range(max_retries):
            edit_instructions_json = await generate_edit_instructions(path, original_content, instructions, project_context, file_contents)
            
            if edit_instructions_json:
                edit_instructions = json.loads(edit_instructions_json)  # Parse JSON here
                console.print(Panel(f"Attempt {attempt + 1}/{max_retries}: The following SEARCH/REPLACE blocks have been generated:", title="Edit Instructions", style="cyan"))
                for i, block in enumerate(edit_instructions, 1):
                    console.print(f"Block {i}:")
                    console.print(Panel(f"SEARCH:\n{block['search']}\n\nREPLACE:\n{block['replace']}", expand=False))

                edited_content, changes_made, failed_edits = await apply_edits(path, edit_instructions, original_content)

                if changes_made:
                    file_contents[path] = edited_content  # Update the file_contents with the new content
                    console.print(Panel(f"File contents updated in system prompt: {path}", style="green"))
                    
                    if failed_edits:
                        console.print(Panel(f"Some edits could not be applied. Retrying...", style="yellow"))
                        instructions += f"\n\nPlease retry the following edits that could not be applied:\n{failed_edits}"
                        original_content = edited_content
                        continue
                    
                    return f"Changes applied to {path}"
                elif attempt == max_retries - 1:
                    return f"No changes could be applied to {path} after {max_retries} attempts. Please review the edit instructions and try again."
                else:
                    console.print(Panel(f"No changes could be applied in attempt {attempt + 1}. Retrying...", style="yellow"))
            else:
                return f"No changes suggested for {path}"
        
        return f"Failed to apply changes to {path} after {max_retries} attempts."
    except Exception as e:
        return f"Error editing/applying to file: {str(e)}"



async def apply_edits(file_path, edit_instructions, original_content):
    changes_made = False
    edited_content = original_content
    total_edits = len(edit_instructions)
    failed_edits = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        edit_task = progress.add_task("[cyan]Applying edits...", total=total_edits)

        for i, edit in enumerate(edit_instructions, 1):
            search_content = edit['search'].strip()
            replace_content = edit['replace'].strip()
            
            # Use regex to find the content, ignoring leading/trailing whitespace
            pattern = re.compile(re.escape(search_content), re.DOTALL)
            match = pattern.search(edited_content)
            
            if match:
                # Replace the content, preserving the original whitespace
                start, end = match.span()
                # Strip <SEARCH> and <REPLACE> tags from replace_content
                replace_content_cleaned = re.sub(r'</?SEARCH>|</?REPLACE>', '', replace_content)
                edited_content = edited_content[:start] + replace_content_cleaned + edited_content[end:]
                changes_made = True
                
                # Display the diff for this edit
                diff_result = generate_diff(search_content, replace_content, file_path)
                console.print(Panel(diff_result, title=f"Changes in {file_path} ({i}/{total_edits})", style="cyan"))
            else:
                console.print(Panel(f"Edit {i}/{total_edits} not applied: content not found", style="yellow"))
                failed_edits.append(f"Edit {i}: {search_content}")

            progress.update(edit_task, advance=1)

    if not changes_made:
        console.print(Panel("No changes were applied. The file content already matches the desired state.", style="green"))
    else:
        # Write the changes to the file
        with open(file_path, 'w') as file:
            file.write(edited_content)
        console.print(Panel(f"Changes have been written to {file_path}", style="green"))

    return edited_content, changes_made, "\n".join(failed_edits)

def generate_diff(original, new, path):
    diff = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=3
    ))

    diff_text = ''.join(diff)
    highlighted_diff = highlight_diff(diff_text)

    return highlighted_diff

def read_file(path):
    global file_contents
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        file_contents[path] = content
        return f"File '{path}' has been read and stored in the system prompt."
    except Exception as e:
        return f"Error reading file: {str(e)}"

def read_multiple_files(paths):
    global file_contents
    results = []
    for path in paths:
        try:
            with open(path, 'r') as f:
                content = f.read()
            file_contents[path] = content
            results.append(f"File '{path}' has been read and stored in the system prompt.")
        except Exception as e:
            results.append(f"Error reading file '{path}': {str(e)}")
    return "\n".join(results)

def list_files(path="."):
    try:
        files = os.listdir(path)
        return "\n".join(files)
    except Exception as e:
        return f"Error listing files: {str(e)}"

def tavily_search(query):
    try:
        if tavily is None:
            return f"Web search unavailable - Tavily not installed or configured"
        response = tavily.qna_search(query=query, search_depth="advanced")
        return response
    except Exception as e:
        return f"Error performing search: {str(e)}"

def execute_code(code):
    """Execute Python code in the code_execution_env virtual environment"""
    global running_processes
    
    try:
        # Path to the virtual environment
        venv_path = "code_execution_env"
        if os.name == 'nt':  # Windows
            python_executable = os.path.join(venv_path, "Scripts", "python.exe")
        else:  # Linux/Mac
            python_executable = os.path.join(venv_path, "bin", "python")
        
        # Check if virtual environment exists
        if not os.path.exists(python_executable):
            return f"Error: Virtual environment not found at {venv_path}. Please create it first with: python -m venv {venv_path}"
        
        # Write code to a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute the code
            result = subprocess.run(
                [python_executable, temp_file],
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd=os.getcwd()
            )
            
            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            if result.returncode != 0:
                output += f"Exit code: {result.returncode}\n"
            
            if not output:
                output = "Code executed successfully with no output."
            
            return output
            
        except subprocess.TimeoutExpired:
            return "Error: Code execution timed out after 30 seconds."
        except Exception as e:
            return f"Error executing code: {str(e)}"
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file)
            except:
                pass
                
    except Exception as e:
        return f"Error: {str(e)}"

def execute_code_background(code):
    """Execute Python code in background and return process ID"""
    global running_processes
    
    try:
        # Path to the virtual environment
        venv_path = "code_execution_env"
        if os.name == 'nt':  # Windows
            python_executable = os.path.join(venv_path, "Scripts", "python.exe")
        else:  # Linux/Mac
            python_executable = os.path.join(venv_path, "bin", "python")
        
        # Check if virtual environment exists
        if not os.path.exists(python_executable):
            return f"Error: Virtual environment not found at {venv_path}. Please create it first with: python -m venv {venv_path}"
        
        # Write code to a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # Start process in background
        process = subprocess.Popen(
            [python_executable, temp_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        
        # Store process with temp file for cleanup
        process_id = str(process.pid)
        running_processes[process_id] = {
            'process': process,
            'temp_file': temp_file,
            'start_time': time.time()
        }
        
        return f"Background process started with ID: {process_id}"
        
    except Exception as e:
        return f"Error starting background process: {str(e)}"

def stop_process(process_id):
    """Stop a running process by its ID"""
    global running_processes
    
    try:
        if process_id not in running_processes:
            return f"Process ID {process_id} not found in running processes."
        
        process_info = running_processes[process_id]
        process = process_info['process']
        temp_file = process_info['temp_file']
        
        # Terminate the process
        if process.poll() is None:  # Process is still running
            process.terminate()
            try:
                process.wait(timeout=5)  # Wait up to 5 seconds for graceful termination
            except subprocess.TimeoutExpired:
                process.kill()  # Force kill if it doesn't terminate gracefully
                process.wait()
        
        # Get any remaining output
        stdout, stderr = process.communicate()
        
        # Clean up temp file
        try:
            os.unlink(temp_file)
        except:
            pass
        
        # Remove from running processes
        del running_processes[process_id]
        
        result = f"Process {process_id} stopped."
        if stdout:
            result += f"\nFinal STDOUT:\n{stdout}"
        if stderr:
            result += f"\nFinal STDERR:\n{stderr}"
        
        return result
        
    except Exception as e:
        return f"Error stopping process {process_id}: {str(e)}"

def list_running_processes():
    """List all currently running processes"""
    global running_processes
    
    if not running_processes:
        return "No running processes."
    
    result = "Running processes:\n"
    for process_id, info in running_processes.items():
        process = info['process']
        start_time = info['start_time']
        runtime = time.time() - start_time
        status = "Running" if process.poll() is None else "Finished"
        result += f"  ID: {process_id}, Status: {status}, Runtime: {runtime:.1f}s\n"
    
    return result

tools = [
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Create a new folder at the specified path",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The absolute or relative path where the folder should be created"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new file at the specified path with the given content",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The absolute or relative path where the file should be created"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content of the file"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_and_apply",
            "description": "Apply AI-powered improvements to a file based on specific instructions and project context",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The absolute or relative path of the file to edit"
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Detailed instructions for the changes to be made"
                    },
                    "project_context": {
                        "type": "string",
                        "description": "Comprehensive context about the project"
                    }
                },
                "required": ["path", "instructions", "project_context"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file at the specified path",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The absolute or relative path of the file to read"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_multiple_files",
            "description": "Read the contents of multiple files at the specified paths",
            "parameters": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "An array of absolute or relative paths of the files to read"
                    }
                },
                "required": ["paths"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files and directories in the specified folder",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The absolute or relative path of the folder to list"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tavily_search",
            "description": "Perform a web search using the Tavily API",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Execute Python code in the code_execution_env virtual environment and analyze its output",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop_process",
            "description": "Stop a running process by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "process_id": {
                        "type": "string",
                        "description": "The ID of the process to stop"
                    }
                },
                "required": ["process_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_running_processes",
            "description": "List all currently running processes started by execute_code",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

from typing import Dict, Any

async def execute_tool(tool_call) -> Dict[str, Any]:
    tool_name = "unknown"  # Initialize tool_name to avoid scoping issues
    
    try:
        function_call = tool_call.function
        tool_name = function_call.name
        tool_arguments = function_call.arguments
        
        # Check if tool_arguments is a string and parse it if necessary
        if isinstance(tool_arguments, str):
            try:
                tool_input = json.loads(tool_arguments)
            except json.JSONDecodeError:
                return {
                    "content": f"Error: Failed to parse tool arguments for {tool_name}",
                    "is_error": True
                }
        else:
            tool_input = tool_arguments

        result = None
        is_error = False

        if tool_name == "create_folder":
            if "path" not in tool_input:
                raise KeyError("Missing 'path' parameter for create_folder")
            result = create_folder(tool_input["path"])
        elif tool_name == "create_file":
            result = create_file(tool_input["path"], tool_input.get("content", ""))
        elif tool_name == "edit_and_apply":
            result = await edit_and_apply(
                tool_input["path"],
                tool_input["instructions"],
                tool_input["project_context"],
                is_automode=automode
            )
        elif tool_name == "read_file":
            result = read_file(tool_input["path"])
        elif tool_name == "read_multiple_files":
            result = read_multiple_files(tool_input["paths"])
        elif tool_name == "list_files":
            result = list_files(tool_input.get("path", "."))
        elif tool_name == "tavily_search":
            result = tavily_search(tool_input["query"])
        elif tool_name == "execute_code":
            result = execute_code(tool_input["code"])
        elif tool_name == "stop_process":
            result = stop_process(tool_input["process_id"])
        elif tool_name == "list_running_processes":
            result = list_running_processes()
        else:
            is_error = True
            result = f"Unknown tool: {tool_name}"

        return {
            "content": result,
            "is_error": is_error
        }
    except KeyError as e:
        error_message = f"Missing required parameter {str(e)} for tool {tool_name}"
        logging.error(error_message)
        return {
            "content": f"Error: {error_message}",
            "is_error": True
        }
    except Exception as e:
        error_message = f"Error executing tool {tool_name}: {str(e)}"
        logging.error(error_message)
        return {
            "content": f"Error: {error_message}",
            "is_error": True
        }


def parse_goals(response):
    goals = re.findall(r'Goal \d+: (.+)', response)
    return goals

async def execute_goals(goals):
    global automode
    for i, goal in enumerate(goals, 1):
        console.print(Panel(f"Executing Goal {i}: {goal}", title="Goal Execution", style="bold yellow"))
        response, _ = await chat_with_ollama(f"Continue working on goal: {goal}")
        if CONTINUATION_EXIT_PHRASE in response:
            automode = False
            console.print(Panel("Exiting automode.", title="Automode", style="bold green"))
            break

async def run_goals(response):
    goals = parse_goals(response)
    await execute_goals(goals)


def save_chat():
    # Generate filename
    now = datetime.datetime.now()
    filename = f"Chat_{now.strftime('%H%M')}.md"
    
    # Format conversation history
    formatted_chat = "# AI Engineer Chat Log\n\n"
    for message in conversation_history:
        if message['role'] == 'user':
            formatted_chat += f"## User\n\n{message['content']}\n\n"
        elif message['role'] == 'assistant':
            if isinstance(message['content'], str):
                formatted_chat += f"## AI Engineer\n\n{message['content']}\n\n"
            elif isinstance(message['content'], list):
                for content in message['content']:
                    if content['type'] == 'tool_use':
                        formatted_chat += f"### Tool Use: {content['name']}\n\n```json\n{json.dumps(content['input'], indent=2)}\n```\n\n"
                    elif content['type'] == 'text':
                        formatted_chat += f"## AI Engineer\n\n{content['text']}\n\n"
        elif message['role'] == 'user' and isinstance(message['content'], list):
            for content in message['content']:
                if content['type'] == 'tool_result':
                    formatted_chat += f"### Tool Result\n\n```\n{content['content']}\n```\n\n"
    
    # Save to file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(formatted_chat)
    
    return filename



async def chat_with_ollama(user_input, image_path=None, current_iteration=None, max_iterations=None):
    global conversation_history, automode

    # Build conversation messages
    current_conversation = [{"role": "user", "content": user_input}]
    messages = conversation_history + current_conversation

    try:
        # Create system message with file context
        system_message = {"role": "system", "content": update_system_prompt(current_iteration, max_iterations)}
        messages_with_system = [system_message] + messages
        
        # Call OpenAI API with tools
        response = await client.chat.completions.create(
            model=MAINMODEL,
            messages=messages_with_system,
            tools=tools,
            tool_choice="auto",
            stream=False
        )
        
        # Process response - OpenAI returns ChatCompletion object
        if response.choices and response.choices[0].message:
            message = response.choices[0].message
            assistant_response = message.content or ""
            
            # Handle tool calls if present
            if message.tool_calls:
                # Add assistant message with tool calls to conversation
                conversation_history = messages + [{"role": "assistant", "content": assistant_response, "tool_calls": message.tool_calls}]
                
                # Execute tools and collect results
                tool_responses = []
                for tool_call in message.tool_calls:
                    tool_result = await execute_tool(tool_call)
                    tool_responses.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": str(tool_result["content"])
                    })
                    
                    # Display tool result
                    style = "red" if tool_result.get("is_error") else "green"
                    console.print(Panel(str(tool_result["content"]), title=f"Tool: {tool_call.function.name}", style=style))
                
                # Add tool responses to conversation
                conversation_history.extend(tool_responses)
                
                # Get final response after tool execution
                final_response = await client.chat.completions.create(
                    model=MAINMODEL,
                    messages=[system_message] + conversation_history,
                    stream=False
                )
                
                if final_response.choices and final_response.choices[0].message:
                    final_assistant_response = final_response.choices[0].message.content or ""
                    console.print(Panel(Markdown(final_assistant_response), title="AI Engineer", title_align="left", border_style="blue", expand=False))
                    
                    # Update conversation history with final response
                    conversation_history.append({"role": "assistant", "content": final_assistant_response})
                    
                    # Display files in context
                    if file_contents:
                        files_in_context = "\n".join(file_contents.keys())
                    else:
                        files_in_context = "No files in context. Read, create, or edit files to add."
                    console.print(Panel(files_in_context, title="Files in Context", title_align="left", border_style="white", expand=False))
                    
                    return final_assistant_response, CONTINUATION_EXIT_PHRASE in final_assistant_response
                else:
                    return "Tool execution completed", False
            else:
                # No tool calls, just regular response
                if not assistant_response:
                    assistant_response = "I'm sorry, I didn't generate a response. Please try again."
                
                console.print(Panel(Markdown(assistant_response), title="AI Engineer", title_align="left", border_style="blue", expand=False))
                
                # Update conversation history
                conversation_history = messages + [{"role": "assistant", "content": assistant_response}]
                
                # Display files in context
                if file_contents:
                    files_in_context = "\n".join(file_contents.keys())
                else:
                    files_in_context = "No files in context. Read, create, or edit files to add."
                console.print(Panel(files_in_context, title="Files in Context", title_align="left", border_style="white", expand=False))
                
                return assistant_response, CONTINUATION_EXIT_PHRASE in assistant_response
            
        else:
            console.print(Panel("Unexpected response format", title="API Error", style="bold red"))
            return "Error: Unexpected response format", False
            
    except Exception as e:
        console.print(Panel(f"API Error: {str(e)}", title="API Error", style="bold red"))
        return f"Error: {str(e)}", False

async def handle_tool_requests(response_text):
    """Enhanced tool request handler with better parsing"""
    import re
    try:
        # Pattern 1: XML-style tags <create_folder directory_path="path" />
        xml_folder = re.search(r'<create_folder[^>]*directory_path="([^"]+)"[^>]*/?>', response_text)
        if xml_folder:
            folder_path = xml_folder.group(1)
            return create_folder(folder_path)
            
        # Pattern 2: XML-style file creation
        xml_file = re.search(r'<create_file[^>]*(?:path|file_path)="([^"]+)"[^>]*/?>', response_text)
        if xml_file:
            file_path = xml_file.group(1)
            return create_file(file_path, "# File created by Ollama Engineer\n")
            
        # Pattern 3: Natural language patterns
        if "create" in response_text.lower() and "folder" in response_text.lower():
            # Look for quoted paths or common path patterns
            path_match = re.search(r'["\'](C:\\[^"\']+)["\']', response_text) or \
                        re.search(r'(C:\\Users\\[^\s]+)', response_text) or \
                        re.search(r'desktop[/\\](\w+)', response_text, re.IGNORECASE)
            if path_match:
                folder_path = path_match.group(1)
                return create_folder(folder_path)
                
        # Pattern 4: Simple folder names for desktop
        if "TEST" in response_text and "desktop" in response_text.lower():
            return create_folder(r"C:\Users\Owner\Desktop\TEST")
            
    except Exception as e:
        return f"Tool execution error: {str(e)}"
    
    return None

def reset_code_editor_memory():
    global code_editor_memory
    code_editor_memory = []
    console.print(Panel("Code editor memory has been reset.", title="Reset", style="bold green"))


def reset_conversation():
    global conversation_history, file_contents, code_editor_files
    conversation_history = []
    file_contents = {}
    code_editor_files = set()
    reset_code_editor_memory()
    console.print(Panel("Conversation history, file contents, code editor memory, and code editor files have been reset.", title="Reset", style="bold green"))




async def main():
    global automode, conversation_history
    console.print(Panel("Welcome to AI Engineer with GPT-4.1!", title="Welcome", style="bold green"))
    console.print("Type 'exit' to end the conversation.")
    console.print("Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.")
    console.print("Type 'reset' to clear the conversation history.")
    console.print("Type 'save chat' to save the conversation to a Markdown file.")
    console.print("While in automode, press Ctrl+C at any time to exit the automode to return to regular chat.")

    while True:
        user_input = get_user_input()

        if user_input.lower() == 'exit':
            console.print(Panel("Thank you for chatting. Goodbye!", title_align="left", title="Goodbye", style="bold green"))
            break

        if user_input.lower() == 'reset':
            reset_conversation()
            continue

        if user_input.lower() == 'save chat':
            filename = save_chat()
            console.print(Panel(f"Chat saved to {filename}", title="Chat Saved", style="bold green"))
            continue

        if user_input.lower().startswith('automode'):
            try:
                parts = user_input.split()
                if len(parts) > 1 and parts[1].isdigit():
                    max_iterations = int(parts[1])
                else:
                    max_iterations = MAX_CONTINUATION_ITERATIONS

                automode = True
                console.print(Panel(f"Entering automode with {max_iterations} iterations. Please provide the goal of the automode.", title_align="left", title="Automode", style="bold yellow"))
                console.print(Panel("Press Ctrl+C at any time to exit the automode loop.", style="bold yellow"))
                user_input = get_user_input()

                iteration_count = 0
                try:
                    while automode and iteration_count < max_iterations:
                        response, exit_continuation = await chat_with_ollama(user_input, current_iteration=iteration_count+1, max_iterations=max_iterations)

                        if exit_continuation or CONTINUATION_EXIT_PHRASE in response:
                            console.print(Panel("Automode completed.", title_align="left", title="Automode", style="green"))
                            automode = False
                        else:
                            console.print(Panel(f"Continuation iteration {iteration_count + 1} completed. Press Ctrl+C to exit automode. ", title_align="left", title="Automode", style="yellow"))
                            user_input = "Continue with the next step. Or STOP by saying 'AUTOMODE_COMPLETE' if you think you've achieved the results established in the original request."
                        iteration_count += 1

                        if iteration_count >= max_iterations:
                            console.print(Panel("Max iterations reached. Exiting automode.", title_align="left", title="Automode", style="bold red"))
                            automode = False
                except KeyboardInterrupt:
                    console.print(Panel("\nAutomode interrupted by user. Exiting automode.", title_align="left", title="Automode", style="bold red"))
                    automode = False
                    if conversation_history and conversation_history[-1]["role"] == "user":
                        conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})
            except KeyboardInterrupt:
                console.print(Panel("\nAutomode interrupted by user. Exiting automode.", title_align="left", title="Automode", style="bold red"))
                automode = False
                if conversation_history and conversation_history[-1]["role"] == "user":
                    conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})

            console.print(Panel("Exited automode. Returning to regular chat.", style="green"))
        else:
            response, _ = await chat_with_ollama(user_input)

if __name__ == "__main__":
    asyncio.run(main())
