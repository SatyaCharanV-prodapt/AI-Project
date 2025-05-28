import os
import asyncio
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain_openai import AzureChatOpenAI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
API_VERSION = os.getenv("API_VERSION")
GITHUB_PERSONAL_ACCESS_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")

llm = AzureChatOpenAI(
    azure_deployment=DEPLOYMENT_NAME,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_API_KEY,
    openai_api_version=API_VERSION,
    temperature=1,
)

app = FastAPI()

# Add CORS middleware to the FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins. Replace "*" with specific origins if needed.
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.).
    allow_headers=["*"],  # Allow all headers.
)

# Chat history to store the conversation
chat_history = []

class UserInput(BaseModel):
    message: str
    # file is not a pydantic field, handled by FastAPI directly

async def initialize_agent():
    """Initialize tools and agent asynchronously."""
    # Initialize the multi-server client
    client = MultiServerMCPClient(
        {
            "terminal": {
                "command": "python",
                "args": [
                    "C:/Users/satyacharan.v/Desktop/mcp-servers/AI_SYSCO/servers/terminal_server.py"
                ],
                "transport": "stdio"
            },
            "file_creator": {
                "command": "python",
                "args": [
                    "C:/Users/satyacharan.v/Desktop/mcp-servers/AI_SYSCO/servers/generatefiles_server.py"
                ],
                "transport": "stdio"
            },
            "github": {
                "command": "docker",
                "args": [
                    "run",
                    "-i",
                    "--rm",
                    "-e",
                    "GITHUB_PERSONAL_ACCESS_TOKEN",
                    "mcp-github"
                ],
                "transport": "stdio",
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_PERSONAL_ACCESS_TOKEN
                }
            }
        }
    )

    print("Client initialized")
    tools = await client.get_tools()
    print("Available tools:", tools)

    return create_react_agent(llm, tools)

# Initialize the agent
agent = asyncio.run(initialize_agent())

@app.post("/chat")
async def chat(user_input: UserInput = None, file: UploadFile = File(None)):
    global chat_history
    user_message = user_input.message if user_input else ""
    file_content = None
    file_name = None
    if file is not None:
        file_content = await file.read()
        file_name = file.filename
        user_message += f"\n[File uploaded: {file_name}]"
    chat_history.append(HumanMessage(content=user_message))
    # Prepare messages for the agent
    messages = [
        SystemMessage(content="You are a helpful AI assistant that uses tools to solve problems.")
    ] + chat_history
    # Optionally, you can add file content as a separate message or context
    if file_content:
        messages.append(HumanMessage(content=f"[File content: {file_content[:1000]}...]"))  # Limit preview
    try:
        print("Preparing to invoke the agent with messages")
        response = await asyncio.wait_for(
            agent.ainvoke({"messages": messages}),
            timeout=600
        )
        ai_response = response["messages"][-1].content
        chat_history.append(AIMessage(content=ai_response))
        return {"response": ai_response}
    except asyncio.TimeoutError:
        return {"error": "AI took too long to respond. Please try again."}
    except Exception as e:
        return {"error": str(e)}

# Run the FastAPI server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
