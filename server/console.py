#!/usr/bin/python3.5

import logging
import atexit
import re
from utils import server_log
from utils import server_config
from utils import database
from utils import backups
from utils import project_paths

@atexit.register
def close_connection():
    #server_log.add_log("Console session: closed", logging.info)
    pass

class SICE_Console:
    def __init__(self):
        #server_log.add_log("Console session: started", logging.info)

        self.commands = [("Exit", self.exit),
                         ("Generate phrase and post to %s" % self.post_mode().upper(), self.generate_phrase_and_post),
                         ("> Database options", self.database_list),
                         ("> Logs options", self.logs_list),
                         ("> Backup options", self.backups_list),
                         ("> Config options", self.config_list),
                         ]

        self.list_template = [("Back", self.back)]
        self.options_lists = [self.commands]
        self.arguments_buffer = []
        self.main_loop()

    def main_loop(self):
        while True:
            self.print_options()
            user_input = input("Choose option: ")
            option_id = self.parse_input(user_input)
            if option_id is None: continue
            output = self.options_lists[-1][option_id][1]()
            if output == "EXIT": break

    def parse_input(self, user_input):
        refined = re.sub("\s\s+", " ", user_input.strip())
        option = re.search("^(\d+)", refined)
        arguments = re.findall('(?:-)([^ ]+)', refined)
        if not option:
            print("ERROR: must be integer.")
            return None
        else:
            option_id = int(option.group(1))
            if (option_id > len(self.options_lists[-1])) or (option_id < 0):
                print("ERROR: no such option.")
                return None
        self.arguments_buffer = arguments
        return option_id

    def print_options(self):
        commands = self.options_lists[-1]
        for i in range(1, len(commands)):
            print(i, commands[i][0])
        print(0, commands[0][0])


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

    def are_you_sure(self):
        decision = input("Are you sure? (y/n)").strip().lower()
        if decision == "y":
            return True
        return False

    def post_mode(self):
        if server_config.is_test():
            return "Test"
        else:
            return "Release"


    # LISTS
    def database_list(self):
        options = self.list_template + [("Print database", self.print_database),
                                        ("Run SQL query", self.run_sql_query),
                                        ("Convert old system to database", database.convert_old_system_to_database),
                                        ("Set -uid attribute usedOnCycle to 0", self.set_usedOnCycle_by_uid),
                                        ("Get user info by -uid", self.print_user_info_by_uid),
                                        ("Get user by -colname -value", self.print_uids_by_col_value),
                                        ("Set all usedCount -n", self.set_all_usedCount_n),
                                        ("Set all as usedOnCycle", self.set_all_as_usedOnCycle),
                                        ]
        self.options_lists.append(options)

    def logs_list(self):
        options = self.list_template + [("Print -n last logs (10 by default)", self.print_logs),
                                        ("Delete logs", self.delete_logs),
                                        ]
        self.options_lists.append(options)

    def backups_list(self):
        options = self.list_template + [("Save users backup manually", self.save_users_backup_to_manual),
                                        ("Load users backup (-t for temporary)", self.load_users_backup),
                                        ]
        self.options_lists.append(options)

    def config_list(self):
        options = self.list_template + [("Print config", self.print_config),
                                        ("Switch to test", self.switch_to_test),
                                        ("Switch to release", self.switch_to_release),
                                        ("Save config", self.save_config),
                                        ]
        self.options_lists.append(options)

    # COMMANDS
    ## DATABASE options
    def run_sql_query(self):
        squery = input("Query: ")
        backups.make_file_backup(project_paths.users, project_paths.temp_file)
        database.run_sql(squery)

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

    def set_all_usedCount_n(self):
        count = 1
        if self.arguments_buffer:
            count = self.try_get_integer_argument()
        backups.make_file_backup(project_paths.users, project_paths.temp_file)
        database.set_all_usedCount_n(count)

    def set_all_as_usedOnCycle(self):
        condition = False
        if self.arguments_buffer:
            if self.arguments_buffer[0] == "-a":
                condition = True
        backups.make_file_backup(project_paths.users, project_paths.temp_file)
        database.set_all_as_usedOnCycle(condition)

    def print_database(self):
        database.print_database(to_file=False, on_screen=True)


    ## LOGS options
    def print_logs(self, logs_count=10):
        if self.arguments_buffer:
            if self.arguments_buffer[0] == "a":
                logs_count = 0
            else:
                try: logs_count = int(self.arguments_buffer[0])
                except: print('Must be integer or "-a". Default count used.')
        for log in server_log.get_logs_list()[-logs_count:]:
            try:
                print(log)
            except UnicodeEncodeError:
                print(log.encode('cp1251', errors="replace"))

    def delete_logs(self):
        if not self.are_you_sure(): return
        server_log.delete_logs()


    ## BACKUPS OPTIONS
    def save_users_backup_to_manual(self):
        if not self.are_you_sure(): return
        backups.make_file_backup(project_paths.users, project_paths.backup_file)

    def load_users_backup(self):
        if self.arguments_buffer:
            if self.arguments_buffer[0] == "t":
                backups.load_backup(project_paths.users, project_paths.temp_file)
        else:
            backups.load_backup(project_paths.users, project_paths.backup_file)


    ## CONFIG options
    def print_config(self):
        print(server_config.get_config())

    def switch_to_test(self):
        server_config.set_to_test()
        server_config.save()

    def switch_to_release(self):
        if not self.are_you_sure(): return
        server_config.set_to_release()

    def save_config(self):
        print(server_config.get_config())
        if not self.are_you_sure(): return
        server_config.save()


    ## other
    def generate_phrase_and_post(self):
        from generation import PhraseGenerator
        generator = PhraseGenerator()
        generator.vk._TEST_MODE = True
        phrase = generator.generate_phrase_cheap()
        generator.vk.post_message(phrase)
        server_log.add_log("phrase has been posted to the test group", logging.debug)

    def back(self):
        self.options_lists = self.options_lists[:-1]

    def exit(self):
        print("Have a nice day.")
        return "EXIT"


if __name__ == "__main__":
    console = SICE_Console()