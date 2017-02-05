#coding:utf-8
from generation import VKManager
from collections import defaultdict
import re, codecs, csv, time

class GroupManager:
    def __init__(self):
        self.VKM = VKManager()
        self.vk = self.VKM.vk

    def get_messages_count(self):
        #wip
        messages_count = self.vk.get(method="wall.get", owner_id="-92940311", count=1)
        return messages_count

    def walk_messages(self, messages_count=None):
        if not messages_count:
            messages_count = 3200
        for offset in range(0, messages_count, 100):
            time.sleep(0.3) #vk doesn't like spam
            messages = self.vk.get(method="wall.get", owner_id="-92940311", offset=offset, count=1000)
            for message in messages:
                if isinstance(message, dict):
                    yield message

    ##custom##

    #gather data to local storage
    def collect_messages_to_local(self):
        pass

    #online ever used
    def save_ever_used_ids(self):
        ids = defaultdict(int)
        reg_id = re.compile("\[id([0-9]+?)\|(.+?)\]")
        for message in self.walk_messages():
            id_search = reg_id.search(message['text'])
            if id_search:
                uid = id_search.group(1)
                ids[uid] += 1
            else:
                print "No id!", message['text'], message

        ids = sorted(ids.items(), key=lambda x: (x[1], x[0]), reverse=True)
        count = 0
        with codecs.open("data/userdata/uids_ever_used.csv", "w", "utf-8") as csvfile:
            writer = csv.writer(csvfile, delimiter='\t', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for entry in ids:
                print entry
                count += entry[1]
                writer.writerow(entry)
        print "messages count: ", count

if __name__ == "__main__":
    gm = GroupManager()
    gm.save_ever_used_ids()