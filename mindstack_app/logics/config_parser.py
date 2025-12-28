"""
Config Parser - Pure Logic for Configuration Type Inference and Parsing

Pure functions for converting configuration values between types.
No database access - only type inference and conversion logic.
"""

from typing import Any
import os


class ConfigParser:
    """Pure logic for configuration parsing and type inference."""

    @staticmethod
    def infer_data_type(key: str) -> str:
        """
        Infer data type from configuration key naming convention.
        
        Args:
            key: Configuration key name
        
        Returns:
            Inferred data type: 'bool', 'int', 'path', or 'string'
        
        Examples:
            >>> ConfigParser.infer_data_type('IS_ENABLED')
            'bool'
            >>> ConfigParser.infer_data_type('MAX_LIMIT')
            'int'
            >>> ConfigParser.infer_data_type('UPLOAD_FOLDER')
            'path'
        """
        key_upper = key.upper()
        
        # Boolean patterns
        if key_upper.startswith(("IS_", "HAS_", "ENABLE_")) or \
           key_upper.endswith(("_ENABLED", "_ENABLE")):
            return "bool"
        
        # Integer patterns
        if key_upper.endswith((
            "_COUNT", "_LIMIT", "_TIMEOUT", "_TTL", 
            "_SECONDS", "_MINUTES", "_MAX", "_MIN"
        )):
            return "int"
        
        # Path patterns
        if key_upper.endswith(("_FOLDER", "_PATH", "_DIR", "_DIRECTORY")):
            return "path"
        
        # Default to string
        return "string"

    @staticmethod
    def parse_value(raw_value: Any, data_type: str) -> Any:
        """
        Parse raw configuration value to typed value.
        
        Args:
            raw_value: Raw value from database (usually string)
            data_type: Target data type ('bool', 'int', 'path', 'string')
        
        Returns:
            Parsed typed value
        
        Raises:
            ValueError: If conversion fails
        """
        try:
            # Boolean conversion
            if data_type == "bool":
                if isinstance(raw_value, bool):
                    return raw_value
                if isinstance(raw_value, str):
                    return raw_value.strip().lower() in {"1", "true", "yes", "on"}
                return bool(raw_value)

            # Integer conversion
            if data_type == "int":
                if raw_value == '' or raw_value is None:
                    return 0
                return int(raw_value)

            # Path conversion (absolute path)
            if data_type == "path" and isinstance(raw_value, str):
                return os.path.abspath(raw_value)

        except (TypeError, ValueError) as e:
            # Return safe defaults on error
            if data_type == 'int':
                return 0
            if data_type == 'bool':
                return False
            raise ValueError(f"Cannot convert '{raw_value}' to {data_type}") from e

        # Default: return as-is (string)
        return raw_value

    @staticmethod
    def parse_with_inference(key: str, raw_value: Any) -> Any:
        """
        Convenience method: infer type from key then parse value.
        
        Args:
            key: Configuration key
            raw_value: Raw value to parse
        
        Returns:
            Parsed typed value
        """
        data_type = ConfigParser.infer_data_type(key)
        return ConfigParser.parse_value(raw_value, data_type)
