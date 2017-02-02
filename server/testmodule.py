#coding:utf-8
import random, datetime, codecs

TEST_UID = "4894606"

def generate_phrases(amount=100):
    global generator
    for i in range(amount):
        print i+1,
        phrase = generator.generate_phrase_cheap(username="Игорь Шепард", sex="m")
        print phrase

class ServerErrorLogger:
    def __init__(self):
        self.server_logs_path = "service/server_logs.txt"
        self.logs_queue = self.load_logs()
        self.new_logs = []
        if len(self.logs_queue) > 500: self.logs_queue = [] #cleaning

        date = datetime.datetime.now().strftime("%d.%m.%Y")
        self.logs_queue.append("\t>Started %s" % date)

    def load_logs(self):
        with codecs.open(self.server_logs_path, "r", "utf-8") as f:
            return f.read().split("\n")


    def save_logs(self):
        if not self.new_logs:
            self.logs_queue.append("No errors.")

        self.logs_queue += self.new_logs
        with codecs.open(self.server_logs_path, "w", "utf-8") as f:
            f.write("\n".join(self.logs_queue))


    def add_log(self, error_message):
        time = datetime.datetime.now().strftime("%H.%M.%S")
        self.new_logs.append("\t".join([time, error_message]))



if __name__ == "__main__":
    from generation import PhraseGenerator
    # generator.update_users()
    generator = PhraseGenerator()
    generator.vk._TEST_MODE = True
    print generator.user_manager.ever_used_uids
    print generator.user_manager.ever_used_uids_with_frequency
    print generator.user_manager.group_uids
    print ""
    print set(generator.user_manager.group_uids) - set(generator.user_manager.ever_used_uids)
    print "update test"
    generator.user_manager.add_and_update_uids(TEST_UID)

