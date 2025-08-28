"""
Authentication module for Dell Switch Port Tracer

Contains authentication handlers including NT domain integration
and basic HTTP authentication.
"""

from .auth import verify_user, get_user_permissions, require_role
from .nt_auth import WindowsAuthenticator

__all__ = ["verify_user", "get_user_permissions", "require_role", "WindowsAuthenticator"]
