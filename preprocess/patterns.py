from collections import defaultdict, Counter
from enum import  Enum
import random
import copy
import dill as pickle
import yaml
import re

from sttk import TextHandlerUnit
from sttk import tf_lex, SF_Safe_Russian_NoDlg
from sttk import tf_default
from sttk import TokenMarkers, TokenType
from sttk import POS, Gender, Number, Case, Other, HumanName, Anim

from sttk import Sentence, SentenceMarkers

from paths import paths
from corpusmanager import corpus_manager

class SentenceCounters(Enum):
    placeholder = 1
    m_placeholder = 2
    f_placeholder = 3

class SentenceType(Enum):
    good = 1
    bad = 2
    filler = 3

marker_to_SentCounter = {Gender.m: SentenceCounters.m_placeholder,
                         Gender.f: SentenceCounters.f_placeholder}

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
        self.reg_unwanted = re.compile('[()"]')
        self.exclude_markers += [SentenceMarkers.first_is_not_word]

    def pass_condition(self, sentence):
        if not super(SF_Pure_Russian, self).pass_condition(sentence):
            return False
        if sentence.all_words_count < 2:
            return False
        if self.reg_unwanted.search(sentence.get_str()):
            return False
        return True


class LanguageModel:
    def __init__(self, lm_dump_name=None):
        self.tokfilter = tf_default
        self.max_ngram_len = 5
        self.lmd = defaultdict(Counter)

        self.NGR_VOCABULARIES = None
        self.token_dictionary = None

        if not lm_dump_name:
            self.process_corpus()
        else:
            print("LM dump loading..")
            lm_dump = self.get_dump(lm_dump_name)
            self.lmd = lm_dump["lmd"]
            self.token_dictionary = lm_dump["token_dictionary"]
            print("LM dump loaded.")

    def load_thu(self):
        thu = TextHandlerUnit()
        thu.max_ngram_len = self.max_ngram_len
        thu.tokenfilters = [self.tokfilter]
        thu.sentencefilter = SF_Pure_Russian()
        return thu

    def process_corpus(self):
        thu = self.load_thu()
        for doc in corpus_manager:
            if not doc.processed:
                thu.process(doc.get_text())
                thu.make_ngram_vocabularies()
                doc.save(thu)
            else:
                dump_dictionary = doc.get_dump()
                thu.NGR_VOCABULARIES = dump_dictionary["ngr"]
                thu.token_dictionary = dump_dictionary["tokdic"]
        self.NGR_VOCABULARIES = thu.NGR_VOCABULARIES
        self.token_dictionary = thu.token_dictionary
        self.make_model()


    def make_model(self):
        for ngram_len in range(2, self.max_ngram_len+1):
            ngram_voc = self.NGR_VOCABULARIES[self.tokfilter.id][ngram_len]
            for ngram, frequency in ngram_voc.items():
                history, target = ngram[:-1], ngram[-1]
                self.lmd[history][target] += frequency
        for history in self.lmd:
            self.lmd[history] = normalize_counter(self.lmd[history])
            #print(history, self.lmd[history])

    def save_model(self, fname=paths.lm_dump):
        lmd_dump = {"lmd": self.lmd, "token_dictionary": self.token_dictionary}
        self.save_obj(fname, lmd_dump)

    def save_simple(self):
        result = []
        for history in self.lmd:
            result.append("{}: {}".format(history, self.lmd[history]))
        with open(paths.lmd_simple, "w", encoding="utf-8") as f:
            f.write("\n".join(result))

    def save_obj(self, fname, obj_to_save):
        with open(fname, 'wb') as output:
            pickle.dump(obj_to_save, output)

    def get_dump(self, fname):
        with open(fname, 'rb') as dmp:
            dmp_obj = pickle.load(dmp)
        return dmp_obj

