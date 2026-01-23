"""
Response Parser - Pure functions to clean and parse AI outputs.
"""
import re
import json
from typing import Dict, Any, Union, Optional

class ResponseParser:
    """Utility to clean and structured AI responses."""
    
    @staticmethod
    def clean_markdown(text: str) -> str:
        """
        Remove markdown code blocks from text.
        Example: ```markdown ... ``` -> ...
        """
        if not text:
            return ""
            
        # Remove ```markdown or ``` wrapper at start/end
        # Regex explanation:
        # ^```\w*\s*  -> Match ``` followed optionally by language name and whitespace at start
        # \s*```$     -> Match whitespace and ``` at end
        cleaned = re.sub(r'^```\w*\s*', '', text.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned)
        return cleaned.strip()

    @staticmethod
    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to extract and parse JSON from text.
        Text might be wrapped in ```json ... ``` or just raw JSON.
        """
        if not text:
            return None
            
        try:
            # 1. Try strict parse first
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
        # 2. Try converting from markdown wrapper
        cleaned = ResponseParser.clean_markdown(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
            
        # 3. Try finding first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                candidate = text[start : end + 1]
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
                
        return None
