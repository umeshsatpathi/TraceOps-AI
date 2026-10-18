"""Single, reusable FalkorDB connection for all TraceShield components.

Supports local Docker FalkorDB as well as managed FalkorDB Cloud instances
with authentication (username, password, SSL, or connection URL).
"""
import os
from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv()


def get_graph():
    """Create and return a connected FalkorDB graph instance."""
    url = os.getenv("FALKORDB_URL")
    if url:
        client = FalkorDB.from_url(url)
    else:
        kwargs = {
            "host": os.getenv("FALKORDB_HOST", "localhost"),
            "port": int(os.getenv("FALKORDB_PORT", "6379")),
        }
        username = os.getenv("FALKORDB_USERNAME")
        if username:
            kwargs["username"] = username
        password = os.getenv("FALKORDB_PASSWORD")
        if password:
            kwargs["password"] = password
        ssl_val = os.getenv("FALKORDB_SSL", "false").strip().lower()
        if ssl_val in ("true", "1", "yes"):
            kwargs["ssl"] = True
        client = FalkorDB(**kwargs)

    graph_name = os.getenv("FALKORDB_GRAPH", "traceshield")
    return client.select_graph(graph_name)
