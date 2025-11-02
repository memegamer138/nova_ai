"""
Command parser and dispatcher for Nova AI
"""


class Engine:
    """Main engine for parsing commands and dispatching to skills"""
    
    def __init__(self, registry):
        """
        Initialize the engine with a skill registry
        
        Args:
            registry: SkillRegistry instance containing registered skills
        """
        self.registry = registry
        self.running = False
    
    def parse_command(self, command):
        """
        Parse a command string into skill and arguments
        
        Args:
            command: Command string from user
            
        Returns:
            tuple: (skill_name, arguments)
        """
        parts = command.strip().split(maxsplit=1)
        if not parts:
            return None, None
        
        skill_name = parts[0]
        arguments = parts[1] if len(parts) > 1 else ""
        
        return skill_name, arguments
    
    def dispatch(self, skill_name, arguments):
        """
        Dispatch a command to the appropriate skill
        
        Args:
            skill_name: Name of the skill to execute
            arguments: Arguments to pass to the skill
            
        Returns:
            Result from skill execution
        """
        skill = self.registry.get_skill(skill_name)
        if skill:
            return skill.execute(arguments)
        else:
            return f"Unknown command: {skill_name}"
    
    def run(self):
        """Main loop for the engine"""
        self.running = True
        print("Nova AI Engine started. Type 'exit' to quit.")
        
        while self.running:
            try:
                command = input("> ").strip()
                
                if command.lower() in ['exit', 'quit']:
                    self.running = False
                    print("Goodbye!")
                    break
                
                if not command:
                    continue
                
                skill_name, arguments = self.parse_command(command)
                if skill_name:
                    result = self.dispatch(skill_name, arguments)
                    if result:
                        print(result)
                        
            except KeyboardInterrupt:
                self.running = False
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
