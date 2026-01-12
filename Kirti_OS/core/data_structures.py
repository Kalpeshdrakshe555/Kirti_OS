# Kirti_OS/core/data_structures.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

@dataclass
class ProjectContext:
    """
    Holds the entire state of the project being built.
    Passed between Scraper, DevOps, and Debugger.
    """
    project_name: str
    user_request: str
    
    # From Blueprint
    tech_stack: List[str] = field(default_factory=list)
    file_list: List[str] = field(default_factory=list)
    folder_structure: Dict[str, List[str]] = field(default_factory=dict)
    dependencies: Dict[str, str] = field(default_factory=dict)
    
    # Tracking Progress
    generated_files: List[str] = field(default_factory=list)
    failed_files: List[str] = field(default_factory=list)
    file_contents: Dict[str, str] = field(default_factory=dict) # Cache code
    
    # Stats
    current_file_index: int = 0
    total_files: int = 0

    def get_file_path(self, filename: str) -> str:
        """Helper to find path of a file from folder structure"""
        # Simple search in folder structure
        for folder, files in self.folder_structure.items():
            if filename in files:
                return f"{folder}/{filename}"
        return filename # Fallback

@dataclass
class FileRequest:
    """Request sent to ProScraper to generate a file"""
    file_name: str
    purpose: str
    context: ProjectContext

@dataclass
class FileResponse:
    """Response from ProScraper with generated code"""
    file_name: str
    code: str
    metadata: Dict[str, Any]
    success: bool

@dataclass
class BuildResult:
    """Result from DevOps Agent after saving/running"""
    file_name: str
    success: bool
    message: str
    stderr: str = ""

@dataclass
class DebugResult:
    """Result from AutoDebugger"""
    file_name: str
    fixed: bool
    final_code: Optional[str] = None
    error_summary: str = ""