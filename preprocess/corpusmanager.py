from os import listdir, rename
from collections import OrderedDict
import csv

class Document:
    def __init__(self, name, doc_path):
        self.name = name
        self.doc_path = doc_path
        self.processed = False


class CorpusManager:
    def __init__(self):
        self.corpus_path = 'data/corpus/'
        self.config_path = 'data/config.csv'
        self.corpus_documents = {}
        self.config = {}

        self.get_corpus_documents()
        self.load_config()

    def get_corpus_documents(self):
        for filename in listdir(self.corpus_path):
            name = filename.replace(".txt", "")
            doc_path = self.corpus_path + filename
            document = Document(name, doc_path)
            self.corpus_documents[name] = document
        self.corpus_documents = OrderedDict(sorted(self.corpus_documents.items(), key=lambda t: t[0]))

    def in_corpus(self, name):
        if name in self.corpus_documents:
            return True
        return False

    def load_config(self):
        with open(self.config_path, 'r', encoding="utf-8") as csvfile:
            config_reader = csv.DictReader(csvfile, delimiter=';')
            for document in config_reader:
                if not self.in_corpus(document["name"]):
                    continue
                processed = True if document["processed"] == "1" else False
                self.corpus_documents[document["name"]].processed = processed

    def save_config(self):
        with open(self.config_path, 'w', encoding="utf-8", newline="") as csvfile:
            writer = csv.writer(csvfile, delimiter=';', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["name", "processed"])
            for name in self.corpus_documents:
                document = self.corpus_documents[name]
                processed = "1" if document.processed else "0"
                document_data = [document.name, processed]
                writer.writerow(document_data)

    def normalize_filenames(self):
        symbols = ("абвгдеёжзийклмнопрстуфхцчшщъыьэюя ",
                   "abvgdeejzijklmnoprstufhzcss_y_eua_")

        tr = {ord(a):ord(b) for a, b in zip(*symbols)}
        for filename in listdir(self.corpus_path):
            normalized_filename = filename.lower().translate(tr)
            rename(self.corpus_path + filename, self.corpus_path + normalized_filename)

    #if you need to mark all documents as unprocessed to iterate through them
    def mark_all_as_unprocessed(self):
        for name in self.corpus_documents:
            document = self.corpus_documents[name]
            document.processed = False

    def iterate_documents(self, process_all=False):
        for name in self.corpus_documents:
            document = self.corpus_documents[name]
            if not document.processed or process_all:
                yield document

if __name__ == "__main__":
    _CM = CorpusManager()
    for doc in _CM.iterate_documents():
        print(doc.name)
    _CM.save_config()