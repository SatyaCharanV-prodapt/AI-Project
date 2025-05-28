from mcp.server.fastmcp import FastMCP
import asyncio
import subprocess
from typing import Optional
from pathlib import Path
import requests

# Create an MCP server
mcp = FastMCP("Terminal Server")

@mcp.tool(description="Execute a terminal command and return its output")
def run_terminal_command(command: str) -> dict[str, Optional[str]]:
    """Execute a terminal command and return its output
    
    Args:
        command: The command to execute
        
    Returns:
        Dictionary containing stdout and stderr
    """
    try:
        # Run command and capture output
        process = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout for safety
        )
        
        return {
            "stdout": process.stdout if process.stdout else None,
            "stderr": process.stderr if process.stderr else None,
            "return_code": process.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": None,
            "stderr": "Command timed out after 30 seconds",
            "return_code": -1
        }
    except Exception as e:
        return {
            "stdout": None,
            "stderr": f"Error executing command: {str(e)}",
            "return_code": -1
        }

if __name__ == "__main__":
    mcp.run(transport="stdio")
