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
    
    # Regex for bracket syntax: [lang:text] e.g. [vi: Xin chào]
    # Group 1: lang code (e.g. vi-VN or vi)
    # Group 2: text content
    BRACKET_REGEX = re.compile(r'\[([a-z]{2,3}(?:-[a-z0-9]+)?)\s*:\s*([^\]]+)\]', re.IGNORECASE)

    @staticmethod
    def parse_segments(text: str):
        """
        Parses text into segments.
        Priority 1: Bracket syntax [lang: text] (supports multiple per line)
        Priority 2: Line-based syntax lang(m): text
        """
        if not text:
            return []
            
        segments = []
        
        # Phase 1: Check for Bracket Format [lang: text]
        bracket_matches = list(VoiceParser.BRACKET_REGEX.finditer(text))
        if bracket_matches:
            for m in bracket_matches:
                raw_lang = m.group(1).lower()
                content = m.group(2).strip()
                
                # Check for gender in lang code (e.g. vi-f -> lang=vi, gender=f)
                lang = raw_lang
                gender = None
                
                if '-' in raw_lang:
                    parts = raw_lang.split('-')
                    if parts[-1] in ['m', 'f']:
                        gender = parts[-1]
                        lang = "-".join(parts[:-1])
                
                if content:
                    segments.append({
                        'text': content,
                        'lang': lang,
                        'gender': gender
                    })
            return segments

        # Phase 2: Line-based parsing
        lines = text.split('\n')
        
        current_lang = None
        current_gender = None
        
        for line in lines:
            if not line.strip():
                continue 
                
            match = VoiceParser.PROMPT_REGEX.match(line)
            if match:
                lang = match.group(1)
                gender = match.group(2)
                content = match.group(3)
                
                current_lang = lang
                current_gender = gender
                
                segments.append({
                    'text': content,
                    'lang': lang,
                    'gender': gender
                })
            else:
                segments.append({
                    'text': line,
                    'lang': current_lang,
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
