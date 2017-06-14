from os import listdir, rename
from collections import OrderedDict
from sttk import TextHandlerUnit
import yaml
import dill as pickle

class Document:
    def __init__(self, name, doc_path):
        self.name = name
        self.doc_path = doc_path
        self.processed = False

    def get_text(self):
        with open(self.doc_path, "r", encoding="utf-8") as f:
            return f.read()

    def save(self):
        thu = 0
        with open("dump.pkl", 'wb') as output:
            pickle.dump(thu, output)


class CorpusManager:
    def __init__(self):
        self.corpus_path = 'data/corpus/'
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
        for filename in listdir(self.corpus_path):
            name = filename.replace(".txt", "")
            doc_path = self.corpus_path + filename
            document = Document(name, doc_path)
            self.documents[name] = document
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
    for i, s in thu.iterate_sentences():
        print(s.get_sentence_string())