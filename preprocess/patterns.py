from collections import defaultdict, Counter
import random
import copy
import dill as pickle

from sttk import TextHandlerUnit
from sttk import tf_lex, SF_Safe_Russian_NoDlg
from sttk import tf_default
from sttk import TokenMarkers, TokenType
from sttk import POS, Gender, Number, Case, Other, HumanName

from sttk import Sentence

from corpusmanager import corpus_manager

lm_dump = "LM_sicecream.pkl"

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
    def __init__(self, lm_dump_name=None):
        if lm_dump_name is None:
            self.tokfilter = tf_default
            self.max_ngram_len = 8
            self.lmd = defaultdict(Counter)

            self.NGR_VOCABULARIES = None
            self.token_dictionary = None

            self.process_corpus()
        else:
            print("LM dump loading..")
            dmp = self.get_dump(lm_dump_name)
            #self.__dict__.update(dmp.__dict__)

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

    def save_model(self, fname=lm_dump):
        with open(fname, 'wb') as output:
            pickle.dump(self, output)

    def save_obj(self, fname, obj_to_save):
        with open(fname, 'wb') as output:
            pickle.dump(obj_to_save, output)

    def get_dump(self, fname):
        with open(fname, 'rb') as dmp:
            dmp_obj = pickle.load(dmp)
        return dmp_obj


class PatternGenerator:
    def __init__(self, lm):
        self.lm = lm
        self.placeholder_tokens = ["он", "она"]
        #self.placeholder_markers = [Other.persn, Other.famn, Other.patrn]
        self.placeholder = "<usr,{},{}|{}>"

    def generate(self, length=12):
        sentence = self.generate_raw(length)
        sentence = self.refine(sentence)
        self.create_placeholders(sentence)
        return sentence

    def generate_raw(self, length):
        history = ["."]
        # history = [".", "Андрея"]
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
                sentence.counters["placeholders"] += 1
                self.change_to_placeholder(token)

    def is_replaceable(self, token):
        if token.toktype != TokenType.word:
            return False
        # temporary
        if token.gr_properties[Case] != Case.nom:
            return False
        if token.gr_properties[HumanName]:
                return True
        for tok_text in self.placeholder_tokens:
            if token.text.lower() == tok_text:
                return True
        return False

    def change_to_placeholder(self, token):
        gender = token.gr_properties[Gender].name
        case = token.gr_properties[Case].name
        token.text = self.placeholder.format(gender, case, token.text)

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

LM = LanguageModel()
generator = PatternGenerator(LM)
# LM.save_thu()
#LM.save_model()
# exit()
for i in range(100):
    result = generator.generate()
    print(result.get_str())
    print(result.counters["placeholders"])
    # for tok in result.tokens:
    #     if tok.gr:
    #         print(tok.text, tok.get_info())

