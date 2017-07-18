from sttk import HumanName, Gender

from custom_enums import TokenCustomMarkers

class Sentence_variegater:
    def __init__(self, token_dictionary):
        self.token_dictionary = token_dictionary

    def variegate(self, sentence):
        for token in sentence.tokens:
            self.change_name(token)
        return sentence

    def change_name(self, token):
        if token.gr_properties[HumanName] and not token.markers[TokenCustomMarkers.is_replaceable]:
            if token.gr_properties[Gender] == Gender.f:
                token.text = "Марго"
            elif token.gr_properties[Gender] == Gender.m:
                token.text = "Стэнли"
            else:
                token.text = "Ганди"

    def find_similar_tokens_by_grammar(self, token_text):
        grams = self.token_dictionary[token_text].gr
        similar_tokens = []
        for token in self.token_dictionary:
            if self.token_dictionary[token].gr == grams:
                similar_tokens.append(token)
        return similar_tokens