# Reverse Muse - MVP Implementation

**AI-powered reading companion with proactive insights**

A minimal yet intelligent MVP that uses "Theory of Mind" to provide context-aware insights while you read. The AI observes your behavior and surfaces relevant knowledge connections as elegant "ghost bubbles."

## 🎯 Core Concept

> **AI is not a passive Q&A tool — it's your "second brain" during reading.**

When you highlight text or linger on a complex formula, a subtle bubble appears:
- "This contradicts what you read in the ResNet paper..."
- "This reminds you of the transformer architecture from BERT..."

The magic: **Zero-friction, proactive, minimal.**

## 🏗️ Architecture

### Monorepo Structure

```
reverse-muse/
├── apps/
│   ├── backend/              # FastAPI backend (Python)
│   │   ├── app/
│   │   │   ├── core/         # Configuration, middleware
│   │   │   ├── routes/       # API endpoints
│   │   │   └── use_cases/   # Application layer orchestration
│   │   ├── domains/          # DDD Domain Layer
│   │   │   ├── reading_hub/      # Reading context & triggers
│   │   │   ├── memory_hub/       # Vector memory chunks
│   │   │   └── insight_hub/      # AI-generated insights
│   │   └── infrastructure/  # Database, external services
│   └── frontend/            # Next.js frontend (TODO)
├── packages/
│   ├── shared/              # Shared types and utilities
│   └── domain/             # Domain models (shared across layers)
└── docs/
    └── prd1.0.md          # Product Requirements Document
```

### DDD Layering

```
┌─────────────────────────────────────────────┐
│   Interface Layer (API / Frontend)        │
│   - FastAPI routes                      │
│   - Request/Response models               │
└─────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│   Application Layer (Use Cases)           │
│   - Orchestrate domain logic            │
│   - Coordinate repositories & services    │
└─────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│   Domain Layer                           │
│   - Entities (aggregate roots)            │
│   - Value Objects                        │
│   - Domain Services                      │
│   - Repository Interfaces (ports)         │
└─────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│   Infrastructure Layer                   │
│   - Database adapters (SurrealDB)        │
│   - LLM clients (OpenAI, Anthropic)     │
│   - Vector search (Pinecone/Chroma)      │
│   - PDF processing                      │
└─────────────────────────────────────────────┘
```

### Core Domains

| Domain | Entities | Services | Ports |
|---------|-----------|-----------|--------|
| **Reading Hub** | ReadingContext, UserAction, ReadingPosition | ReadingContextService | ReadingContextRepository |
| **Memory Hub** | MemoryChunk, MemoryMetadata | MemoryChunkService | MemoryChunkRepository |
| **Insight Hub** | BubbleInsight, InsightContext | InsightGenerationService | InsightRepository |

## 🚀 Quick Start

### Prerequisites

- Conda (Miniconda or Anaconda)
- Python 3.10+ (via conda)
- SurrealDB 1.0+
- Node.js 18+ (for frontend, when implemented)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd reverse-muse

# Create conda environment
conda create -n reverse-muse python=3.10 -y

# Activate conda environment
conda activate reverse-muse

# Install backend dependencies
pip install -e ".[backend,dev]"

# Or install from requirements.txt
pip install -r apps/backend/requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# At minimum, set:
# - OPENAI_API_KEY (or ANTHROPIC_API_KEY)
# - SURREALDB_URL
```

### Start SurrealDB

```bash
# Using Docker
docker run --rm -p 8001:8000 \
  -v $(pwd)/data/surrealdb:/data \
  surrealdb/surrealdb:latest \
  start --user root --pass root file:/data/database.db

# Or download locally from https://surrealdb.com/install
surreal start --user root --pass root --log debug
```

### Start Backend

```bash
# Development with auto-reload
python -m apps.backend.app.main

# Or using uvicorn directly
uvicorn apps.backend.app.main:app --reload --port 8000
```

### Verify

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

## 📚 API Endpoints

### Reading Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/reading/start` | Start a new reading session |
| `POST` | `/api/v1/reading/action` | Record user action (selection, linger) |

### Insights

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/insights/{context_id}` | Get insights for a reading context |

### Example Flow

```python
# 1. Start reading session
response = requests.post(
    "http://localhost:8000/api/v1/reading/start",
    json={
        "user_id": "user_123",
        "paper_id": "paper_456",
        "session_id": "session_789"
    }
)
context_id = response.json()["context_id"]

# 2. Record a text selection
response = requests.post(
    f"http://localhost:8000/api/v1/reading/action?context_id={context_id}",
    json={
        "trigger_type": "selection",
        "selected_text": "The attention mechanism...",
        "reading_position": {
            "paper_id": "paper_456",
            "page_number": 5,
            "text_snippet": "...attention..."
        }
    }
)

