#!/usr/bin/python3.5

import logging
import atexit
import re
from utils import server_log
from utils import database

@atexit.register
def close_connection():
    server_log.add_log("Console session: closed", logging.info)

class SICE_Console:
    def __init__(self):
        server_log.add_log("Console session: started", logging.info)

        self.commands = {"Print database": self.print_database,
                         "Convert old system to database": database.convert_old_system_to_database,
                         "Generate phrase and post to Test": self.generate_phrase_and_post,
                         "Print 10 last logs": self.print_logs,
                         "Set -uid attribute usedOnCycle to 0": self.set_usedOnCycle_by_uid,
                         "Get user info by -uid": self.print_user_info_by_uid,
                         "Get user by -colname -value": self.print_uids_by_col_value,
                         }

        self.options = ["Exit"] + sorted(self.commands.keys())
        self.commands["Exit"] = self.exit
        self.arguments_buffer = []
        self.main_loop()

    def main_loop(self):
        while True:
            self.print_options()
            user_input = input("Choose option: ")
            option_id = self.parse_input(user_input)
            if option_id is None: continue
            output = self.commands[self.options[option_id]]()
            if output == "EXIT": break

    def parse_input(self, user_input):
        refined = re.sub("\s\s+", " ", user_input.strip())
        option = re.search("^(\d+)", refined)
        arguments = re.findall("(?:-)([^ ]+)", refined)
        if not option:
            print("ERROR: must be integer.")
        else:
            option_id = int(option.group(1))
            if (option_id > len(self.options)) or (option_id < 0):
                print("ERROR: no such option.")
                return None
        self.arguments_buffer = arguments
        return option_id

    def print_options(self):
        for i in range(1, len(self.options)):
            print(i, self.options[i])
        print(0, self.options[0])


    # AUXILIARY
    def is_buffer_empty(self):
        if not self.arguments_buffer:
            print("ERROR: Arguments must be specified.")
            return True
        return False

    def try_get_integer_argument(self, i=0):
        try:
            value = int(self.arguments_buffer[i])
            return value
        except:
            print('Argument must be integer.')
            return None


    # COMMANDS
    def generate_phrase_and_post(self):
        from generation import PhraseGenerator
        generator = PhraseGenerator()
        generator.vk._TEST_MODE = True
        phrase = generator.generate_phrase_cheap()
        generator.vk.post_message(phrase)
        server_log.add_log("phrase has been posted to the test group", logging.debug)

    def set_usedOnCycle_by_uid(self):
        if not self.arguments_buffer:
            print("Uid not specified. e.g. -123")
            return
        else:
            uid = self.try_get_integer_argument()
            if uid is None: return
        database.clear_usedOnCycle_by_uid(uid)

    def print_user_info_by_uid(self):
        if not self.arguments_buffer:
            print("Uid not specified. e.g. -123")
            return
        else:
            uid = self.try_get_integer_argument()
            if uid is None: return
        user_info = list(map(str, database.get_user_by_uid(uid)[0]))
        for i in range(len(database.columns)):
            print("%s: %s" % (database.columns[i], user_info[i]))

    def print_uids_by_col_value(self):
        if self.is_buffer_empty(): return
        colname = self.arguments_buffer[0]
        value = self.arguments_buffer[1]
        print(colname, value)
        for row in database.get_user_by_col_value(colname, value):
            print(row)

    def print_logs(self, logs_count=10):
        if self.arguments_buffer:
            if self.arguments_buffer[0] == "all":
                logs_count = 0
            else:
                try: logs_count = int(self.arguments_buffer[0])
                except: print('Must be integer or "all". Default count used.')
        for log in server_log.get_logs_list()[-logs_count:]:
            try:
                print(log)
            except UnicodeEncodeError:
                print(log.encode('cp1251'))

    def print_database(self):
        database.print_database(to_file=False, on_screen=True)

    def exit(self):
        print("Have a nice day.")
        return "EXIT"


if __name__ == "__main__":
    console = SICE_Console()
