#coding:utf-8
from corpusmanager import CorpusManager
import subprocess, json, operator, random, shutil, re, os
class DataManager:
    def __init__(self, process_all_corpus=False, mystem_all=False):
        #params
        self.process_all = process_all_corpus
        self.mystem_all = mystem_all

        #paths
        self._data_path = 'data/'
        self._mystem_output_folder_path = self._data_path + "mystem_output/"
        self.exceptions_path = self._data_path + 'exceptions.txt'
        self.mystem_path = self._data_path + 'mystem'
        self.mystem_input_path = self._data_path + 'input.txt'
        self.mystem_output_path = self._mystem_output_folder_path + '%s_mystem.json'

        #data
        self.exceptions = []

        #init
        self.corpus = CorpusManager()
        self.load_exceptions()

    def load_exceptions(self):
        with open(self.exceptions_path, "r", encoding="utf-8") as f:
            for line in f:
                self.exceptions.append(line.strip())

    def initiate_mystem(self, document_name):
        output_path = self.mystem_output_path % document_name
        if os.path.isfile(output_path) and not self.mystem_all: return
        command = u"%s -dig -c -s -d --eng-gr --format json < %s > %s" % (self.mystem_path, self.mystem_input_path, output_path)
        command = command.split()
        proc = subprocess.call(command, shell=True)
        print(proc)

    def mystem_documents(self):
        for document in self.corpus.iterate_documents(self.process_all):
            shutil.copy2(document.doc_path, self.mystem_input_path)
            self.initiate_mystem(document.name)

class PatternGenerator:
    def __init__(self):
        self.dm = DataManager()

        self.mystem = [[]]
        self.gram = {}
        # self.words_info = {} #сюда добавляется вся информация про то сколько раз и где нграммы встретились
        # self.sentence_patterns = {}
        # self.sentence_length_dict = {}
        # self.nicknames = []
        #
        # self.current_file = ""
        # self.patterns_amount = 0
        # self.words_amount = 0
        #
        self.reGram = re.compile("(,|=)")
        # self.rePunctuationFix = re.compile(" ([.,?!])")
        # self.rePunctuationFix_2 = re.compile("([.?!])( -\.|\.|\"\.?)")
        # self.reSpeechFix = re.compile(" :\" ")
        #
        # self.rePersnFix = re.compile(",(persn|famn)")

    #берет список списков предложений (self.mystem) и делает n шаблонов предложений, записывает в self.sentence_patterns
    def refine_sentence_patterns(self):
        for sent in self.mystem:
            # print sent, "sentence"
            if self.sentence_check(sent, len(sent)): continue
            self.patterns_length(len(sent))
            sent = u"_+_".join(sent)
            if sent in self.sentence_patterns:
                self.sentence_patterns[sent] += 1
            else:
                self.sentence_patterns[sent] = 1

    #удаляет последний паттерн в process_mystem_entry, если не соответствует необходимым параметрам
    def accept_sentence(self):
        sentence = self.mystem[-1]
        for gr in sentence:
            grams = self.reGram.split(gr)
            if grams[0] in [u"S", u"SPRO"]:
                if (u'nom' in grams) and (u'sg' in grams)and (u'anim' in grams):
                    return
        self.mystem.pop()

    def gram_process(self, text, gram):
        if gram not in self.gram:
            self.gram[gram] = [text, ]
        else:
            if text not in self.gram[gram]:
                self.gram[gram].append(text)

    #true, if write grams not word
    def gram_check(self, gram):
        if self.reGram.split(gram[:6])[0] in [u"S", u"A", u"V", u"ANUM", u"NUM", u"SPRO"]:
            return True
        return False

    #true, if a word is an exception
    def word_exceptions(self, lex, gram):
        if lex in self.dm.exceptions:
            # print lex, gram
            return True
        if (u"abbr" in gram) or (u"obsc" in gram) or (u"inform" in gram) or (u"rare" in gram):
            #print lex, gram
            return True
        if u"#" in lex: return True
        return False

    def process_mystem_entry(self, entry):
        if "analysis" in entry:
            if entry["analysis"] == []: return
            gram = entry["analysis"][0]['gr']
            if self.word_exceptions(entry["analysis"][0]['lex'], gram): return
            if self.gram_check(gram):
                self.gram_process(entry["text"].lower(), gram)
                self.mystem[-1].append(gram) #добавляем в последний список разбор
            else:
                self.gram_process(entry["text"].strip(), entry["text"].strip())
                self.mystem[-1].append(entry['text'].strip())
        else:
            if entry['text'] in [u"\s", "\n"]:
                self.accept_sentence()
                self.username_include()
                self.modify_sentence()
                self.mystem.append([])
            elif (entry['text'] == u" "): return
            else:
                self.gram_process(entry["text"].strip(), entry["text"].strip())
                self.mystem[-1].append(entry['text'].strip())

    def load_mystem_array(self, mystem_path):
        with open(mystem_path, "r", encoding="utf-8") as f:
            for line in f:
                a = json.loads(line.strip())
                for key in a:
                    self.process_mystem_entry(key)

    def process_documents(self):
        for document in self.dm.corpus.iterate_documents(self.dm.process_all):
            mystem_path = self.dm.mystem_output_path % document
            self.load_mystem_array(mystem_path)
            self.refine_sentence_patterns()
        self.exclude_rare_patterns()
        self.save_patterns_and_words()

    def update_dataset(self, hard_reset=False, files_=False):
        if not hard_reset:
            pass
            # self.load_patterns()
            # self.load_words()
        if files_:
            return self.process_documents()


if __name__ == "__main__":
    pg = PatternGenerator()
    pg.update_dataset(hard_reset=True)