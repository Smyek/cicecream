#!/usr/local/lib/python2.7
#coding: utf-8

import ssl
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

import vkontakte, codecs, random, re, string

token = "9ccb936cc7885c4928041db74f6235799f04e2ae673782379a6da82c80c30984f5e5b90f27702354c07f9"
CLIENT_ID = '4894606'
CLIENT_SECRET = 'ySiSE0LwXHrAq8zD9e0V'
vk = vkontakte.API('4894606', 'ySiSE0LwXHrAq8zD9e0V', token)

DATA_FOLDER = "data/"
USEDUIDS_FILE = DATA_FOLDER + "uidsUsed.txt"
WORDS_FILE = DATA_FOLDER + "words.txt"
PATTERNS_FILE = DATA_FOLDER + "patterns.txt"

def post_message(message_text, test_message=False):
    group_id = "-92940311"
    if test_message:
        group_id = "-125307022"
    vk.get(method="wall.post", message=message_text, owner_id=group_id) ## это чтоб постить от смороженного

#offset - random
def get_ids():
    randOffset = 0
    members_count = vk.get(method="groups.getById", group_id="92940311", fields=u"members_count")[0][u"members_count"]
    if members_count > 1000:
        k = int(str(members_count)[0])
        randOffset = random.randint(0,k)
    return vk.get(method="groups.getMembers", group_id="92940311", offset=randOffset)['users']

def get_random_id():
    ids = get_ids()
    randomId = str(random.choice(ids))
    return randomId

def make_username(UID, NAME):
    pattern = u"@id%s (%s)" % (UID, NAME)
    return pattern

def get_name(id, case='nom'):
    user = vk.get(method="users.get", user_ids=id, name_case=case, fields=u'first_name, last_name, sex')[0]
    name = u"%s %s" % (user[u"first_name"], user[u"last_name"])
    sexDict = {1: u"f", 2: u"m", 0: u"m", 3: u"m"}
    sex = sexDict[user[u"sex"]]
    return name, sex


class Phrase:
    def __init__(self):
        self.ids = []
        self.idsUsed = []
        self.sentence_patterns = {}
        self.gram = {}
        self.reGram = re.compile(u"(,|=)")

        self.current_id = None
        self.current_username = None

    def load_ids_fname(self, fname):
        with codecs.open(fname, "r", "utf-8") as f:
            for uid in f:
                uid = uid.strip("\r\n")
                if fname == DATA_FOLDER + "uidsNew.txt":
                    if uid != u"": self.ids.append(uid)
                elif fname == DATA_FOLDER + "uidsUsed.txt":
                    if uid != u"": self.idsUsed.append(uid)

    def update_users(self):
        self.load_ids_fname(DATA_FOLDER + "uidsUsed.txt")
        current_ids = get_ids()
        for uid in current_ids:
            uid = str(uid)
            if uid not in self.idsUsed:
                self.ids.append(uid)
        if self.ids == []:
            with codecs.open(DATA_FOLDER + "uidsUsed.txt", "w", "utf-8") as f:
                f.write(u"")
            self.ids = current_ids
            self.idsUsed = []

    def update_used_uids(self):
        self.idsUsed.append(self.current_id)
        with codecs.open(DATA_FOLDER + "uidsUsed.txt", "w", "utf-8") as f:
            f.write(u"\r\n".join([str(x) for x in self.idsUsed]))
    def load_patterns(self):
        with codecs.open(DATA_FOLDER + "patterns.txt", "r", "utf-8") as f:
            for line in f:
                self.sentence_patterns[line[:-2]] = 1

    def load_words(self):
        with codecs.open(DATA_FOLDER + "words.txt", "r", "utf-8") as f:
            for line in f:
                line = line[:-2].split(u"\t")
                gram, words = line[0], line[1:]
                self.gram[gram] = words

    def random_pattern(self):
        with codecs.open(DATA_FOLDER + "info.txt", "r", "utf-8") as f:
            index = random.randint(0, int(f.read()))
        with codecs.open(DATA_FOLDER + "patterns.txt", "r", "utf-8") as f:
            count = 0
            for pattern in f:
                if index == count: return pattern
                count += 1

    def upper_repl(self, match):
         return match.group(1) + u" " + match.group(2).upper()

    def user_link(self, match):
        return make_username(match.group(1), self.current_username)

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
                    username, sex = get_name(self.current_id, "nom")
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
    generator = Phrase()
    generator.update_users()
    phrase = generator.generate_phrase_cheap()
    post_message(phrase, True)
