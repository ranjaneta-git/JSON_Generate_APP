"""
Custom JSON formatter for BMIoT firmware configs
Formats JSON with readable array layouts matching firmware style
"""
import json
from typing import Any, Dict, List


class CompactArrayEncoder(json.JSONEncoder):
    """Custom JSON encoder that formats arrays compactly"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.indent_level = 0
    
    def encode(self, obj):
        """Encode object with custom formatting"""
        if isinstance(obj, dict):
            return self._encode_dict(obj)
        elif isinstance(obj, list):
            return self._encode_list(obj)
        else:
            return super().encode(obj)
    
    def _encode_dict(self, obj, level=0):
        """Encode dictionary with proper indentation"""
        if not obj:
            return "{}"
        
        indent = "  " * level
        next_indent = "  " * (level + 1)
        
        items = []
        for key, value in obj.items():
            encoded_value = self._encode_value(value, level + 1)
            items.append(f'{next_indent}"{key}": {encoded_value}')
        
        return "{\n" + ",\n".join(items) + f"\n{indent}}}"
    
    def _encode_value(self, value, level):
        """Encode a value with appropriate formatting"""
        if isinstance(value, dict):
            return self._encode_dict(value, level)
        elif isinstance(value, list):
            return self._encode_list(value, level)
        elif isinstance(value, str):
            return json.dumps(value)
        else:
            return json.dumps(value)
    
    def _encode_list(self, obj, level=0):
        """Encode list with smart formatting"""
        if not obj:
            return "[]"
        
        # Check if list contains only simple types (int, str, float)
        is_simple = all(isinstance(item, (int, float, str, bool, type(None))) for item in obj)
        
        if is_simple:
            # Format simple arrays on single line if not too long
            content = ", ".join(json.dumps(item) for item in obj)
            if len(content) < 80:  # Keep on one line if under 80 chars
                return f"[{content}]"
            else:
                # Break into multiple lines for readability
                return self._encode_list_multiline(obj, level)
        else:
            # Complex arrays (like JKA) - each element on new line
            return self._encode_list_complex(obj, level)
    
    def _encode_list_multiline(self, obj, level):
        """Encode simple list across multiple lines"""
        indent = "  " * level
        next_indent = "  " * (level + 1)
        
        # Group items in rows of ~10 for readability
        items_per_row = 10
        rows = []
        for i in range(0, len(obj), items_per_row):
            chunk = obj[i:i + items_per_row]
            row_content = ", ".join(json.dumps(item) for item in chunk)
            rows.append(f"{next_indent}{row_content}")
        
        return "[\n" + ",\n".join(rows) + f"\n{indent}]"
    
    def _encode_list_complex(self, obj, level):
        """Encode complex list with each item on new line"""
        indent = "  " * level
        next_indent = "  " * (level + 1)
        
        items = []
        for item in obj:
            if isinstance(item, list):
                # Nested list (like JKA entries) - keep compact
                encoded = self._encode_list_compact(item)
            else:
                encoded = self._encode_value(item, level + 1)
            items.append(f"{next_indent}{encoded}")
        
        return "[\n" + ",\n".join(items) + f"\n{indent}]"
    
    def _encode_list_compact(self, obj):
        """Encode nested list compactly (for JKA entries)"""
        items = []
        for item in obj:
            if isinstance(item, list):
                # Inner arrays stay on one line
                content = ", ".join(json.dumps(x) for x in item)
                items.append(f"[{content}]")
            else:
                items.append(json.dumps(item))
        return "[" + ", ".join(items) + "]"


def format_bmiot_json(data: Dict[str, Any]) -> str:
    """
    Format BMIoT JSON with readable layout
    
    Args:
        data: Dictionary to format
        
    Returns:
        Formatted JSON string
    """
    encoder = CompactArrayEncoder()
    return encoder.encode(data)


def format_and_save_json(data: Dict[str, Any], filepath: str):
    """
    Format and save BMIoT JSON to file
    
    Args:
        data: Dictionary to save
        filepath: Output file path
    """
    formatted = format_bmiot_json(data)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(formatted)
        f.write('\n')  # Trailing newline


# Convenience function for backward compatibility
def save_formatted_json(data: Dict[str, Any], filepath: str):
    """Save JSON with custom formatting (backward compatible)"""
    format_and_save_json(data, filepath)
