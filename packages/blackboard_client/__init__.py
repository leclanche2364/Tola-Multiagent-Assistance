"""Shared Blackboard client for the four-agent system.

Supabase-first writes with a local SQLite outbox as fallback.
Stdlib only. The client never reads env files; callers pass
credentials explicitly.
"""

from .client import BlackboardClient, ALLOWED_TABLES

__all__ = ["BlackboardClient", "ALLOWED_TABLES"]