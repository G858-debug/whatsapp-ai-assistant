    def _check_package_needs_clarification(self, package_details: str) -> bool:
        """
        Check if package deal details are vague and need clarification.
        Returns True if clarification is needed.
        """
        import re

        if not package_details or len(package_details.strip()) < 10:
            return True

        # Check if essential information is missing
        has_session_count = bool(re.search(r'\d+\s*(session|sessions|ses)', package_details, re.IGNORECASE))
        has_price = bool(re.search(r'R?\s*\d+', package_details))
        has_duration = bool(re.search(r'\d+\s*(month|months|week|weeks|day|days)', package_details, re.IGNORECASE))

        # If any of these is missing, we need clarification
        if not (has_session_count and has_price):
            return True

        # Check for vague phrases that indicate incomplete information
        vague_phrases = ['tbd', 'to be determined', 'discuss', 'flexible', 'depends', 'various', 'etc']
        for phrase in vague_phrases:
            if phrase in package_details.lower():
                return True

        return False