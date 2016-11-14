#!/usr/local/lib/python2.7
#coding: utf-8

import ssl
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

import vkontakte, codecs, random, re, string

DATA_FOLDER = "data/"
USEDUIDS_FILE = DATA_FOLDER + "uidsUsed.txt"
WORDS_FILE = DATA_FOLDER + "words.txt"
PATTERNS_FILE = DATA_FOLDER + "patterns.txt"

class VKManager:
    def __init__(self):
        self._API_DATA = {}
        self.load_api_data()
        self._TOKEN = self._API_DATA["token"]
        self._CLIENT_ID = self._API_DATA["client_id"]
        self._CLIENT_SECRET = self._API_DATA["client_secret"]

        self.vk = vkontakte.API(self._CLIENT_ID, self._CLIENT_SECRET, self._TOKEN)

        self._TEST_MODE = True

    def load_api_data(self):
        with codecs.open(DATA_FOLDER + "apidata.csv", "r", "utf-8") as f:
            data_rows = f.read().split("\r\n")
            for row in data_rows:
                key, value = row.split(";")
                self._API_DATA[key] = value

    def load_config(self):
        with codecs.open(DATA_FOLDER + "config.csv", "r", "utf-8") as f:
            data_rows = f.read().split("\r\n")
            for row in data_rows:
                key, value = row.split(";")
                if key == "test_mode":
                    self._TEST_MODE = "True" == value

    def post_message(self, message_text):
        group_id = "-92940311"
        if self._TEST_MODE:
            group_id = "-125307022"
        self.vk.get(method="wall.post", message=message_text, owner_id=group_id) ## это чтоб постить от смороженного

    def get_ids(self, group_id="92940311"):
        uids = []
        members_count = self.vk.get(method="groups.getById", group_id=group_id, fields=u"members_count")[0][u"members_count"]
        for offset in range(0, members_count, 1000):
            uids += self.vk.get(method="groups.getMembers", group_id=group_id, offset=offset)['users']
        return uids

    def get_name(self, id, case='nom'):
        user = self.vk.get(method="users.get", user_ids=id, name_case=case, fields=u'first_name, last_name, sex')[0]
        name = u"%s %s" % (user[u"first_name"], user[u"last_name"])
        sexDict = {1: u"f", 2: u"m", 0: u"m", 3: u"m"}
        sex = sexDict[user[u"sex"]]
        return name, sex



