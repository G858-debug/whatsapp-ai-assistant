from typing import Dict, List, Tuple
import re

class SALanguageDetector:
    """Detects South African languages in text"""
    
    LANGUAGE_MARKERS = {
        'en': ['the', 'is', 'are', 'what', 'when', 'how'],
        'af': ['die', 'is', 'wat', 'wanneer', 'hoe', 'en'],
        'xh': ['le', 'phi', 'njani', 'nini', 'ukuba'],
        'zu': ['le', 'phi', 'kanjani', 'nini', 'ukuthi'],
        'st': ['ke', 'eng', 'jwang', 'neng', 'hore'],
        'tn': ['ke', 'eng', 'jang', 'leng', 'gore']
    }

    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detects the most likely language of the input text
        Returns tuple of (language_code, confidence_score)
        """
        text = text.lower()
        scores: Dict[str, int] = {lang: 0 for lang in self.LANGUAGE_MARKERS}
        
        words = set(re.findall(r'\w+', text))
        
        for lang, markers in self.LANGUAGE_MARKERS.items():
            for marker in markers:
                if marker in words:
                    scores[lang] += 1
        
        if not any(scores.values()):
            return 'en', 0.0
            
        best_lang = max(scores.items(), key=lambda x: x[1])
        confidence = best_lang[1] / len(words)
        
        return best_lang[0], confidence