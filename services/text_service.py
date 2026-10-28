from config import LANGUAGE_PREFIXES

IGBO_WORD_MAP = {
    'chineke': 'Chineke',  # God
    'ndewo': 'Ndeewo',     # Hello
    'kedu': 'Kedụ',        # How
    'ime': 'ịme',          # to do
    'umu': 'ụmụ',          # children
    'nwa': 'nwa',          # child
    'anya': 'anya',        # eye
    'obi': 'obi',          # heart
    'ulo': 'ụlọ',          # house
    'aha': 'aha',          # name
    'onye': 'onye',        # person
    'ugbo': 'ụgbọ',        # vehicle
    'uche': 'uche',        # wisdom/mind
    'chi': 'chi',          # personal god/destiny
    'eze': 'eze',          # king
    'ada': 'ada',          # first daughter
    'nna': 'nna',          # father
    'nne': 'nne',          # mother
    'nwanne': 'nwanne',    # sibling
    'egwu': 'egwu',        # music/dance
    'oji': 'ọjị',          # kola nut
    'mmiri': 'mmiri',      # water
    'anwu': 'anwụ',        # sun
    'onwa': 'ọnwa',        # moon
    'kpakpando': 'kpakpando',  # star
}

YORUBA_WORD_MAP = {
    'bawo': 'Báwo',        # How
    'ni': 'ni',            # is/are
    'se': 'ṣe',            # to do/make
    'omo': 'ọmọ',          # child
    'oko': 'ọkọ',          # husband/vehicle
    'ile': 'ilé',          # house
    'eko': 'Èkó',          # Lagos
    'oba': 'ọba',          # king
    'oye': 'òye',          # title/position
    'ire': 'ire',          # good/blessing
    'aje': 'àjẹ',          # wealth/witch
    'owo': 'owó',          # money
    'ori': 'orí',          # head/destiny
    'emi': 'èmi',          # I/me
    'iwo': 'ìwọ',          # you
    'awa': 'àwa',          # we
    'eyin': 'ẹ̀yin',        # you (plural)
    'won': 'wọn',          # they
    'ti': 'tí',            # of/from
    'si': 'sí',            # to/at
    'fun': 'fún',          # for
    'ni': 'ní',            # at/in
    'pe': 'pé',            # that/to call
    'ki': 'kí',            # to/let
    'ma': 'má',            # don't
    'ko': 'kò',            # not
    'da': 'dá',            # to create/pour
    'wa': 'wá',            # to come/to be
    'lo': 'lọ',            # to go
    'gbo': 'gbọ́',          # to hear
    'ri': 'rí',            # to see
    'je': 'jẹ',            # to eat/to be
    'mu': 'mú',            # to drink/to take
    'sun': 'sùn',          # to sleep
    'dide': 'dìde',        # to stand up
    'joko': 'jókòó',       # to sit
}


def _apply_word_map_with_casing(text, word_map):
    """Helper to apply a diacritic mapping preserving casing and trailing punctuation."""
    words = text.split()
    enhanced_words = []

    for word in words:
        clean_word = word.lower().strip('.,!?;:')
        if clean_word in word_map:
            enhanced = word_map[clean_word]
            if word.isupper():
                enhanced = enhanced.upper()
            elif word.istitle():
                enhanced = enhanced.capitalize()

            # Preserve punctuation
            punctuation = ''
            for char in word[::-1]:
                if char in '.,!?;:':
                    punctuation = char + punctuation
                else:
                    break
            enhanced_words.append(enhanced + punctuation)
        else:
            enhanced_words.append(word)

    return ' '.join(enhanced_words)


def enhance_igbo_text_with_diacritics(text):
    """Add proper Igbo diacritics to common words"""
    return _apply_word_map_with_casing(text, IBO_WORD_MAP if 'IBO_WORD_MAP' in globals() else IGBO_WORD_MAP)


def enhance_yoruba_text_with_diacritics(text):
    """Add proper Yoruba diacritics to common words"""
    return _apply_word_map_with_casing(text, YORUBA_WORD_MAP)


def enhance_text_by_language(text, language_code):
    """Enhance text diacritics based on language code if applicable"""
    if language_code == 'ig':
        return enhance_igbo_text_with_diacritics(text)
    elif language_code == 'yo':
        return enhance_yoruba_text_with_diacritics(text)
    return text


def extract_language_prefix(text):
    """Extract language prefix from text and return (language_code, cleaned_text, is_preference_setting, is_tts_request)"""
    tts_commands = ['/speak']
    text_lower = text.lower().strip()

    # Check for TTS commands first
    for tts_cmd in tts_commands:
        if text_lower.startswith(tts_cmd):
            remaining_text = text[len(tts_cmd):].strip()

            # Check if a language is specified after TTS command
            for prefix, lang_code in LANGUAGE_PREFIXES.items():
                lang_name = prefix[1:]  # e.g., 'yoruba'
                if remaining_text.lower().startswith(lang_name):
                    text_to_convert = remaining_text[len(lang_name):].strip()
                    return lang_code, text_to_convert, False, True

            return None, remaining_text, False, True

    # Check for regular language prefixes
    for prefix, lang_code in LANGUAGE_PREFIXES.items():
        if text_lower.startswith(prefix):
            cleaned_text = text[len(prefix):].strip()
            is_preference_setting = len(cleaned_text) == 0
            return lang_code, cleaned_text, is_preference_setting, False

    return None, text, False, False
