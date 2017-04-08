#coding: utf-8

from utils import server_log
from utils import database as database_users
from utils import project_paths
from utils import server_config

import vk, random, re, string

WORDS_FILE = project_paths.data_file("words.txt")
PATTERNS_FILE = project_paths.data_file("patterns.txt")

class VKManager:
    def __init__(self):
        self._API_DATA = {}
        self.load_api_data()
        self.session = vk.Session(access_token=self._API_DATA["token"])
        self.vk = vk.API(self.session)

    def load_api_data(self):
        with open(project_paths.data_file("apidata.csv"), "r", encoding="utf-8") as f:
            data_rows = f.read().split("\n")
            for row in data_rows:
                key, value = row.split(";")
                self._API_DATA[key] = value

    # post vk via smorozhenoe group
    def post_message(self, message_text):
        group_id = "-92940311"
        if server_config.is_test:
            group_id = "-125307022"
        self.vk.get(method="wall.post", message=message_text, owner_id=group_id)

    def get_ids(self, group_id="92940311"):
        uids = []
        members_count = self.vk.get(method="groups.getById", group_id=group_id, fields="members_count")[0]["members_count"]
        for offset in range(0, members_count, 1000):
            uids += self.vk.get(method="groups.getMembers", group_id=group_id, offset=offset)['users']
        return uids

    def get_name(self, id, case='nom'):
        user = self.vk.get(method="users.get", user_ids=id, name_case=case, fields='first_name, last_name, sex')[0]
        name = "%s %s" % (user["first_name"], user["last_name"])
        sexDict = {1: "f", 2: "m", 0: "m", 3: "m"}
        sex = sexDict[user["sex"]]
        return name, sex

class UserManager:
    def __init__(self, vkm):
        self.vk = vkm

        #load
        self.group_uids = self.vk.get_ids()
        database_users.update_users(self.group_uids)

        #selections
        self.never_used = self.find_never_used()
        self.not_used_on_cycle = self.find_not_used_on_cycle()

        #choose
        self.result_selection = self.choose_selection()

        #log
        self.log()

    def add_to_used(self, id):
        database_users.increment_user_used(id)

    def find_never_used(self):
        return list(set(self.group_uids) & set(database_users.get_never_used_uids()))

    def find_not_used_on_cycle(self):
        return list(set(self.group_uids) & set(database_users.get_not_used_oncycle_uids()))

    def choose_selection(self):
        for selection_id, selection in [("never_used", self.never_used),
                                        ("not_used_on_cycle", self.not_used_on_cycle),
                                        ("group_uids", self.group_uids)]:
            if selection:
                server_log.add_key_value_log("chosen selection", selection_id)

                #clear not_used_on_cycle because all users were used on this cycle
                if selection_id == "group_uids":
                    self.used_uids = []
                return selection

    def choose_random_uid(self):
        uid = random.choice(self.result_selection)
        server_log.add_key_value_log("chosen uid", "%s (https://vk.com/id%s)" % (uid,uid))
        return uid

    def log(self):
        for selection_id, selection in [("never_used", self.never_used),
                                        ("not_used_on_cycle", self.not_used_on_cycle),
                                        ("group_uids", self.group_uids)]:
            server_log.add_key_value_log(selection_id, "%s uids" % len(selection))


