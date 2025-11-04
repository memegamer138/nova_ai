"""Skill registry and helpers.

This module stores registered skill callables along with optional metadata
such as required permissions and a short description.

API highlights:
- register_skill(intent_name, permissions=None, overwrite=False, description=None)
  -> decorator used by skill modules to register handlers
- get_skill(intent_name) -> callable or None
- get_skill_meta(intent_name) -> metadata dict or None
- list_skills() -> dict of intent -> metadata
- unregister_skill(intent_name) -> remove registration
"""

from typing import Callable, Dict, Optional, Set
import logging

logger = logging.getLogger(__name__)

# Internal registry structure: intent -> metadata dict
# metadata keys: func (callable), permissions (set), description (str)
SKILL_REGISTRY: Dict[str, Dict] = {}


def register_skill(intent_name: str, *, permissions: Optional[Set[str]] = None, overwrite: bool = False, description: Optional[str] = None):
    """Decorator to register a skill function with optional metadata.

    Args:
        intent_name: canonical name of the intent (string)
        permissions: optional set of permission strings required to run this skill
        overwrite: if True, allow replacing an existing registration
        description: optional short text describing the skill

    Usage:
        @register_skill('create_file', permissions={'file'})
        def create_file(...):
            ...
    """
    perms = set(permissions) if permissions else set()

    def decorator(func: Callable):
        if intent_name in SKILL_REGISTRY and not overwrite:
            msg = f"Intent '{intent_name}' is already registered. Use overwrite=True to replace."
            logger.error(msg)
            raise ValueError(msg)

        SKILL_REGISTRY[intent_name] = {
            "func": func,
            "permissions": perms,
            "description": description or "",
        }
        logger.info("Registered skill '%s' (permissions=%s)", intent_name, perms)
        return func

    return decorator


def get_skill(intent_name: str) -> Optional[Callable]:
    """Retrieve the skill callable for an intent, or None."""
    meta = SKILL_REGISTRY.get(intent_name)
    return meta.get("func") if meta else None


def get_skill_meta(intent_name: str) -> Optional[Dict]:
    """Return metadata dict for the intent, or None if not registered."""
    return SKILL_REGISTRY.get(intent_name)


def list_skills() -> Dict[str, Dict]:
    """Return a shallow copy of the registry (intent -> metadata)."""
    return {k: v.copy() for k, v in SKILL_REGISTRY.items()}


def unregister_skill(intent_name: str) -> bool:
    """Remove a registered intent. Returns True if removed, False if not found."""
    if intent_name in SKILL_REGISTRY:
        del SKILL_REGISTRY[intent_name]
        logger.info("Unregistered skill '%s'", intent_name)
        return True
    logger.debug("Tried to unregister unknown skill '%s'", intent_name)
    return False


def required_permissions(intent_name: str) -> Set[str]:
    """Return the set of permissions required by the intent (empty set if none)."""
    meta = SKILL_REGISTRY.get(intent_name)
    if not meta:
        return set()
    return set(meta.get("permissions") or set())
