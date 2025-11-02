"""
Skill registry for Nova AI
"""


class SkillRegistry:
    """Registry for managing and accessing skills"""
    
    def __init__(self):
        """Initialize the skill registry"""
        self.skills = {}
        self._load_skills()
    
    def _load_skills(self):
        """Load all available skills"""
        # Import and register skills
        try:
            from skills.file_manager import FileManagerSkill
            self.register_skill('file', FileManagerSkill())
        except ImportError as e:
            print(f"Warning: Could not load file_manager skill: {e}")
    
    def register_skill(self, name, skill):
        """
        Register a skill with the registry
        
        Args:
            name: Name to register the skill under
            skill: Skill instance to register
        """
        self.skills[name] = skill
        print(f"Registered skill: {name}")
    
    def get_skill(self, name):
        """
        Get a skill by name
        
        Args:
            name: Name of the skill to retrieve
            
        Returns:
            Skill instance or None if not found
        """
        return self.skills.get(name)
    
    def list_skills(self):
        """
        Get a list of all registered skills
        
        Returns:
            list: Names of all registered skills
        """
        return list(self.skills.keys())