# Response may contain AI insight
if "insight" in response.json():
    print(f"AI says: {response.json()['insight']['content']}")
```

## 🎨 Design Patterns Used

### 1. Repository Pattern

```python
# Domain layer defines the interface
class ReadingContextRepository(ABC):
    @abstractmethod
    async def save(self, context: ReadingContext) -> None:
        pass

# Infrastructure layer implements it
class SurrealReadingContextRepository(ReadingContextRepository):
    async def save(self, context: ReadingContext) -> None:
        # SurrealDB implementation
        pass
```

### 2. Use Case Pattern

```python
# Application layer orchestrates business logic
class RecordUserActionUseCase:
    def __init__(
        self,
        context_repo: ReadingContextRepository,
        memory_repo: MemoryChunkRepository,
        insight_use_case: GenerateInsightUseCase,
    ):
        # Dependency injection
        pass

    async def execute(self, context_id: str, action: UserAction):
        # 1. Retrieve context
        # 2. Record action
        # 3. Search related memories
        # 4. Generate insight if applicable
        pass
```

### 3. Aggregate Root Pattern

```python
# ReadingContext owns UserActions and ReadingPosition
@dataclass
class ReadingContext:
    id: Optional[str] = None
    current_position: Optional[ReadingPosition] = None
    recent_actions: List[UserAction] = field(default_factory=list)

    def add_action(self, action: UserAction):
        """Enforce invariants"""
        self.recent_actions.append(action)
        if len(self.recent_actions) > 10:
            self.recent_actions = self.recent_actions[-10:]
```

## 🔧 Configuration

### Environment Variables

```env
# Project
PROJECT_NAME=Reverse Muse
ENVIRONMENT=development
DEBUG=true

# Database
SURREALDB_URL=ws://localhost:8001/rpc
SURREALDB_NAMESPACE=reverse_muse
SURREALDB_DATABASE=main
SURREALDB_USER=root
SURREALDB_PASS=root

# LLM
OPENAI_API_KEY=sk-your-key
DEFAULT_LLM_MODEL=gpt-4o-mini

# Embedding
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small
SIMILARITY_THRESHOLD=0.85

# AI Bubble
LINGER_THRESHOLD_SECONDS=5
LINGER_CONFIDENCE_THRESHOLD=0.8
MAX_BUBBLE_LENGTH=200
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps/backend --cov-report=html

# Run specific test
pytest apps/backend/tests/unit/test_reading_context.py::test_create_context
```

## 📦 Tech Stack

- **Backend Framework**: FastAPI
- **Database**: SurrealDB (multi-model, supports vectors)
- **LLM**: OpenAI / Anthropic / Ollama
- **Embeddings**: OpenAI text-embedding-3-small
- **PDF Processing**: PyMuPDF
- **Python Version**: 3.10+
- **Architecture**: DDD + Clean Architecture

## 🎯 MVP Scope

The current implementation includes:

✅ **Domain Layer**: Complete entity and service definitions
✅ **Application Layer**: Use cases for core operations
✅ **Infrastructure Layer**: SurrealDB repository implementations
✅ **API Layer**: FastAPI routes for reading sessions and actions
✅ **Configuration**: Environment-based configuration with Pydantic

### TODO for Production:

- [ ] LLM integration (OpenAI / Anthropic clients)
- [ ] Vector search implementation
- [ ] PDF upload and chunking pipeline
- [ ] Frontend (Next.js + React PDF viewer)
- [ ] WebSocket support for real-time bubble updates
- [ ] Authentication & user management
- [ ] Comprehensive test coverage
- [ ] Docker deployment configuration

## 🔄 Code Style

- **Linting**: `ruff check .`
- **Formatting**: `black .`
- **Type Checking**: `mypy apps/backend`

## 📝 Development Workflow

1. **Add a new feature**:
   - Define entities in `apps/backend/domains/*/core/entities.py`
   - Add domain services in `apps/backend/domains/*/services/`
   - Create repository interface in `apps/backend/domains/*/port/`
   - Implement repository in `apps/backend/infrastructure/db/`
   - Create use case in `apps/backend/app/use_cases/`
   - Expose via API in `apps/backend/app/routes/`

2. **Run tests**:
   ```bash
   pytest apps/backend/tests
   ```

3. **Format code**:
   ```bash
   black . && ruff check --fix .
   ```

## 📄 License

MIT License

## 🙏 Acknowledgments

- Reference project: [llm-paper-reader](https://github.com/zhangjunmengyang/llm_paper_reader) - Used as pattern reference for DDD structure
- DDD concepts from [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- Architecture inspired by Clean Architecture principles

---

**Built with ❤️ using Domain-Driven Design principles**
