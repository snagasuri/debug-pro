"""Module for handling code snapshot diffing and comparison."""

from typing import Dict, List, Optional, Set
from datetime import datetime

from app.schemas.common import CodeFile, CodeSnapshot, DiffResult

def calculate_diff(old_snapshot: CodeSnapshot, new_snapshot: CodeSnapshot) -> DiffResult:
    """
    Calculate the differences between two code snapshots.
    
    Args:
        old_snapshot: The previous code snapshot
        new_snapshot: The current code snapshot
        
    Returns:
        A DiffResult containing added, modified, and deleted files
    """
    old_files = old_snapshot.files
    new_files = new_snapshot.files
    
    # Get sets of file paths
    old_paths = set(old_files.keys())
    new_paths = set(new_files.keys())
    
    # Calculate added, modified, and deleted files
    added_paths = new_paths - old_paths
    deleted_paths = old_paths - new_paths
    common_paths = old_paths & new_paths
    
    # Find modified files by comparing content
    modified_paths = {
        path for path in common_paths
        if old_files[path].content != new_files[path].content
    }
    
    # Create DiffResult
    added = {path: new_files[path] for path in added_paths}
    modified = {path: new_files[path] for path in modified_paths}
    deleted = list(deleted_paths)
    
    return DiffResult(
        added=added,
        modified=modified,
        deleted=deleted
    )

def apply_diff(base_snapshot: CodeSnapshot, diff: DiffResult) -> CodeSnapshot:
    """
    Apply a diff to a base snapshot to create a new snapshot.
    
    Args:
        base_snapshot: The snapshot to apply changes to
        diff: The DiffResult containing the changes
        
    Returns:
        A new CodeSnapshot with the changes applied
    """
    # Create a copy of the base files
    updated_files = base_snapshot.files.copy()
    
    # Apply additions
    for path, file in diff.added.items():
        updated_files[path] = file
    
    # Apply modifications
    for path, file in diff.modified.items():
        if path in updated_files:
            updated_files[path] = file
    
    # Apply deletions
    for path in diff.deleted:
        if path in updated_files:
            del updated_files[path]
    
    # Create new snapshot
    return CodeSnapshot(
        id=base_snapshot.id,  # Maintain same ID for version tracking
        timestamp=datetime.now(),
        files=updated_files,
        metadata={
            **(base_snapshot.metadata or {}),
            "diff_applied": {
                "timestamp": datetime.now().isoformat(),
                "added": len(diff.added),
                "modified": len(diff.modified),
                "deleted": len(diff.deleted)
            }
        }
    )

def serialize_diff(diff: DiffResult) -> Dict:
    """
    Serialize a DiffResult to a dictionary format suitable for storage.
    
    Args:
        diff: The DiffResult to serialize
        
    Returns:
        A dictionary representation of the diff
    """
    return {
        "added": {
            path: file.dict() for path, file in diff.added.items()
        },
        "modified": {
            path: file.dict() for path, file in diff.modified.items()
        },
        "deleted": diff.deleted
    }

def deserialize_diff(diff_dict: Dict) -> DiffResult:
    """
    Create a DiffResult from a serialized dictionary format.
    
    Args:
        diff_dict: The serialized diff dictionary
        
    Returns:
        A DiffResult object
    """
    added = {
        path: CodeFile(**file_dict)
        for path, file_dict in diff_dict["added"].items()
    }
    modified = {
        path: CodeFile(**file_dict)
        for path, file_dict in diff_dict["modified"].items()
    }
    deleted = diff_dict["deleted"]
    
    return DiffResult(
        added=added,
        modified=modified,
        deleted=deleted
    )

def get_changed_files(diff: DiffResult) -> Set[str]:
    """
    Get a set of all file paths that were changed in a diff.
    
    Args:
        diff: The DiffResult to analyze
        
    Returns:
        A set of file paths that were added, modified, or deleted
    """
    changed = set()
    changed.update(diff.added.keys())
    changed.update(diff.modified.keys())
    changed.update(diff.deleted)
    return changed
