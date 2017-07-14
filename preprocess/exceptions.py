from paths import paths
from utils import YamlHandler

class WordExceptions:
    def __init__(self):
        self.content = YamlHandler(paths.exceptions)
        self.default = self.content.doc["General"]
        self.not_plh = self.content.doc["NotPlaceholder"]

    def is_general(self, lex):
        if lex in self.default:
            return True
        return False

    def is_not_plh(self, lex):
        if lex in self.not_plh:
            return True
        return False

word_exceptions = WordExceptions()