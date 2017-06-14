from collections import defaultdict, Counter
import random
import re

from sttk import TextHandlerUnit
from sttk import tf_lex, SF_Safe_Russian_NoDlg
from sttk import tf_default
from sttk import TokenMarkers, TokenType

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
        result = []
        s_len = len(sentence)
        should_upper_first = True
        for i in range(s_len):
            token = sentence[i]
            current_token_obj = self.lm.thu.token_dictionary[token]
            # upper first char
            if should_upper_first:
                token = token[0].upper() + token[1:]
                should_upper_first = False
            result.append(token)
            #add space if it's eos
            if current_token_obj.markers[TokenMarkers.is_eos]:
                result.append(" ")
                should_upper_first = True
            #add regular space
            if (i < s_len - 1):
                next_token_obj = self.lm.thu.token_dictionary[sentence[i+1]]
                if next_token_obj.toktype in [TokenType.word, TokenType.word_fixed] and \
                                current_token_obj.toktype in [TokenType.word, TokenType.word_fixed]:
                    result.append(" ")

        result = "".join(result)
        #result = result[0].upper() + result[1:]
        return result


LM = LanguageModel()
generator = PatternGenerator(LM)
for i in range(30):
    result = generator.generate(15)
    print(generator.refine(result))
