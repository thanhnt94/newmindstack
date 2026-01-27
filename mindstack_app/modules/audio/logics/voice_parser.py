import re

class VoiceParser:
    """
    Parses text with inline voice prompts such as:
    en(m): Hello world
    vi: Xin chào
    
    Returns structured segments or SSML/Clean text based on target format.
    """
    
    # Regex to detect lines starting with: code(gender): text OR code: text
    # Group 1: code (e.g. en)
    # Group 2: gender (optional, e.g. m)
    # Group 3: text content
    PROMPT_REGEX = re.compile(r'^\s*([a-z]{2})(?:\(([mf])\))?:\s*(.+)$', re.MULTILINE)

    @staticmethod
    def parse_segments(text: str):
        """
        Parses multi-line text into a list of segments.
        Each segment is a dict: {'text': str, 'lang': str|None, 'gender': str|None}
        If a line doesn't match the pattern, it inherits the previous setting or uses None (default).
        """
        lines = text.split('\n')
        segments = []
        
        current_lang = None
        current_gender = None
        
        for line in lines:
            if not line.strip():
                continue # Skip empty lines (or handle newlines if strictly needed)
                
            match = VoiceParser.PROMPT_REGEX.match(line)
            if match:
                lang = match.group(1)
                gender = match.group(2) # Can be None
                content = match.group(3)
                
                current_lang = lang
                current_gender = gender
                
                segments.append({
                    'text': content,
                    'lang': lang,
                    'gender': gender
                })
            else:
                # No prompt found, use current context or treat as generic text
                segments.append({
                    'text': line,
                    'lang': current_lang, # potentially continue previous voice
                    'gender': current_gender
                })
                
        return segments

    @staticmethod
    def generate_ssml(text: str, voice_map: dict, default_voice: str) -> str:
        """
        Converts text with prompts into a full SSML string for Edge TTS.
        
        Args:
            text: Raw input text
            voice_map: Dict mapping 'lang-gender' (e.g. 'en-m') to edge voice IDs.
            default_voice: Fallback voice ID if no prompt/mapping found.
            
        Returns:
            Valid string starting with <speak>...
        """
        segments = VoiceParser.parse_segments(text)
        if not segments:
            return ""
            
        ssml_parts = ['<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">']
        
        for seg in segments:
            content = seg['text']
            lang = seg['lang']
            gender = seg['gender']
            
            voice_id = default_voice
            
            if lang:
                # Construct key: 'en-m', 'vi-f', or just 'en'
                key_gender = f"{lang}-{gender}" if gender else lang
                key_generic = lang
                
                # Try finding specific gendered voice, then generic lang voice
                if key_gender in voice_map:
                    voice_id = voice_map[key_gender]
                elif key_generic in voice_map:
                    voice_id = voice_map[key_generic]
                    
            # Escape XML chars in content
            content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')
            
            ssml_parts.append(f'<voice name="{voice_id}">{content}</voice>')
            
        ssml_parts.append("</speak>")
        return "".join(ssml_parts)

    @staticmethod
    def strip_prompts(text: str) -> str:
        """
        Removes prompt prefixes for engines that don't support voice switching (e.g. gTTS).
        Example: 'en(m): Hello' -> 'Hello'
        """
        segments = VoiceParser.parse_segments(text)
        return " ".join([s['text'] for s in segments])
