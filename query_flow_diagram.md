# RAG System Query Flow Diagram

```
┌─────────────────┐
│   FRONTEND      │
│  (script.js)    │
└─────────────────┘
         │
         │ 1. User types query
         │ sendMessage()
         ▼
┌─────────────────┐
│  POST /api/query│
│  {              │
│   query: string │
│   session_id    │
│  }              │
└─────────────────┘
         │
         │ 2. HTTP Request
         ▼
┌─────────────────┐
│    FASTAPI      │
│   (app.py:56)   │
│                 │
│ query_documents │
│   endpoint      │
└─────────────────┘
         │
         │ 3. Create session if needed
         │ session_manager.create_session()
         ▼
┌─────────────────┐
│   RAG SYSTEM    │
│ (rag_system.py) │
│                 │
│ query() method  │
└─────────────────┘
         │
         │ 4. Get conversation history
         │ session_manager.get_conversation_history()
         ▼
┌─────────────────┐
│  AI GENERATOR   │
│(ai_generator.py)│
│                 │
│generate_response│
└─────────────────┘
         │
         │ 5. Claude API call with tools
         ▼
┌─────────────────┐
│  CLAUDE API     │
│                 │
│ Processes query │
│ with tools      │
└─────────────────┘
         │
         │ 6. Uses search tool
         ▼
┌─────────────────┐
│ COURSE SEARCH   │
│     TOOL        │
│(search_tools.py)│
└─────────────────┘
         │
         │ 7. Semantic search
         ▼
┌─────────────────┐
│  VECTOR STORE   │
│(vector_store.py)│
│                 │
│   ChromaDB      │
└─────────────────┘
         │
         │ 8. Returns relevant chunks
         ▼
┌─────────────────┐
│    RESPONSE     │
│   ASSEMBLY      │
│                 │
│ AI + Sources    │
└─────────────────┘
         │
         │ 9. Update conversation history
         │ session_manager.add_exchange()
         ▼
┌─────────────────┐
│   API RESPONSE  │
│  QueryResponse  │
│  {             │
│   answer: str   │
│   sources: []   │
│   session_id    │
│  }             │
└─────────────────┘
         │
         │ 10. JSON Response
         ▼
┌─────────────────┐
│   FRONTEND      │
│   DISPLAY       │
│                 │
│ • Show answer   │
│ • Show sources  │
│ • Update UI     │
└─────────────────┘
```

## Key Components:

**Frontend Layer:**
- User interface (HTML/CSS/JS)
- Handles user input and display

**API Layer:**
- FastAPI endpoints
- Request/response handling
- Error management

**RAG Orchestration:**
- Coordinates all components
- Manages session state
- Handles tool integration

**AI Processing:**
- Claude API integration
- Tool-aware response generation
- Context management

**Search & Retrieval:**
- Semantic search via ChromaDB
- Course content indexing
- Source attribution

**Session Management:**
- Conversation history
- Context preservation
- Multi-turn dialogue support

## Data Flow:
1. **Input**: User query → API request
2. **Processing**: RAG system → AI generation → Tool search
3. **Retrieval**: Vector database → Relevant content
4. **Generation**: AI response with sources
5. **Output**: Structured response → UI display