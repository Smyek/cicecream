#!/usr/bin/python3.5
#coding: utf-8

from collections import Counter

from utils import server_log
from utils import database as database_users
from utils import project_paths
from utils import server_config
from utils import YamlHandler
from utils import GenderSet
from utils import backups, users_autosave

import vk, random, re

pattern_user = re.compile("(<usr[0-9]+?,([mf]),(....?)\|(.+?)>)")

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
        if server_config.is_test():
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
        genderDict = {1: "f", 2: "m", 0: "m", 3: "m"}
        gender = genderDict[user["sex"]]
        return name, gender

class UserManager:
    def __init__(self):

        #load
        self.group_uids = vkm.get_ids()
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
        user_pack = UserPack([VKUser(uid)])
        return user_pack

    def log(self):
        for selection_id, selection in [("never_used", self.never_used),
                                        ("not_used_on_cycle", self.not_used_on_cycle),
                                        ("group_uids", self.group_uids)]:
            server_log.add_key_value_log(selection_id, "%s uids" % len(selection))

class VKUser:
    def __init__(self, uid):
        self.uid = uid
        self.name, self.gender = vkm.get_name(uid)
        self.case = "nom"
        self.msg_link = "@id{} ({})".format(self.uid, self.name)

    def vk_link(self, UID, NAME):
        pattern = "@id{} ({})".format(UID, NAME)
        return pattern

    def change_case(self, case):
        self.name, self.gender = vkm.get_name(self.uid, case)
        self.msg_link = "@id{} ({})".format(self.uid, self.name)
        self.case = case

    def __eq__(self, other):
        if self.gender == other.gender:
            return True
        return False

class UserPack:
    def __init__(self, users_list):
        self.list = users_list
        self.gender_set = GenderSet(users_list)

    def __iter__(self):
        return (x for x in self.list)

class Placeholder:
    def __init__(self, placeholder_reg_result):
        self.plh_string, self.gender, self.case, self.original = placeholder_reg_result

    def __eq__(self, other):
        if self.gender == other.gender:
            return True
        return False

class Pattern:
    def __init__(self, pattern):
        self.text = pattern
        self.placeholders = [Placeholder(plh) for plh in pattern_user.findall(self.text)]

    def insert_users(self, users):
        users_count = len(users)
        for user in users:
            for plh in self.placeholders:
                if user == plh:
                    if plh.case != user.case:
                        user.change_case(plh.case)
                    self.text = self.text.replace(plh.plh_string, user.msg_link)
                    break

        #clear
        if users_count < len(self.placeholders):
            for plh in self.placeholders:
                self.text = self.text.replace(plh.plh_string, "")


class PatternsManager:
    def __init__(self):
        self.current_id = None
        self.current_username = None

        self.max_pick_patterns_attempts = 20
        self.patterns = YamlHandler(project_paths.patterns)
        if not project_paths.is_file(project_paths.used_patterns):
            with open(project_paths.used_patterns, "w", encoding="utf-8") as f:
                f.write('Used_Patterns: []')
        self.used_patterns = YamlHandler(project_paths.used_patterns)

    def pick_pattern(self, user_pack, attempts=0):
        if attempts > self.max_pick_patterns_attempts:
            server_log.add_log("clear_used_patterns")
            self.clear_used_patterns()
            self.pick_pattern(user_pack, 0)

        gender_set = user_pack.gender_set.str
        random_pattern = random.choice(self.patterns.doc["patterns"][gender_set])

        if random_pattern in self.used_patterns.doc["Used_Patterns"]:
            attempts += 1
            server_log.add_log("Pattern already used.")
            return self.pick_pattern(user_pack, attempts)

        random_pattern = Pattern(random_pattern)
        server_log.add_log("Pattern pick attempt: {}".format(attempts))
        return random_pattern

    def clear_used_patterns(self):
        self.used_patterns.doc = {"Used_Patterns": []}
        self.used_patterns.save_doc()

    def add_pattern_to_used(self, pattern):
        self.used_patterns.doc["Used_Patterns"].append(pattern)
        self.used_patterns.save_doc()

    def generate_phrase(self, user_pack):
        pattern = self.pick_pattern(user_pack)
        self.add_pattern_to_used(pattern.text)
        server_log.add_log(pattern.text)
        pattern.insert_users(user_pack.list)
        return pattern.text

@users_autosave
def run_generation_job():
    user_pack = user_manager.choose_random_uid()
    patman = PatternsManager()
    phrase = patman.generate_phrase(user_pack)
    vkm.post_message(phrase)

    for user in user_pack:
        user_manager.add_to_used(user.uid)
    return phrase

vkm = VKManager()
user_manager = UserManager()

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