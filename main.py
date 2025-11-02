"""
Nova AI - Main Entry Point
"""
from core.engine import Engine
from core.registry import SkillRegistry


def main():
    """Main function to run Nova AI"""
    # Initialize skill registry
    registry = SkillRegistry()
    
    # Initialize engine
    engine = Engine(registry)
    
    # Start the engine
    engine.run()


if __name__ == "__main__":
    main()
