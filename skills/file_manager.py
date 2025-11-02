"""
File Manager Skill - MVP skill for creating and deleting files
"""
import os


class FileManagerSkill:
    """Skill for managing files (create/delete operations)"""
    
    def __init__(self):
        """Initialize the file manager skill"""
        self.name = "file_manager"
        self.description = "Create and delete files"
    
    def execute(self, arguments):
        """
        Execute file management commands
        
        Args:
            arguments: Command arguments (e.g., "create filename.txt" or "delete filename.txt")
            
        Returns:
            str: Result message
        """
        parts = arguments.split(maxsplit=1)
        if not parts:
            return self.help()
        
        action = parts[0].lower()
        
        if action == 'create':
            if len(parts) < 2:
                return "Error: Please specify a filename to create"
            filename = parts[1]
            return self.create_file(filename)
        
        elif action == 'delete':
            if len(parts) < 2:
                return "Error: Please specify a filename to delete"
            filename = parts[1]
            return self.delete_file(filename)
        
        else:
            return self.help()
    
    def create_file(self, filename):
        """
        Create a new file
        
        Args:
            filename: Name of the file to create
            
        Returns:
            str: Result message
        """
        try:
            with open(filename, 'w') as f:
                f.write("")
            return f"File created: {filename}"
        except Exception as e:
            return f"Error creating file: {e}"
    
    def delete_file(self, filename):
        """
        Delete an existing file
        
        Args:
            filename: Name of the file to delete
            
        Returns:
            str: Result message
        """
        try:
            if os.path.exists(filename):
                os.remove(filename)
                return f"File deleted: {filename}"
            else:
                return f"Error: File not found: {filename}"
        except Exception as e:
            return f"Error deleting file: {e}"
    
    def help(self):
        """
        Return help information for this skill
        
        Returns:
            str: Help message
        """
        return """File Manager Skill
Usage:
  file create <filename>  - Create a new file
  file delete <filename>  - Delete an existing file
"""
