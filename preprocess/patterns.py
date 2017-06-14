from collections import defaultdict, Counter
import random
import copy

from sttk import TextHandlerUnit
from sttk import tf_lex, SF_Safe_Russian_NoDlg
from sttk import tf_default
from sttk import TokenMarkers, TokenType

from sttk import Sentence

from corpusmanager import corpus_manager


def normalize_counter(counter):
    sum = 0
    percentage = []
    for (key, value) in counter.items(): sum += value
    for (key, value) in counter.items():
        percentage.append((key, value / (float(sum))))
    return percentage

def weighted_choice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        if upto + w >= r:
            return c
        upto += w
    assert False, "Shouldn't get here"

class SF_Pure_Russian(SF_Safe_Russian_NoDlg):
    def __init__(self):
        SF_Safe_Russian_NoDlg.__init__(self)
        self.id = "pure_russian"

    def pass_condition(self, sentence):
        if not super(SF_Pure_Russian, self).pass_condition(sentence):
            return False
        if sentence.all_words_count < 2:
            return False
        return True


class LanguageModel:
    def __init__(self):
        self.tokfilter = tf_default
        self.max_ngram_len = 8

        self.thu = self.load_thu()
        self.lmd = defaultdict(Counter)
        print(self.thu.sentencefilter)
        self.process_corpus()

    def load_thu(self):
        if True:
            thu = TextHandlerUnit()
            thu.max_ngram_len = self.max_ngram_len
            thu.tokenfilters = [self.tokfilter]
            thu.sentencefilter = SF_Pure_Russian()
        return thu

    def process_corpus(self):
        for doc in corpus_manager:
            if not doc.processed:
                self.thu.process(doc.get_text())
                self.thu.make_ngram_vocabularies()
        self.make_model()

    def make_model(self):
        for ngram_len in range(2, self.max_ngram_len+1):
            ngram_voc = self.thu.NGR_VOCABULARIES[self.tokfilter.id][ngram_len]
            for ngram, frequency in ngram_voc.items():
                history, target = ngram[:-1], ngram[-1]
                self.lmd[history][target] += frequency
        for history in self.lmd:
            self.lmd[history] = normalize_counter(self.lmd[history])
            #print(history, self.lmd[history])


class PatternGenerator:
    def __init__(self, lm):
        self.lm = lm

        self.placeholder = "<usr,{},{}|{}>"

    def generate(self, length=10):
        history = ["."]
        should_end = False
        while not should_end:
            for ngram_len in range(self.lm.max_ngram_len-1, 0, -1):
                if ngram_len > len(history):
                    continue
                ngram = tuple(history[-ngram_len:])
                if ngram not in self.lm.lmd:
                    continue
                else:
                    choice = weighted_choice(self.lm.lmd[ngram])
                    history.append(choice)
                    if (len(history) > length - 1):
                        if self.lm.thu.token_dictionary[choice].markers[TokenMarkers.is_eos]:
                            should_end = True
                            break
        return history[1:]

    def refine(self, sentence):
        result = Sentence()
        s_len = len(sentence)
        should_upper_first = True
        for i in range(s_len):
            token = sentence[i]
            current_token_obj = self.get_tok_obj(token, to_copy=True)
            # upper first char
            if should_upper_first:
                current_token_obj.first_upper()
                should_upper_first = False
            result.add(current_token_obj)
            #add space if it's eos
            if current_token_obj.markers[TokenMarkers.is_eos] and (i != s_len-1):
                result.add(self.space_tok())
                should_upper_first = True
            #add regular space
            if (i < s_len - 1):
                next_token_obj = self.get_tok_obj(sentence[i+1])
                if next_token_obj.toktype in [TokenType.word, TokenType.word_fixed] and \
                                current_token_obj.toktype in [TokenType.word, TokenType.word_fixed]:
                    result.add(self.space_tok())
        result.calculate_meta()
        return result

    # placeholdering
    def create_placeholders(self, sentence):
        s_len = len(sentence.tokens)
        for i in range(s_len):
            token = sentence.tokens[i]
            if self.is_replaceable(token):
                self.change_to_placeholder(token)

    def is_replaceable(self, token):
        if token.toktype != TokenType.word:
            return
        if token.gr == "SPRO,sg,3p,m=nom":
            return True
        return False

    def change_to_placeholder(self, token):
        sex = "m"
        case = "nom"
        token.text = self.placeholder.format(sex, case, token.text)

    # auxiliary
    def get_tok_obj(self, tok_text, to_copy=False):
        tok = self.lm.thu.token_dictionary[tok_text]
        if to_copy:
            tok = copy.copy(tok)
        return tok

    def space_tok(self):
        return self.get_tok_obj(" ")


LM = LanguageModel()
generator = PatternGenerator(LM)
for i in range(100):
    result = generator.generate(10)
    result = generator.refine(result)
    generator.create_placeholders(result)
    print(result.get_str())
    # for tok in result.tokens:
    #     print(tok, tok.get_info())

