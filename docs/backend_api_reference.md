BACKEND SERVICES – API SPECIFICATION
====================================
Repository: AI-Project (test/branch)
Framework: FastAPI (Python ≥3.9)
Default host/port: http://127.0.0.1:8000
CORS: fully open (all origins, methods, headers, credentials True)


1. Common behaviour
-------------------
• Stateless FastAPI instances, but each file keeps an in-memory chat_history list that persists for the lifetime of the process (or until it is re-started).
• Both expose a single POST /chat endpoint that accepts a JSON payload (and optionally a file for the Azure version).
• Returns JSON with either response or error.
• No explicit authentication/authorisation layer is implemented; any client that can reach the server may call the endpoint.
• Time-outs: 600 s (10 min) per LLM call.
• Error handling: generic try/except → HTTP 200 with {"error": "..."} (consider changing to proper HTTP status codes).

---
2. mcp_client_ai.py  ("Azure OpenAI Agent")
-------------------------------------------
POST /chat
~~~~~~~~~
Description  
  Chat completion powered by an Azure OpenAI deployment; supports optional single-file upload (binary content is injected into the prompt).

Request  
 Content-Type: multipart/form-data or application/json  
 Body fields  
  • message   string    (required if no file)  
  • file      binary    (optional) UploadFile

Example (cURL)  
```
curl -X POST http://localhost:8000/chat  \
     -F 'message=Summarise this file'     \
     -F 'file=@report.pdf'
```

Successful Response  HTTP 200  
```json
{ "response": "<assistant-reply>" }
```

Failure Response (Timeout / Other exception)  
```json
{ "error": "<human readable error>" }
```

Environment Variables (required)  
 DEPLOYMENT_NAME             Azure model deployment name  
 AZURE_OPENAI_ENDPOINT       https://<resource>.openai.azure.com  
 AZURE_API_KEY               Azure OpenAI key  
 API_VERSION                 e.g. "2024-04-01-preview"  
 GITHUB_PERSONAL_ACCESS_TOKEN <token>  (used only for a Docker call)

Notes / Limitations  
 • UploadFile is fully read into memory; very large files will exhaust RAM.  
 • File content is truncated to 1 000 characters before being placed in the prompt (code comment: [file_content[:1000]…]).  
 • Uses langchain-community MultiServerMCPCClient to spin up two helper Python scripts in servers/. If these fail, the /chat call fails.  
 • As provided, imports “uvicorn” inside __main__, so launch with  
   `python backend/mcp_client_ai.py`  or  
   `uvicorn backend.mcp_client_ai:app --reload`

---
3. mcp_gamini_ai.py  ("Gemini Pro Agent")
-----------------------------------------
POST /chat
~~~~~~~~~
Description  
 Chat completion powered by Google Gemini Pro (via google-generative-ai SDK). No file-upload support.

Request  
 Content-Type: application/json  
 Body Schema   `{ "message": "<user text>" }`

Example  
```
curl -X POST http://localhost:8000/chat \
      -H 'Content-Type: application/json' \
      -d '{ "message": "Explain transformers in 3 sentences." }'
```

Successful Response  HTTP 200  
```json
{ "response": "<assistant-reply>" }
```

Failure Response  
```json
{ "error": "<human readable error>" }
```

Environment Variables (required)  
 GEMINI_API_KEY    Google Generative-AI API key  
 GEMINI_MODEL      (e.g. "gemini-1.5-pro-latest")  
 GITHUB_PERSONAL_ACCESS_TOKEN <token> (only for Docker run)

Notes / Limitations  
 • Uses custom GeminiLlm wrapper class built on top of google-generative-ai SDK + LangChain ChatModels.  
 • Launch with  
   `uvicorn backend.mcp_gamini_ai:app --reload`

---
4. Suggested Improvements
-------------------------
1. Version your API (e.g. prefix /v1/).  
2. Move chat_history into a DB or client-side memory to support multiple concurrent users.  
3. Return proper HTTP status codes (4xx for client errors, 5xx for server errors).  
4. Auto-generate docs: FastAPI already exposes /docs (Swagger) and /openapi.json; ensure both endpoints still work after refactor.  
5. Ensure secrets are read only once; avoid printing them via print(env) statements.  
6. mcp_client_ai: handle >1 000-char files via chunking or ask user to narrow scope.

---
END OF DOCUMENT
