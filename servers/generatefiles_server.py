from mcp.server.fastmcp import FastMCP

mcp = FastMCP("File Creator")

@mcp.tool(description="Create a file at the given path and write content to it")
def create_file(path: str, content: str) -> str:
    """Create a file and write content to it."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File created at {path}"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
