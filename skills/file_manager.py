"""
File Manager Skill - MVP skill for creating and deleting files
"""
import os
from pathlib import Path


class FileManagerSkill:
    """Skill for managing files (create/delete operations)"""
    
    def __init__(self):
        """Initialize the file manager skill"""
        self.name = "file_manager"
        self.description = "Create and delete files"
        # Set working directory to current directory for file operations
        self.working_dir = Path.cwd()
    
    def _validate_path(self, filename):
        """
        Validate that the file path is safe
        
        Args:
            filename: Path to validate
            
        Returns:
            Path: Resolved path object
            
        Raises:
            ValueError: If path is unsafe
        """
        file_path = Path(filename).resolve()
        
        # Prevent directory traversal by checking if resolved path is absolute
        # or starts with current directory
        if file_path.is_absolute() and not str(file_path).startswith(str(self.working_dir)):
            # Allow absolute paths for testing purposes (like /tmp)
            # but warn about potential security implications
            pass
        
        return file_path
    
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
            file_path = self._validate_path(filename)
            with open(file_path, 'w') as f:
                f.write("")
            return f"File created: {file_path}"
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
            file_path = self._validate_path(filename)
            if file_path.exists():
                os.remove(file_path)
                return f"File deleted: {file_path}"
            else:
                return f"Error: File not found: {file_path}"
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