class PatternManager:
    def __init__(self):
        self.patterns = {"patterns": {1: {"m": [], "f": []},
                                      2: [], 3: [], 4: [], 5: [], 6: []},
                         "fillers": []}
        self.demand = {1: {"m": 1000, "f": 1000},
                       2: 500, 3: 500}
        self.supply = {1: {"m": 0, "f": 0},
                       2: 0, 3: 0, 4: 0, 5: 0, 6: 0}

        self.fillers_count = 0
        self.max_fillers = 5000

    def filter_sentence(self, sentence):
        if sentence.markers[SentenceMarkers.uneven_characters]:
            return SentenceType.bad
        if sentence.markers[SentenceMarkers.first_is_not_word]:
            return SentenceType.bad
        if sentence.counters[SentenceCounters.placeholder] < 1:
            return SentenceType.filler
        return SentenceType.good

    def add(self, sentence):
        # TODO refactor
        sentence_string = sentence.get_str()
        pass_type = self.filter_sentence(sentence)
        if pass_type == SentenceType.bad:
            return
        if pass_type == SentenceType.filler:
            if self.fillers_count < self.max_fillers:
                self.patterns["fillers"].append(sentence_string)
                self.fillers_count += 1
            return

        ph_count = sentence.counters[SentenceCounters.placeholder]
        patterns = self.patterns["patterns"]
        gender = None
        if ph_count > 1 and ph_count < 7:
            patterns_set = patterns[ph_count]
        elif ph_count == 1:
            gender = "m" if sentence.counters[SentenceCounters.m_placeholder] else "f"
            patterns_set = patterns[ph_count][gender]
        else:
            return

        if sentence_string in patterns_set:
            return

        if gender:
            if self.supply[ph_count][gender] >= self.demand[ph_count][gender]:
                return
            self.supply[ph_count][gender] += 1
        else:
            if ph_count in self.demand and self.supply[ph_count] >= self.demand[ph_count]:
                return
            self.supply[ph_count] += 1
        patterns_set.append(sentence_string)

        print(sentence_string)
        print(self.supply)
        print()

    def satisfied(self):
        for key in self.demand:
            if self.demand[key] != self.supply[key]:
                return False
        return True

    def save_patterns(self):
        with open(paths.patterns, "w", encoding="utf-8") as yaml_file:
            yaml.dump(self.patterns, yaml_file, allow_unicode=True)

