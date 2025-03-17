"""Module for extracting and managing code file metadata."""

import os
from typing import Dict, List, Optional, Any
import magic  # for mime type detection
import ast
from datetime import datetime

def detect_language(file_path: str, content: str) -> str:
    """
    Detect the programming language of a file based on extension and content.
    
    Args:
        file_path: Path to the file
        content: Content of the file
        
    Returns:
        The detected language name
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    # Common language extensions
    language_map = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.jsx': 'React',
        '.tsx': 'React TypeScript',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.go': 'Go',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.rs': 'Rust',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.cs': 'C#',
        '.html': 'HTML',
        '.css': 'CSS',
        '.scss': 'SCSS',
        '.sql': 'SQL',
        '.md': 'Markdown',
        '.json': 'JSON',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.xml': 'XML',
        '.sh': 'Shell',
        '.bash': 'Shell'
    }
    
    return language_map.get(ext, 'Unknown')

def analyze_python_structure(content: str) -> Dict[str, Any]:
    """
    Analyze Python code structure using AST.
    
    Args:
        content: Python source code content
        
    Returns:
        Dictionary containing code structure information
    """
    try:
        tree = ast.parse(content)
        
        classes = []
        functions = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    'name': node.name,
                    'lineno': node.lineno,
                    'methods': [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                })
            elif isinstance(node, ast.FunctionDef):
                functions.append({
                    'name': node.name,
                    'lineno': node.lineno,
                    'args': [arg.arg for arg in node.args.args]
                })
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                else:
                    module = node.module or ''
                    for name in node.names:
                        imports.append(f"{module}.{name.name}")
        
        return {
            'classes': classes,
            'functions': functions,
            'imports': imports
        }
    except SyntaxError:
        return {
            'classes': [],
            'functions': [],
            'imports': []
        }

def calculate_complexity_metrics(content: str) -> Dict[str, Any]:
    """
    Calculate basic code complexity metrics.
    
    Args:
        content: Source code content
        
    Returns:
        Dictionary containing complexity metrics
    """
    lines = content.splitlines()
    
    # Basic metrics
    metrics = {
        'total_lines': len(lines),
        'blank_lines': sum(1 for line in lines if not line.strip()),
        'comment_lines': sum(1 for line in lines if line.strip().startswith('#')),
        'code_lines': sum(1 for line in lines if line.strip() and not line.strip().startswith('#')),
        'average_line_length': sum(len(line) for line in lines) / len(lines) if lines else 0,
        'max_line_length': max(len(line) for line in lines) if lines else 0
    }
    
    return metrics

def extract_file_metadata(file_path: str, content: str) -> Dict[str, Any]:
    """
    Extract comprehensive metadata for a code file.
    
    Args:
        file_path: Path to the file
        content: Content of the file
        
    Returns:
        Dictionary containing file metadata
    """
    language = detect_language(file_path, content)
    
    metadata = {
        'language': language,
        'size_bytes': len(content),
        'mime_type': magic.from_buffer(content.encode(), mime=True),
        'last_modified': datetime.now().isoformat(),
        'complexity_metrics': calculate_complexity_metrics(content)
    }
    
    # Add language-specific analysis
    if language == 'Python':
        metadata['structure'] = analyze_python_structure(content)
    
    return metadata

def extract_dependencies(files: Dict[str, str]) -> Dict[str, List[str]]:
    """
    Extract file dependencies based on imports and references.
    
    Args:
        files: Dictionary mapping file paths to their content
        
    Returns:
        Dictionary mapping file paths to lists of dependent file paths
    """
    dependencies = {}
    
    for file_path, content in files.items():
        language = detect_language(file_path, content)
        deps = set()
        
        if language == 'Python':
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.Import):
                            for name in node.names:
                                deps.add(name.name.split('.')[0])
                        else:
                            if node.module:
                                deps.add(node.module.split('.')[0])
            except SyntaxError:
                pass
        
        dependencies[file_path] = list(deps)
    
    return dependencies
