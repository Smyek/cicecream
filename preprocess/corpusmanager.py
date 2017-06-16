from os import listdir, rename
from collections import OrderedDict
import os
from sttk import TextHandlerUnit
import dill as pickle

from paths import paths

class Document:
    def __init__(self, fname):
        self.name = fname.replace(".txt", "")
        self.doc_path = paths.corpus_file(fname)
        self.dump_path = paths.corpus_file(self.name + ".pkl", raw=False)
        self.processed = os.path.isfile(self.dump_path)

    def get_text(self):
        with open(self.doc_path, "r", encoding="utf-8") as f:
            return f.read()

    def save(self, thu):
        dump_dictionary = {"ngr": thu.NGR_VOCABULARIES, "tokdic": thu.token_dictionary}
        with open(self.dump_path, 'wb') as output:
            pickle.dump(dump_dictionary, output)

    def get_dump(self):
        print("getting dump {}".format(self.dump_path))
        with open(self.dump_path, 'rb') as dmp:
            dmp_obj = pickle.load(dmp)
        return dmp_obj

class CorpusManager:
    def __init__(self):
        self.documents = {}
        self.corpusmeta = {}

        self.get_corpus_documents()

    def __getitem__(self, item):
        if item in self.documents:
            return self.documents[item]
        else:
            print("There is no document named '{}'".format(item))

    def __iter__(self):
        return (x for x in self.documents.values())

    def get_corpus_documents(self):
        for filename in listdir(paths.corpus_raw):
            document = Document(filename)
            self.documents[document.name] = document
        self.documents = OrderedDict(sorted(self.documents.items(), key=lambda t: t[0]))

    def normalize_filenames(self):
        symbols = ("абвгдеёжзийклмнопрстуфхцчшщъыьэюя ",
                   "abvgdeejzijklmnoprstufhzcss_y_eua_")

        tr = {ord(a):ord(b) for a, b in zip(*symbols)}
        for filename in listdir(self.corpus_path):
            normalized_filename = filename.lower().translate(tr)
            rename(self.corpus_path + filename, self.corpus_path + normalized_filename)

    def iterate_documents(self, process_all=False):
        for name in self.documents:
            document = self.documents[name]
            if not document.processed or process_all:
                yield document

corpus_manager = CorpusManager()

if __name__ == "__main__":
    # for doc in corpus_manager.iterate_documents():
    #     print(doc.name)
    doc = corpus_manager[list(corpus_manager.documents.keys())[0]]
    thu = TextHandlerUnit()
    thu.process(doc.get_text())