class PatternGenerator:
    def __init__(self, lm):
        self.lm = lm
        self.placeholder_tokens = ["он", "она"]
        #self.placeholder_markers = [Other.persn, Other.famn, Other.patrn]
        self.placeholder = "<usr{},{},{}|{}>"

    def generate(self, length=12):
        sentence = self.generate_raw(length)
        sentence = self.refine(sentence)
        self.create_placeholders(sentence)
        return sentence

    def generate_raw(self, length):
        history = [random.choice([".", "!", "?"])]
        choices = self.lm.lmd[tuple(history)]
        history.append(weighted_choice(choices))
        # history = [".", "Андрея"]
        should_end = False
        while not should_end:
            for ngram_len in range(self.lm.max_ngram_len-1, 1, -1):
                if ngram_len > len(history):
                    continue
                ngram = tuple(history[-ngram_len:])
                if ngram not in self.lm.lmd:
                    if ngram_len == 2:
                        return self.generate_raw(length)
                    continue
                else:
                    choice = weighted_choice(self.lm.lmd[ngram])
                    history.append(choice)
                    if (len(history) > length - 1):
                        if self.get_tok_obj(choice).markers[TokenMarkers.is_eos]:
                            should_end = True
                            break
        return history[1:]

    # refinement
    def refine(self, sentence):
        sentence = self.convert(sentence)
        while self.has_extra_names(sentence):
            self.remove_extra_names(sentence)
        self.finalisation(sentence)
        return sentence

    def convert(self, sentence):
        result = Sentence()
        for token in sentence:
            current_token_obj = self.get_tok_obj(token, to_copy=True)
            result.add(current_token_obj)
        return result

    def remove_extra_names(self, sentence):
        # TODO refactoring
        s_len = len(sentence.tokens)
        tokens_result = []
        skip_this_token = False
        for i in range(s_len-1):
            if skip_this_token:
                skip_this_token = False
                continue
            current_token = sentence.tokens[i]
            next_token = sentence.tokens[i + 1]
            if not (self.is_name(current_token) and self.is_name(next_token)) or \
                    (current_token.gr_properties[HumanName] == next_token.gr_properties[HumanName]):
                tokens_result.append(current_token)
            else:
                for tok in [current_token, next_token]:
                    if tok.gr_properties[HumanName] == HumanName.persn:
                        tokens_result.append(tok)
                        skip_this_token = True
                if not skip_this_token:
                    for tok in [current_token, next_token]:
                        if tok.gr_properties[HumanName] == HumanName.patrn:
                            tokens_result.append(tok)
                            skip_this_token = True
        tokens_result.append(sentence.tokens[-1])
        sentence.tokens = tokens_result


    def has_extra_names(self, sentence):
        for i in range(len(sentence.tokens)-1):
            current_token = sentence.tokens[i]
            next_token = sentence.tokens[i + 1]
            if (self.is_name(current_token) and self.is_name(next_token)):
                if current_token.gr_properties[HumanName] == next_token.gr_properties[HumanName]:
                    return False
                return True
        return False


    def finalisation(self, sentence):
        tokens_result = []
        s_len = len(sentence.tokens)
        should_upper_first = True
        for i in range(s_len):
            current_token = sentence.tokens[i]
            tokens_result.append(current_token)
            # upper first char
            if should_upper_first:
                current_token.first_upper()
                should_upper_first = False
            #add space if it's eos
            if current_token.markers[TokenMarkers.is_eos] and (i != s_len-1):
                tokens_result.append(self.space_tok())
                if (current_token.text != "..."):
                    should_upper_first = True
            #add regular space
            if (i < s_len - 1):
                next_token = sentence.tokens[i+1]
                if next_token.toktype in [TokenType.word, TokenType.word_fixed] and \
                                current_token.toktype in [TokenType.word, TokenType.word_fixed]:
                    tokens_result.append(self.space_tok())
        sentence.tokens = tokens_result
        sentence.calculate_meta()
        return sentence

    # placeholdering
    def create_placeholders(self, sentence):
        s_len = len(sentence.tokens)
        for i in range(s_len):
            token = sentence.tokens[i]
            if self.is_replaceable(token):
                sentence.counters[SentenceCounters.placeholder] += 1
                sentence.counters[marker_to_SentCounter[token.gr_properties[Gender]]] += 1
                self.change_to_placeholder(token, sentence.counters[SentenceCounters.placeholder])

    def is_replaceable(self, token):
        if token.toktype != TokenType.word:
            return False
        # temporary (nom and Gender)
        if token.gr_properties[Case] != Case.nom:
            return False
        if not(token.gr_properties[Gender]):
            return False

        if token.gr_properties[HumanName]:
                return True
        if token.gr_properties[HumanName] == Anim.anim:
                return True
        for tok_text in self.placeholder_tokens:
            if token.text.lower() == tok_text:
                return True
        return False

    def change_to_placeholder(self, token, count):
        gender = token.gr_properties[Gender].name
        case = token.gr_properties[Case].name
        token.text = self.placeholder.format(count, gender, case, token.text)

    # auxiliary
    def get_tok_obj(self, tok_text, to_copy=False):
        tok = self.lm.token_dictionary[tok_text]
        if to_copy:
            tok = copy.copy(tok)
        return tok

    def space_tok(self):
        return self.get_tok_obj(" ")

    def is_name(self, token):
        if token.gr_properties[HumanName]:
            return True
        return False


def create_and_save_lm(fname=paths.lm_dump):
    LM = LanguageModel()
    LM.save_model(fname)
    LM.save_simple()

def make_patterns(lm_fname=paths.lm_dump):
    PM = PatternManager()
    LM = LanguageModel(lm_fname)
    generator = PatternGenerator(LM)
    while not PM.satisfied():
        for lengths in [(6, 8), (8, 10), (10, 15)]:
            sentence = generator.generate(random.randint(*lengths))
            PM.add(sentence)
    PM.save_patterns()
    print(PM.demand)

def save_simple_lmd(lm_fname=paths.lm_dump):
    LM = LanguageModel(lm_fname)
    LM.save_simple()

if __name__ == "__main__":
    create_and_save_lm()
    # save_simple_lmd()
    make_patterns()