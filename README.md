# Puzzle Generator

A web-based application for generating, creating, editing, and visualizing tactical turn-based strategy puzzles. Built with FastAPI, LangGraph, and modern LLM integration. Create interactive puzzle maps with nodes, edges, and unit paths via manual editing or AI-powered chat and form generation.

## Features

### Core Functionality
- **Puzzle Generation**: AI-powered generation using multiple LLM providers (OpenAI, Google Gemini)
- **Manual Puzzle Creation**: Visual editor with nodes, edges, unit paths, game mode, and coins
- **Puzzle Visualization**: Interactive SVG editor with zoom, pan, playback, and path highlighting
- **Interactive Chat**: Conversational AI assistant that helps create and modify puzzles via natural language; streaming responses with markdown formatting
- **Puzzle Management**: Create, read, update, and delete puzzles with persistent storage
- **Session Management**: Multi-session chat with sidebar; puzzle context stored in agent state

### Technical Features
- **LangGraph Agent**: State-based agent (intent → chat / collect_info / collect_and_create / modify_puzzle → format_response)
- **Streaming Chat**: Server-sent streaming with reasoning block and final answer; thinking indicator in UI
- **HTMX + Fetch**: Dynamic UI (sidebar, editor partial) and custom fetch-based streaming for chat
- **Multi-LLM Support**: Switch models in chat and on generate form

## Tech Stack

### Backend
- **FastAPI**: Web framework
- **SQLAlchemy**: ORM (SQLite)
- **LangGraph**: Agent orchestration (async checkpointer)
- **LangChain**: LLM integration
- **Pydantic**: Validation and settings

### Frontend
- **Jinja2**: Server-side templates
- **HTMX**: Partial updates (sidebar, editor)
- **JavaScript**: Chat streaming (`script.js`), puzzle editor (`editor.js`), generate form (`generate_puzzle.js`)
- **SVG**: Puzzle canvas in editor
- **CSS**: Dark theme (`style.css`)

### LLM Providers
- OpenAI (e.g. GPT-4o-mini, GPT-4.1-mini)
- Google Gemini (3 Pro, 3 Flash, 2.5 Pro/Flash, 2.0 Flash, etc.)

## Project Structure

```
Puzzle-Generator/
├── app/
│   ├── agents/             # LangGraph agents
│   │   ├── chat_agent.py   # Main chat agent (streaming, puzzle state)
│   │   └── agent_tools.py  # Generate, update, serialize puzzles
│   ├── core/
│   │   ├── config.py       # Settings (e.g. checkpoints URL)
│   │   └── database.py     # SQLAlchemy engine and session
│   ├── llm/
│   │   ├── openai_client.py
│   │   ├── gemini_client.py
│   │   └── llm_manager.py
│   ├── models/             # SQLAlchemy models
│   │   ├── puzzle_model.py
│   │   ├── node_model.py
│   │   ├── edge_model.py
│   │   ├── unit_model.py
│   │   ├── path_model.py
│   │   ├── path_nodes.py
│   │   ├── session_model.py
│   │   └── ...
│   ├── prompts/
│   │   ├── prompt_manager.py
│   │   └── prompt_game_rules.py
│   ├── routers/
│   │   ├── puzzle_routers.py
│   │   └── chat_routers.py
│   ├── schemas/            # Pydantic schemas
│   ├── services/
│   │   ├── puzzle_services.py
│   │   └── session_services.py
│   ├── static/
│   │   ├── editor.js       # Puzzle editor (create/update, export)
│   │   ├── script.js       # Chat form, streaming, thinking indicator
│   │   ├── generate_puzzle.js
│   │   └── style.css
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── chat.html
│   │   ├── create-puzzle.html
│   │   ├── update-puzzle.html
│   │   ├── generate-puzzle.html
│   │   ├── puzzles.html
│   │   └── partials/
│   │       ├── editor_partial.html
│   │       └── chat_sidebar_items.html
│   └── main.py
├── data/                   # SQLite DB (if used)
├── images/
│   └── ux_flow.png
├── utils/
│   └── logger_config.py
├── requirements.txt
└── README.md
```

## Setup & Run

1. **Create and activate a virtual environment** (e.g. `.venv`).
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Environment**: Configure `.env` if needed (e.g. LLM API keys, `CHECKPOINTS_URL` for LangGraph checkpointer).
4. **Run**: `uvicorn app.main:app --reload` (default: http://127.0.0.1:8000)

## Usage

### Chat (create & modify puzzles)
1. Go to **`/puzzles/chat`**.
2. Start a new session or pick one from the sidebar.
3. Describe what you want (e.g. "Create a skirmish puzzle with 10 nodes and 3 enemy units" or "Change the puzzle so the player has one more unit").
4. The agent classifies intent, uses tools (generate, update, etc.), and answers; the integrated editor shows or updates the puzzle.

### Generate via form
1. Go to **`/puzzles/generate`**.
2. Set name, model, game mode, node/edge/turn counts, and units.
3. Submit; the generated puzzle is saved and you are redirected to its page.

### Manual create / edit
1. **Create**: `/puzzles/create-puzzle` — use the editor (nodes, edges, units, game mode, coins), then save.
2. **Edit**: `/puzzles/{puzzle_id}/update` — same editor, then update.
3. From chat, the right-hand panel loads the editor partial for the current session's puzzle.

### List & delete
- **List**: `/puzzles`
- **Puzzle page**: `/puzzles/{puzzle_id}`
- **Delete**: via UI on list or API.

## API Endpoints

### Puzzles
- `GET /puzzles` — List puzzles (optional filters).
- `GET /puzzles/{puzzle_id}` — Redirect to puzzle page.
- `GET /puzzles/{puzzle_id}/data` — Puzzle JSON for editor.
- `GET /puzzles/{puzzle_id}/update` — Edit puzzle page.
- `POST /puzzles` — Create puzzle (JSON body).
- `PUT /puzzles/{puzzle_id}` — Update puzzle (JSON body).
- `DELETE /puzzles/{puzzle_id}/delete` — Delete puzzle.

### Chat
- `GET /puzzles/chat` — Chat page (sessions list).
- `GET /puzzles/chat/editor` — Editor partial (optional `session_id`).
- `GET /puzzles/chat/sidebar` — Sidebar partial.
- `GET /puzzles/chat/{session_id}` — Session messages (HTML).
- `GET /puzzles/chat/puzzle/{puzzle_id}` — Chat page for that puzzle's session.
- `POST /puzzles/chat` — Send message (JSON); streaming response.
- `DELETE /puzzles/chat/{session_id}/delete` — Delete session.

## LangGraph Agent

- **State**: messages, user_intent, collected_info, current_puzzle_id, tool_result, puzzle (serialized JSON), model, session_id.
- **Nodes**: intent → chat | collect_info | collect_and_create | modify_puzzle → format_response → END.
- **Streaming**: Reasoning block + final answer; final text is replaced by markdown-rendered HTML at the end of the stream.
- **Puzzle context**: Incoming `puzzle_json` from the router is merged into state so the agent always has the current puzzle for chat/modify.

## Game Rules

See `app/prompts/prompt_game_rules.py` for rules used in prompts and validation.
