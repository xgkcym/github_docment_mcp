import hashlib
import time

import requests

from core.settings import settings
from utils.logger_handler import logger


class NiuTrans:
    """翻译服务"""
    def __init__(self):
        self.url = settings.niu_trans_url

    def __language_identification__(self,text:str):
        """根据文本内容自动识别语言并进行目标翻译"""
        data = {
            "from":"auto",
            "to":settings.niu_trans_to,
            "appId":settings.niu_trans_appId,
            "timestamp":round(time.time() * 1000),
            "srcText": text,
        }
        try:
            auth_str = self.__generate_auth_str__(data)
            data['authStr'] = auth_str
            result = requests.post(self.url, data=data)
            text = result.json().get("tgtText", text)
            return text
        except Exception as e:
            raise  e

    def identification(self,text:str)->str:
        docs: list[str] = text.split("\n\n")
        result = ""
        i = 0
        try :
            while i < len(docs):
                j = 1
                while len("\n\n".join(docs[i:i + j])) < 3000 and i + j < len(docs):
                    j += 1
                result += self.__language_identification__("\n\n".join(docs[i:i + j]))
                i += j
            logger.info(f"[翻译成功] 翻译后的文本: {result}")
            return  result
        except Exception as e:
            logger.error(f"[翻译失败] 错误信息: {str(e)}")
            raise Exception(f"[翻译失败] 错误信息: {str(e)}") from e

    def __generate_auth_str__(self,params):
        sorted_params = sorted(list(params.items()) + [('apikey', settings.niu_trans_api_key)], key=lambda x: x[0])
        param_str = '&'.join([f'{key}={value}' for key, value in sorted_params])
        md5 = hashlib.md5()
        md5.update(param_str.encode('utf-8'))
        auth_str = md5.hexdigest()
        return auth_str


def create_translate():
    return NiuTrans()


