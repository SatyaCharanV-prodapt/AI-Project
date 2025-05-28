import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from fastapi.middleware.cors import CORSMiddleware

# Gemini LLM imports
import google.generativeai as genai
from google.generativeai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro-latest")
GITHUB_PERSONAL_ACCESS_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")

# Gemini LLM wrapper
class GeminiLLM:
    def __init__(self, model_name: str, api_key: str):
        genai.configure(api_key=api_key)
        self.model_name = model_name
        # No Client() in google.generativeai; use genai directly

    async def ainvoke(self, prompt: str) -> str:
        resp = genai.generate_content(
            model=self.model_name, contents=prompt
        )
        return resp.text.strip() or "I’m not sure how to answer that."

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_history = []

class UserInput(BaseModel):
    message: str

async def initialize_agent():
    client = MultiServerMCPClient(
        {
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
    # print("Available tools:", tools)
    # Use GeminiLLM as the LLM
    llm = GeminiLLM(model_name=GEMINI_MODEL, api_key=GEMINI_API_KEY)
    print("Gemini LLM initialized")
    # Adapter for compatibility with create_react_agent
    from langchain_core.language_models.chat_models import BaseChatModel
    class GeminiChatModel(BaseChatModel):
        llm: GeminiLLM  # Pydantic expects fields to be declared
        tools: list = []  # Add tools as a field for Pydantic
        def __init__(self, llm):
            object.__setattr__(self, 'llm', llm)
            object.__setattr__(self, 'tools', [])
        def bind_tools(self, tools):
            object.__setattr__(self, 'tools', tools)
            return self
        async def ainvoke(self, input):
            print(f"Received input for ainvoke: {input}")
            prompt = input["messages"][-1].content
            result = await self.llm.ainvoke(prompt)
            print(f"Gemini LLM result: {result}")
            return {"messages": chat_history + [AIMessage(content=result)]}
        @property
        def _llm_type(self):
            return "gemini"
        async def _generate(self, messages, stop=None):
            prompt = messages[-1].content
            print(f"_generate called with prompt: {prompt}")
            text = await self.llm.ainvoke(prompt)
            print(f"_generate result: {text}")
            return text
    return create_react_agent(GeminiChatModel(llm), tools)

agent = asyncio.run(initialize_agent())

@app.post("/chat")
async def chat(user_input: UserInput):
    global chat_history
    chat_history.append(HumanMessage(content=user_input.message))
    print(f"User message added to chat history: {user_input.message}")
    messages = [
        SystemMessage(content="You are a helpful AI assistant that uses tools to solve problems.")
    ] + chat_history
    try:
        print("Preparing to invoke the agent with messages")
        response =await agent.ainvoke({"messages": messages}
        )
        print(f"Response received from agent {response}")
        ai_response = response["messages"][-1].content
        chat_history.append(AIMessage(content=ai_response))
        return {"response": ai_response}
    except asyncio.TimeoutError:
        return {"error": "AI took too long to respond. Please try again."}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
