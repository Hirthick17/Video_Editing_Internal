"""Hirthick's Vision Studio - Backend Foundation & Orchestration Core."""

# Compatibility shim for LangChain 1.x / LangChain-Core 0.3.x global flags
try:
    import langchain
    if not hasattr(langchain, "debug"):
        langchain.debug = False
    if not hasattr(langchain, "verbose"):
        langchain.verbose = False
    if not hasattr(langchain, "llm_cache"):
        langchain.llm_cache = None
except ImportError:
    pass

__version__ = "0.1.0"
