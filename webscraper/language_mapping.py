def map_language_code(lang):
    lang_map = {
        'en': 'EN',   # English
        'fr': 'FR',   # French
        'es': 'ES',   # Spanish
        'de': 'DE',   # German
        'it': 'IT',   # Italian
        'pt': 'PT',   # Portuguese
        'nl': 'NL',   # Dutch
        'ru': 'RU',   # Russian
        'zh-cn': 'ZH',# Chinese (Simplified)
        'zh-tw': 'ZH',# Chinese (Traditional)
        'ja': 'JA',   # Japanese
        'ko': 'KO',   # Korean
        'ar': 'AR',   # Arabic
        'hi': 'HI',   # Hindi
        'bn': 'BN',   # Bengali
        'pa': 'PA',   # Punjabi
        'jv': 'JV',   # Javanese
        'ms': 'MS',   # Malay
        'tr': 'TR',   # Turkish
        'vi': 'VI',   # Vietnamese
        'pl': 'PL',   # Polish
        'uk': 'UK',   # Ukrainian
        'ro': 'RO',   # Romanian
        'cs': 'CS',   # Czech
        'el': 'EL',   # Greek
        'hu': 'HU',   # Hungarian
        'sv': 'SV',   # Swedish
        'fi': 'FI',   # Finnish
        'no': 'NO',   # Norwegian
        'da': 'DA',   # Danish
        'he': 'HE',   # Hebrew
        'th': 'TH',   # Thai
        'id': 'ID',   # Indonesian
        # Add more languages as needed
    }
    return lang_map.get(lang, 'UN')  # Default to 'UN' (Unknown) if language not in map
