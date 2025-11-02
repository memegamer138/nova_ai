# core/registry.py

SKILL_REGISTRY = {}

def register_skill(intent_name):
    """Decorator to register a skill function."""
    def decorator(func):
        SKILL_REGISTRY[intent_name] = func
        return func
    return decorator

def get_skill(intent_name):
    """Retrieve a skill function by intent."""
    return SKILL_REGISTRY.get(intent_name)
