# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Start the application:**
```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

**Install dependencies:**
```bash
uv sync
```

**Environment setup:**
- Copy `.env.example` to `.env` 
- Set `ANTHROPIC_API_KEY=your_key_here`

## Architecture Overview

This is a **Retrieval-Augmented Generation (RAG) system** for querying course materials using semantic search and AI responses.

### Core Architecture Pattern
The system follows a **tool-augmented RAG pattern** where the AI uses structured tools to search course content, rather than traditional RAG retrieval-then-generate.

```
User Query → FastAPI → RAG System → AI Generator → Search Tools → Vector Store
                                        ↓
                        Claude API with tool definitions
```

### Key Components

**RAG System (`rag_system.py`)** - Main orchestrator that:
- Coordinates between AI generator, vector store, and search tools
- Manages conversation sessions and history
- Handles tool-based search workflow

**AI Generator (`ai_generator.py`)** - Claude API interface that:
- Uses structured system prompts with tool definitions
- Handles tool execution workflow via `tool_manager`
- Manages conversation context and history

**Vector Store (`vector_store.py`)** - ChromaDB wrapper with dual collections:
- `course_catalog` - Course metadata for name resolution
- `course_content` - Actual course content chunks
- Semantic search with filtering by course/lesson

**Search Tools (`search_tools.py`)** - Tool-based search system:
- `CourseSearchTool` - Implements Anthropic tool interface
- Enables AI to perform structured searches with parameters
- Tracks sources for response attribution

**Document Processor (`document_processor.py`)** - Text processing:
- Extracts course structure (title, lessons) from raw text
- Chunks content with sentence-aware splitting
- Creates `Course` and `CourseChunk` objects

### Data Flow Architecture

1. **Document Loading** (`startup_event`): Course files → Document Processor → Vector Store
2. **Query Processing**: User input → RAG System → AI Generator → Search Tools → Vector Store
3. **Response Generation**: Search results → AI synthesis → Session history update

### Configuration System

**Config (`config.py`)** - Centralized settings using dataclass:
- API keys and model selection
- Chunk sizes and overlap for text processing  
- Vector store paths and search limits
- Session management parameters

### Session Management

**SessionManager (`session_manager.py`)** - Conversation context:
- Maintains chat history per session
- Configurable history length (`MAX_HISTORY`)
- Enables multi-turn conversations with context

## Key Design Patterns

**Tool-Augmented RAG**: AI uses structured tools rather than direct vector search
**Dual Vector Collections**: Separate metadata and content for flexible querying
**Session-Based Context**: Conversation history maintained across queries
**Configurable Processing**: Centralized config for all processing parameters
- Always use uv to run the server, do don't use pip directly.
- make sure to use uv to manage all dependencies
- use uv to run python files