class PhraseGenerator:
    def __init__(self):
        self.sentence_patterns = {}
        self.gram = {}
        self.reGram = re.compile("(,|=)")

        self.current_id = None
        self.current_username = None

        self.vk = VKManager()
        self.user_manager = UserManager(self.vk)

        self.load_words()

    def load_patterns(self):
        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                self.sentence_patterns[line[:-2]] = 1

    def load_words(self):
        with open(WORDS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip().split("\t")
                gram, words = line[0], line[1:]
                self.gram[gram] = words

    def random_pattern(self):
        with open(project_paths.data_file("info.txt"), "r", encoding="utf-8") as f:
            index = random.randint(0, int(f.read()))
            server_log.add_key_value_log("pattern", index+1)
        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            count = 0
            for pattern in f:
                if index == count: return pattern
                count += 1

    def upper_repl(self, match):
         return match.group(1) + " " + match.group(2).upper()

    def make_username(self, UID, NAME):
        pattern = "@id%s (%s)" % (UID, NAME)
        return pattern

    def user_link(self, match):
        return self.make_username(match.group(1), self.current_username)

    def phrase_refine(self, phrase):
        phrase = " ".join(phrase)# + "."
        phrase = re.sub(" ?-? ?-\.?$", "", phrase)
        phrase = re.sub("^--? ?", "", phrase)
        phrase = re.sub("- ?-", "—", phrase)
        phrase = re.sub("</? >", "", phrase)
        phrase = re.sub("([«\"]) ?(.+?) ?([»\"])", "\\1\\2\\3", phrase)
        phrase = re.sub("([^" + string.punctuation + "]) ([" + string.punctuation + "])", "\\1\\2", phrase)
        phrase = re.sub("(@[^" + string.punctuation + "]+?) ([" + string.punctuation + "])", "\\1\\2", phrase)
        phrase = re.sub("(@[^" + string.punctuation.replace("_", "") + "]+?)-", "\\1 -", phrase)
        phrase = re.sub("(.)@", "\\1 @", phrase)
        phrase = re.sub(" ?\( ", " (", phrase)
        phrase = re.sub("- то([ ?!.])", "-то\\1", phrase)
        phrase = re.sub("([А-Яа-яЁё])- ", "\\1 - ", phrase)

        phrase = re.sub("([^\"]*?)\"([^\"]*?)", "\\1\\2", phrase)
        phrase = re.sub("([^\(]*?)\(([^\(]*?)", "\\1\\2", phrase)
        phrase = re.sub("([^\)]*?)\)([^\)]*?)", "\\1\\2", phrase)


        phrase = phrase[0].upper() + phrase[1:]
        phrase = re.sub("([!.?] ?)([а-яё])", self.upper_repl, phrase) #здесь нужно сделать функцию которая повышает регистр буквы после знака конца предложения в его середине
        phrase = re.sub("(\r)?\n", "", phrase)
        # phrase = re.sub("^@", "… @", phrase)
        phrase = re.sub(" +", " ", phrase)
        phrase = re.sub("[Ii]d([0-9]+)", self.user_link, phrase)
        return phrase.strip()

    def word_modifier(self, word, gram):
        for gr in ["persn", "famn", "patrn", "geo"]:
            if gr in gram:
                word = word[0].upper() + word[1:]
        return word

    def generate_phrase_cheap(self, username=None, sex=None):
        phrase = []
        pattern = self.random_pattern().strip().split("_+_")
        for gram in pattern:
            if "<username>" in gram:
                if username is None:
                    self.current_id = self.user_manager.choose_random_uid()
                    username, sex = self.vk.get_name(self.current_id, "nom")
                if ",%s," % sex not in gram: return self.generate_phrase_cheap(username, sex)
                phrase.append("id" + str(self.current_id)) #make_username(self.current_id, username)
                self.current_username = username
                continue
            if gram not in self.gram: return self.generate_phrase_cheap(username, sex)
            word = self.word_modifier(random.choice(self.gram[gram]), gram)
            phrase.append(word)
        phrase = self.phrase_refine(phrase)
        if (len(phrase) > 260) or (len(phrase.split()) < 8):
            return self.generate_phrase_cheap(username, sex)
        self.user_manager.add_to_used(self.current_id)
        return phrase

def run_generation_job():
    generator = PhraseGenerator()
    phrase = generator.generate_phrase_cheap()
    generator.vk.post_message(phrase)
    return phrase

if __name__ == "__main__":
    success = False
    while not success:
        try:
            phrase = run_generation_job()
            server_log.add_log(phrase)
            server_log.add_time_elapsed()
            success = True
        except ValueError as err:
            server_log.add_log(str(err))