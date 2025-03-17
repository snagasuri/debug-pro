# Deebo: Autonomous Debugging Assistant

## 1. The Problem

Modern software development is increasingly complex, and developers spend countless hours debugging issues that range from simple syntax errors to complex runtime failures. Key challenges include:
- **Time-Consuming Debugging**: Manual debugging requires reading lengthy logs, reproducing issues, and applying fixes trial-and-error style.
- **Context Overload**: Large codebases and frequent changes make it difficult for developers (and even LLM-based tools) to maintain full context, leading to redundant or incorrect fixes.
- **Environment Inconsistencies**: Debugging issues often behave differently in development, staging, and production, making isolation of problems difficult.
- **Lack of Automation**: Many debugging tools require manual intervention or incomplete automation that does not scale well with complex projects.

## 2. How Deebo Solves It

Deebo is an autonomous debugging assistant that streamlines the debugging process by automating error diagnosis and fix generation. Here's how it addresses the problem:

- **Automated Code Ingestion & Diffing**: Deebo ingests an entire codebase (or just the diffs from previous versions) to build a precise snapshot of the project. This reduces redundant analysis by updating only what has changed.
- **Isolated Execution via Docker**: By spinning up Docker containers on-demand, Deebo creates a controlled environment where the code is executed exactly as it would in production. This isolation allows it to capture real-time logs, errors, and stack traces without polluting the developer's local environment.
- **LLM-Powered Debugging Analysis**: Leveraging an advanced language model (e.g., Claude 3.7), Deebo analyzes execution outputs to generate debugging hypotheses, propose fixes, and provide detailed explanations with confidence scores.
- **Agentic Debugging Workflow**: Initially simplified into a single debugging agent, the design anticipates future expansion into multiple "scenario agents" (each testing different fixes) overseen by a "mother agent" that selects the best solution. This structured, autonomous decision-making significantly reduces the manual burden on developers.
- **Composable Core API**: The entire debugging pipeline is built as a modular API. This design allows it to be integrated as:
  - A lightweight MCP server for Cline (and other AI coding assistants) to call.
  - A standalone web or desktop application via a simple API wrapper.
  - A reusable backend service that can evolve independently of the front end.

## 3. Technical Architecture

### Core Components

- **Code Ingestion Module**: Handles storing and managing code snapshots with features including:
  - Efficient diff calculation between versions
  - Metadata extraction (language detection, complexity metrics)
  - Optimized storage with memory/disk caching
  - Session management with version history
  - File filtering and validation
- **Docker Manager Module**: Manages the lifecycle of Docker containers used to execute code. This module is responsible for spawning containers with the required environment, injecting the latest codebase into the container, and cleaning up containers after execution.
- **Execution Module**: Executes commands (e.g., running tests) inside the Docker container and captures execution results (logs, errors, stack traces).
- **Debug Analysis Module**: Uses an LLM (e.g., Claude 3.7) to analyze execution outputs and generate a DebugReport, which includes proposed fixes, detailed explanations, and confidence scores indicating the likelihood of success.
- **Orchestrator**: Ties all modules together into an end-to-end debugging workflow. It manages code ingestion, Docker container management, command execution, debug analysis, and resource cleanup.

### Tech Stack

- **Backend Framework**: FastAPI with Python
- **Containerization**: Docker (using Docker SDK for Python)
- **Authentication & Database**: Supabase
- **Language Model Integration**: Claude 3.7 (or similar)
- **Testing**: pytest

## 4. Project Setup

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Supabase account (for authentication and database)
- Claude API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/debug-pro.git
cd debug-pro
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env file with your configuration values
```

4. Run the application:
```bash
uvicorn main:app --reload
```

5. With Docker:
```bash
docker-compose up -d
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

### Main Endpoints

- `POST /api/v1/debug`: Create a new debugging session
- `GET /api/v1/debug/{session_id}`: Get the status of a debugging session
- `POST /api/v1/debug/{session_id}/continue`: Continue an existing debugging session
- `POST /api/v1/debug/{session_id}/apply-fix`: Apply a proposed fix to the codebase

## Project Structure

```
debug-pro/
├── app/                       # Core application
│   ├── api/                   # API endpoints
│   ├── core/                  # Core configuration
│   ├── db/                    # Database models
│   ├── modules/               # Core modules
│   │   ├── code_ingestion/    # Code snapshot handling
│   │   ├── docker_manager/    # Docker container management
│   │   ├── execution/         # Command execution
│   │   ├── debug_analysis/    # LLM-powered analysis
│   │   └── orchestrator/      # Debug workflow coordination
│   └── schemas/               # Data models
├── tests/                     # Test suite
├── main.py                    # Application entry point
├── Dockerfile                 # For containerizing the API
├── docker-compose.yml         # For local development
└── requirements.txt           # Python dependencies
```

## Development

### Running Tests

```bash
pytest
```

### Code Style

We follow PEP 8 style guidelines. You can check your code with:

```bash
flake8
```

## 5. Benefits & Future Enhancements

### Immediate Benefits

- **Efficiency Gains**: Automated debugging reduces the time spent on manual error diagnosis and trial-and-error fixes.
- **Isolation & Consistency**: Docker ensures that code execution is reproducible and isolated, reducing environment-related issues.
- **Cost-Effective Debugging**: Incremental codebase caching and diffing minimize redundant processing and save on resources.
- **Improved Developer Productivity**: Detailed, LLM-generated debugging reports provide actionable insights and fix recommendations.

### Future Enhancements

- **Multi-Agent Debugging**: Expand the simplified agent system to include multiple scenario agents, each exploring different fixes concurrently, with a mother agent to choose the best outcome.
- **MCP Server Integration**: Wrap the core API with a lightweight MCP interface for seamless integration with Cline and other platforms.
- **Enhanced Diffing & Caching**: Develop sophisticated algorithms for code versioning and diff management to handle larger projects more efficiently.
- **User Feedback Loop**: Integrate real-time feedback mechanisms to refine debugging suggestions based on developer input.
- **Extensible UI**: Build a web or desktop application interface for a more interactive debugging experience.

## License

[MIT License](LICENSE)
