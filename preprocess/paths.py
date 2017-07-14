import os

class Paths:
    def __init__(self):
        self.wd = os.path.dirname(os.path.realpath(__file__))
        self.service = os.path.join(self.wd, "service")
        self.data = os.path.join(self.wd, "data")
        self.temp = os.path.join(self.wd, "temp")

        # constant
        # dirs
        self.output = os.path.join(self.data, "output")
        self.corpus = os.path.join(self.data, "corpus")
        self.corpus_raw = os.path.join(self.corpus, "raw")
        self.corpus_processed = os.path.join(self.corpus, "processed")

        #files
        self.lm_dump = self.service_file("LM_sicecream.pkl")
        self.patterns = self.output_file("patterns.yaml")

        self.lmd_simple = self.service_file("LMD_Simple.txt")

        #datafiles
        self.fixlist = self.data_file("fixlist.txt")
        self.exceptions = self.data_file("exceptions.yaml")

    def root_file(self, filename):
        return os.path.join(self.wd, filename)

    def service_file(self, filename):
        return os.path.join(self.service, filename)

    def data_file(self, filename):
        return os.path.join(self.data, filename)

    def output_file(self, filename):
        return os.path.join(self.output, filename)

    def temp_file(self, filename):
        return os.path.join(self.temp, filename)

    def corpus_file(self, filename, raw=True):
        if raw:
            return os.path.join(self.corpus_raw, filename)
        else:
            return os.path.join(self.corpus_processed, filename)

paths = Paths()