class PhraseGenerator:
    def __init__(self):
        self.ids = []
        self.idsUsed = []
        self.sentence_patterns = {}
        self.gram = {}
        self.reGram = re.compile(u"(,|=)")

        self.current_id = None
        self.current_username = None

        self.vk = VKManager()

    def load_ids_fname(self, fname):
        with codecs.open(fname, "r", "utf-8") as f:
            uids = f.read().split("\r\n")
        for uid in uids:
            if fname == DATA_FOLDER + "uidsNew.txt":
                if uid != u"": self.ids.append(uid)
            elif fname == USEDUIDS_FILE:
                if uid != u"": self.idsUsed.append(uid)

    def update_users(self):
        self.load_ids_fname(USEDUIDS_FILE)
        current_ids = self.vk.get_ids()
        for uid in current_ids:
            uid = str(uid)
            if uid not in self.idsUsed:
                self.ids.append(uid)
        if self.ids == []:
            with codecs.open(USEDUIDS_FILE, "w", "utf-8") as f:
                f.write(u"")
            self.ids = current_ids
            self.idsUsed = []

    def remove_user_from_used_uids(self, userid):
        '''userid can be a list'''
        if not isinstance(userid, list): userid = [userid]
        for id in userid:
            if id in self.idsUsed:
                self.idsUsed.remove(id)
        self.update_used_uids(False)

    def update_used_uids(self, write_current=True):
        '''Write current user Default. Don't Write, while updating without saving current'''
        if write_current:
            self.idsUsed.append(self.current_id)
        with codecs.open(USEDUIDS_FILE, "w", "utf-8") as f:
            f.write(u"\r\n".join([str(x) for x in self.idsUsed]))

    def load_patterns(self):
        with codecs.open(PATTERNS_FILE, "r", "utf-8") as f:
            for line in f:
                self.sentence_patterns[line[:-2]] = 1

    def load_words(self):
        with codecs.open(WORDS_FILE, "r", "utf-8") as f:
            for line in f:
                line = line[:-2].split(u"\t")
                gram, words = line[0], line[1:]
                self.gram[gram] = words

    def random_pattern(self):
        with codecs.open(DATA_FOLDER + "info.txt", "r", "utf-8") as f:
            index = random.randint(0, int(f.read()))
        with codecs.open(PATTERNS_FILE, "r", "utf-8") as f:
            count = 0
            for pattern in f:
                if index == count: return pattern
                count += 1

    def upper_repl(self, match):
         return match.group(1) + u" " + match.group(2).upper()

    def make_username(self, UID, NAME):
        pattern = u"@id%s (%s)" % (UID, NAME)
        return pattern

    def user_link(self, match):
        return self.make_username(match.group(1), self.current_username)

    def phrase_refine(self, phrase):
        phrase = u" ".join(phrase)# + "."
        phrase = re.sub(u" ?-? ?-\.?$", u"", phrase)
        phrase = re.sub(u"^--? ?", u"", phrase)
        phrase = re.sub(u"- ?-", u"—", phrase)
        phrase = re.sub(u"</? >", u"", phrase)
        phrase = re.sub(u"([«\"]) ?(.+?) ?([»\"])", u"\\1\\2\\3", phrase)
        phrase = re.sub(u"([^" + string.punctuation + u"]) ([" + string.punctuation + "])", u"\\1\\2", phrase)
        phrase = re.sub(u"(@[^" + string.punctuation + u"]+?) ([" + string.punctuation + u"])", u"\\1\\2", phrase)
        phrase = re.sub(u"(@[^" + string.punctuation.replace(u"_", u"") + u"]+?)-", u"\\1 -", phrase)
        phrase = re.sub(u"(.)@", u"\\1 @", phrase)
        phrase = re.sub(u" ?\( ", u" (", phrase)
        phrase = re.sub(u"- то([ ?!.])", u"-то\\1", phrase)
        phrase = re.sub(u"([А-Яа-яЁё])- ", u"\\1 - ", phrase)

        phrase = re.sub(u"([^\"]*?)\"([^\"]*?)", u"\\1\\2", phrase)
        phrase = re.sub(u"([^\(]*?)\(([^\(]*?)", u"\\1\\2", phrase)
        phrase = re.sub(u"([^\)]*?)\)([^\)]*?)", u"\\1\\2", phrase)


        phrase = phrase[0].upper() + phrase[1:]
        phrase = re.sub(u"([!.?] ?)([а-яё])", self.upper_repl, phrase) #здесь нужно сделать функцию которая повышает регистр буквы после знака конца предложения в его середине
        phrase = re.sub(u"(\r)?\n", u"", phrase)
        # phrase = re.sub(u"^@", u"… @", phrase)
        phrase = re.sub(u" +", u" ", phrase)
        phrase = re.sub(u"[Ii]d([0-9]+)", self.user_link, phrase)
        return phrase.strip()

    def word_modifier(self, word, gram):
        for gr in [u"persn", u"famn", u"patrn", u"geo"]:
            if gr in gram:
                word = word[0].upper() + word[1:]
        return word

    def generate_phrase_cheap(self, username=None, sex=None):
        self.load_words()
        phrase = []
        pattern = self.random_pattern()[:-2].split(u"_+_")
        for gram in pattern:
            if u"<username>" in gram:
                if username is None:
                    self.current_id = random.choice(self.ids)
                    username, sex = self.vk.get_name(self.current_id, "nom")
                if u",%s," % sex not in gram: return self.generate_phrase_cheap(username, sex)
                phrase.append(u"id" + str(self.current_id)) #make_username(self.current_id, username)
                self.current_username = username
                continue
            if gram not in self.gram: return self.generate_phrase_cheap(username, sex)
            word = self.word_modifier(random.choice(self.gram[gram]), gram)
            phrase.append(word)
        phrase = self.phrase_refine(phrase)
        if (len(phrase) > 260) or (len(phrase.split()) < 8):
            return self.generate_phrase_cheap(username, sex)
        self.update_used_uids()
        return phrase

if __name__ == "__main__":
    generator = PhraseGenerator()
    generator.update_users()
    phrase = generator.generate_phrase_cheap()
    generator.vk.post_message(phrase)