if  __name__ == '__main__':
    translate = create_translate()
    text = """# CLAUDE.md\n\nThis file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.\n\n## Repository Overview\n\nThis is a comprehensive collection of practical LLM-powered application examples, tutorials, and recipes organized by complexity and use case. The repository contains 70+ example projects demonstrating various AI frameworks and patterns.\n\n## Project Categories\n\nProjects are organized into six main categories:\n\n1. **starter_ai_agents/** - Quick-start boilerplate examples for learning different AI frameworks (Agno, OpenAI SDK, LlamaIndex, CrewAI, PydanticAI, LangChain, AWS Strands, Camel AI, DSPy, Google ADK)\n2. **simple_ai_agents/** - Straightforward, single-purpose agents (finance tracking, web automation, newsletter generation, calendar scheduling, etc.)\n3. **mcp_ai_agents/** - Projects using Model Context Protocol for semantic RAG, database interactions, and external tool integrations\n4. **memory_agents/** - Agents with persistent memory capabilities using frameworks like GibsonAI Memori\n5. **rag_apps/** - Retrieval-Augmented Generation examples with vector databases and document processing\n6. **advance_ai_agents/** - Complex multi-agent workflows and production-ready applications (research agents, job finders, meeting assistants, etc.)\n7. **course/** - Structured learning materials, including the complete AWS Strands course (8 lessons)\n\n## Common Development Commands\n\n### Running Individual Projects\n\nEach project is self-contained with its own dependencies. Navigate to the specific project directory first:\n\n```bash\ncd <category>/<project_name>\n```\n\n### Installing Dependencies\n\nProjects use either `requirements.txt` or `pyproject.toml`:\n\n```bash\n# For requirements.txt projects\npip install -r requirements.txt\n\n# For pyproject.toml projects (newer projects)\npip install -e .\n# or with uv (preferred for faster installs)\nuv pip install -e .\n```\n\n### Running Projects\n\nMost projects use simple Python execution:\n\n```bash\npython main.py\n# or\npython app.py\n```\n\nSome projects (especially RAG and advanced agents) use Streamlit:\n\n```bash\nstreamlit run app.py\n```\n\n### Environment Configuration\n\nAll projects require environment variables for API keys. Each project has a `.env.example` file. Copy it to `.env` and add your keys:\n\n```bash\ncp .env.example .env\n# Then edit .env with your API keys\n```\n\nCommon API keys used across projects:\n- `NEBIUS_API_KEY` - Nebius Token Factory inference provider (used extensively)\n- `OPENAI_API_KEY` - OpenAI models\n- `GITHUB_PERSONAL_ACCESS_TOKEN` - For GitHub MCP agents\n- `SGAI_API_KEY` - ScrapeGraph AI for web scraping agents\n- `MEMORI_API_KEY` - GibsonAI Memori for memory-enabled agents\n\n## High-Level Architecture\n\n### Multi-Stage Workflow Pattern\n\nAdvanced agents (in `advance_ai_agents/`) typically use a multi-stage workflow pattern with specialized sub-agents:\n\n```python\nclass ResearchWorkflow(Workflow):\n    searcher: Agent  # Gathers information\n    analyst: Agent   # Analyzes findings\n    writer: Agent    # Produces final output\n```\n\nExample: `advance_ai_agents/deep_researcher_agent/agents.py`\n\n### MCP Integration Pattern\n\nMCP agents use the Model Context Protocol to integrate external tools:\n\n```python\nasync with MCPServerStdio(\n    params={\n        "command": "npx",\n        "args": ["-y", "@modelcontextprotocol/server-github"],\n        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ["TOKEN"]}\n    }\n) as server:\n    agent = Agent(mcp_servers=[server], ...)\n```\n\nExample: `mcp_ai_agents/github_mcp_agent/main.py`, `mcp_ai_agents/mcp_starter/main.py`\n\n### Framework-Specific Patterns\n\n**Agno Framework** (most common):\n- Uses `Agent` class with tools, model, and instructions\n- Supports workflow orchestration via `Workflow` class\n- Examples: `starter_ai_agents/agno_starter/`, `advance_ai_agents/deep_researcher_agent/`\n\n**OpenAI Agents SDK**:\n- Uses async `Runner.run()` with agents\n- Examples: `starter_ai_agents/openai_agents_sdk/`, `mcp_ai_agents/mcp_starter/`\n\n**AWS Strands**:\n- Complete course available in `course/aws_strands/`\n- Covers basic agents, session management, MCP, multi-agent patterns, observability, and guardrails\n\n**LangChain/LangGraph**:\n- Graph-based workflows with state management\n- Examples: `starter_ai_agents/langchain_langgraph_starter/`\n\n## Contributing Guidelines\n\n### Adding New Projects\n\n1. Create an issue describing the project first\n2. Submit ONE project per Pull Request\n3. Place in appropriate category folder (see `CONTRIBUTING.md:46-52`)\n4. Use snake_case naming (e.g., `finance_agent`, `blog_writing_agent`)\n5. Must include a `README.md` following the template in `.github/README_TEMPLATE.md`\n6. Include either `requirements.txt` or `pyproject.toml` (pyproject.toml preferred)\n7. Provide `.env.example` file - never commit secrets\n8. Use code formatter (Black or Ruff) for consistent style\n\n### Project README Requirements\n\nEach project README must include:\n- Clear description of what the agent does\n- Prerequisites (Python version, required API keys)\n- Installation steps\n- Usage instructions with example queries/commands\n- Technical details (frameworks used, models)\n\n## AWS Strands Course Structure\n\nLocated in `course/aws_strands/`, this is an 8-lesson progressive course:\n\n1. **01_basic_agent** - First agent with simple tools\n2. **02_session_management** - Persistent conversations and state\n3. **03_structured_output** - Extract structured data with Pydantic\n4. **04_mcp_agent** - External tool integration via MCP\n5. **05_human_in_the_loop_agent** - Request human input/approval\n6. **06_multi_agent_pattern/** - Advanced multi-agent systems\n   - `06_1_agent_as_tools` - Orchestrator with specialized agents\n   - `06_2_swarm_agent` - Dynamic agent handoffs\n   - `06_3_graph_agent` - Graph-based workflows\n   - `06_4_workflow_agent` - Sequential pipelines\n7. **07_observability** - OpenTelemetry and Langfuse monitoring\n8. **08_guardrails** - Safety measures and content filtering\n\nEach lesson builds on the previous, with complete working examples.\n\n## Key Technical Notes\n\n- **Python Version**: Requires Python 3.10 or higher (specified in most pyproject.toml files)\n- **Primary AI Provider**: Nebius Token Factory is used extensively across examples for inference\n- **Dependency Management**: Newer projects use `uv` for faster package installation\n- **MCP Tools**: Many agents integrate with external services via MCP (GitHub, databases, custom servers)\n- **Streaming UI**: Streamlit is the standard for web-based agent interfaces\n- **Memory Systems**: GibsonAI Memori is the primary memory provider for context retention\n- **Web Scraping**: ScrapeGraph AI is used for intelligent web data extraction\n\n## Common Frameworks by Category\n\n- **Starter**: Agno, OpenAI SDK, LlamaIndex, CrewAI, PydanticAI, LangChain, AWS Strands, Camel AI, DSPy, Google ADK\n- **Simple**: Agno (most common), Mastra AI, browser-use\n- **MCP**: OpenAI SDK, AWS Strands, custom MCP servers\n- **Memory**: Agno with GibsonAI Memori, AWS Strands with Memori\n- **RAG**: LlamaIndex, LangChain, Agno, CrewAI with Qdrant/vector stores\n- **Advanced**: Agno workflows, CrewAI multi-agent, Google ADK, FastAPI services\n'
    """
    res = translate.identification(text=text)
    print(res)