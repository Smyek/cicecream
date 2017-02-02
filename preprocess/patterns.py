from corpusmanager import CorpusManager
from text_refiner import TxtRefiner
import subprocess, json, operator, random, shutil, re, os
from collections import Counter, defaultdict
class DataManager:
    def __init__(self, process_all_corpus=False, mystem_all=False, refine_all=False):
        #params
        self.process_all = process_all_corpus
        self.mystem_all = mystem_all
        self.refine_all = refine_all

        #paths
        self._data_path = 'data\\'
        self._mystem_output_folder_path = self._data_path + "mystem_output\\"
        self.exceptions_path = self._data_path + 'exceptions.txt'
        self.mystem_path = self._data_path + 'mystem'
        #self.mystem_input_path = self._data_path + 'input.txt'
        self.mystem_output_path = self._mystem_output_folder_path + '%s_mystem.json'
        self.refined_folder_path = self._data_path + "refined_texts\\"
        self.refined_text_path = self.refined_folder_path + '%s_ref.txt'

        #data
        self.exceptions = []

        #init
        self.corpus = CorpusManager()
        self.refiner = TxtRefiner()
        self.load_exceptions()
        self.prepare_documents()

    def load_exceptions(self):
        with open(self.exceptions_path, "r", encoding="utf-8") as f:
            for line in f:
                self.exceptions.append(line.strip())

    def initiate_mystem(self, document):
        input_path = self.refined_text_path % document.name
        output_path = self.mystem_output_path % document.name
        if os.path.isfile(output_path) and not self.mystem_all: return
        command = u"%s -c -s -d --eng-gr --format json < %s > %s" % (self.mystem_path, input_path, output_path)
        print(command)
        command = command.split()
        #proc = subprocess.call(command, shell=True)
        subprocess.Popen(command).wait()
        #print(proc)

    def refine_text(self, document):
        output_path = self.refined_text_path % document.name
        if os.path.isfile(output_path) and not self.refine_all: return
        with open(document.doc_path, "r", encoding="utf-8") as docfile:
            text = docfile.read()
        text = self.refiner.refine_text(text)
        with open(output_path, "w", encoding="utf-8") as docfile_refined:
            docfile_refined.write(text)

    def prepare_documents(self):
        for document in self.corpus.iterate_documents(self.process_all):
            #shutil.copy2(document.doc_path, self.mystem_input_path)
            self.refine_text(document)
            self.initiate_mystem(document)

class PatternGenerator:
    def __init__(self):
        process_all_corpus = False
        mystem_all = True
        refine_all = True
        self.dm = DataManager(process_all_corpus, mystem_all, refine_all)

        self.mystem = [[]]
        self.gram = {}
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


    #возвращает true, если записываем гр. разбор а не слово
    def gram_check(self, gram):
        if self.reGram.split(gram[:6])[0] in [u"S", u"A", u"V", u"ANUM", u"NUM", u"SPRO"]:
            return True
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

    def count_mystem_grams(self, mystem_path):
        with open(mystem_path, "r", encoding="utf-8") as f:
            mystem_content = f.read().strip()
            mystem_json = json.loads(mystem_content)
            print(mystem_json)
            for key in mystem_json:
                print(key)
                self.process_mystem_entry(key)

    def process_documents(self):
        for document in self.dm.corpus.iterate_documents(self.dm.process_all):
            print("Processing %s..." % document.name)
            mystem_path = self.dm.mystem_output_path % document.name
            self.count_mystem_grams(mystem_path)


    # def update_dataset(self, hard_reset=False, files_=False):
    #     if not hard_reset:
    #         pass
    #         # self.load_patterns()
    #         # self.load_words()
    #     if files_:
    #         return self.process_documents()


if __name__ == "__main__":
    pg = PatternGenerator()
    pg.process_documents()
    #pg.update_dataset(hard_reset=True)