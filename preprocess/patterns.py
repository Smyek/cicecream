from collections import defaultdict, Counter
from enum import  Enum
import random
import copy
from pprint import pformat
import yaml
import re

from sttk import TextHandlerUnit, TokenDictionary
from sttk import tf_lex, SF_Safe_Russian_NoDlg
from sttk import tf_default
from sttk import TokenMarkers, TokenType
from sttk import POS, Gender, Number, Case, Other, HumanName, Anim
from sttk import Sentence, SentenceMarkers
from sttk import markers_manager

from paths import paths
from corpusmanager import corpus_manager

from exceptions import word_exceptions

from utils import YamlHandler

class SentenceCounters(Enum):
    placeholder = 1
    m_placeholder = 2
    f_placeholder = 3

class SentenceType(Enum):
    good = 1
    bad = 2
    filler = 3

class SentenceCustomMarkers(Enum):
    has_V = 1
    has_exception = 2


class TokenCustomMarkers(Enum):
    is_replaceable = 1
    exception = 2

marker_to_SentCounter = {Gender.m: SentenceCounters.m_placeholder,
                         Gender.f: SentenceCounters.f_placeholder}

def custom_token_marker_signer(token):
    if word_exceptions.is_general(token.lex):
        token.markers[TokenCustomMarkers.exception] = True

markers_manager.add_custom_enum(TokenCustomMarkers)
markers_manager.token_signers.append(custom_token_marker_signer)
markers_manager.add_tokmar_to_sentmar(TokenCustomMarkers.exception, SentenceCustomMarkers.has_exception)

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
        self.reg_unwanted = re.compile('[\(\)"]')
        self.exclude_markers += [SentenceMarkers.first_is_not_word,
                                 SentenceMarkers.has_obscene,
                                 SentenceMarkers.has_bastard,
                                 SentenceMarkers.has_bad_single_char]

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
        self.max_ngram_len = 4
        self.lmd = defaultdict(Counter)

        self.NGR_VOCABULARIES = None
        self.token_dictionary = None

        if not lm_dump_name:
            self.process_corpus()
        else:
            print("LM dump loading..")
            lm_dump = self.get_dump(lm_dump_name)
            self.lmd = lm_dump["lmd"]
            self.token_dictionary = TokenDictionary()
            self.token_dictionary.load_dump(lm_dump["token_dictionary"])
            print(self.token_dictionary.dic)
            print("LM dump loaded.")

    def load_thu(self):
        thu = TextHandlerUnit(fixlist_path = paths.fixlist)
        thu.max_ngram_len = self.max_ngram_len
        thu.tokenfilters = [self.tokfilter]
        thu.sentencefilter = SF_Pure_Russian()
        return thu

    def process_corpus(self):
        main_thu = self.load_thu()
        for doc in corpus_manager:
            single_thu = self.load_thu()
            if not doc.processed:
                single_thu.process(doc.get_text())
                single_thu.make_ngram_vocabularies()
                doc.save(single_thu)
            else:
                dump_dictionary = doc.get_dump()
                single_thu.NGR_VOCABULARIES.load_dump(dump_dictionary["ngr"])
                single_thu.token_dictionary.load_dump(dump_dictionary["tokdic"])
            main_thu += single_thu
        self.NGR_VOCABULARIES = main_thu.NGR_VOCABULARIES
        self.token_dictionary = main_thu.token_dictionary
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
        print("Saving lmd..")
        self.lmd = dict(self.lmd)
        self.token_dictionary = self.token_dictionary.get_dump()
        lmd_dump = {"lmd": self.lmd, "token_dictionary": self.token_dictionary}
        for token in self.token_dictionary:
            print(token, self.token_dictionary[token])
        self.save_obj(fname, lmd_dump)
        print("Saving lmd complete")

    def save_obj(self, fname, obj_to_save):
        with open(fname, 'w', encoding="utf-8") as output:
            output.write(pformat(obj_to_save))

    def get_dump(self, fname):
        with open(fname, 'r', encoding="utf-8") as dmp:
            dmp_obj = eval(dmp.read())
        return dmp_obj

class PatternManager:
    def __init__(self):
        self.patterns_config = YamlHandler(paths.patterns_config).doc
        self.patterns = {"patterns": {},
                         "fillers": []}
        self.supply = Counter()
        self.demand = self.patterns_config["Demand"]

        self.fillers_count = 0
        self.max_fillers = self.patterns_config["MaxFillers"]

    def filter_sentence(self, sentence):
        for bad_marker in [SentenceMarkers.uneven_characters, SentenceMarkers.first_is_not_word,
                           SentenceType.bad, SentenceMarkers.has_bastard, SentenceCustomMarkers.has_exception]:
            if sentence.markers[bad_marker]:
                return SentenceType.bad
        if sentence.all_words_count > 15 or sentence.all_words_count < 2:
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
        if 0 < ph_count < 4:
            gender_set = "m{}f{}".format(sentence.counters[SentenceCounters.m_placeholder], sentence.counters[SentenceCounters.f_placeholder])
            if gender_set not in self.patterns["patterns"]:
                self.patterns["patterns"][gender_set] = []
            patterns_set = self.patterns["patterns"][gender_set]
        else: return

        if sentence_string in patterns_set:
            return

        if self.supply[gender_set] >= self.demand[gender_set]:
            return
        self.supply[gender_set] += 1

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
            next_token = sentence.tokens[i + 1] if i != s_len-1 else None
            prev_token = sentence.tokens[i - 1] if i != 0 else None
            current_token.markers[TokenCustomMarkers.is_replaceable] = self.is_replaceable(current_token, next_token, prev_token)
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
                if current_token.markers[TokenCustomMarkers.is_replaceable] and next_token.markers[TokenCustomMarkers.is_replaceable]:
                    sentence.markers[SentenceType.bad] = True
        sentence.tokens = tokens_result
        sentence.calculate_meta()
        return sentence

    # placeholdering
    def create_placeholders(self, sentence):
        s_len = len(sentence.tokens)
        for i in range(s_len):
            token = sentence.tokens[i]
            if token.markers[TokenCustomMarkers.is_replaceable]:
                sentence.counters[SentenceCounters.placeholder] += 1
                sentence.counters[marker_to_SentCounter[token.gr_properties[Gender]]] += 1
                self.change_to_placeholder(token, sentence.counters[SentenceCounters.placeholder])

    def is_replaceable(self, token, next_token, prev_token):
        if token.toktype != TokenType.word:
            return False
        # temporary (Gender)
        if token.gr_properties[Case] not in [Case.nom, Case.gen, Case.acc, Case.abl]:
            return False
        if token.gr_properties[Gender] not in [Gender.m, Gender.f]:
            return False
        if token.gr_properties[Number] != Number.sg:
            return False

        if word_exceptions.is_not_plh(token.lex):
            return False

        if (next_token and next_token.text == "-") or (prev_token and prev_token.text == "-"):
            #print(prev_token.text, token.text, next_token.text)
            return False

        if token.gr_properties[HumanName]:
                return True
        if token.gr_properties[Anim] == Anim.anim:
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

def make_patterns(lm_fname=paths.lm_dump):
    PM = PatternManager()
    LM = LanguageModel(lm_fname)
    print(LM.token_dictionary.dic["другая"].markers)
    generator = PatternGenerator(LM)
    while not PM.satisfied():
        for lengths in [(3, 5), (6, 8), (8, 10)]:
            sentence = generator.generate(random.randint(*lengths))
            PM.add(sentence)
    PM.save_patterns()
    print(PM.demand)

if __name__ == "__main__":
    # create_and_save_lm()
    make_patterns()