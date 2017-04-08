import logging
import atexit
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
                         }

        self.options = ["Exit"] + sorted(self.commands.keys())
        self.commands["Exit"] = self.exit

        self.main_loop()

    def main_loop(self):
        while True:
            self.print_options()
            user_input = input("Choose option: ")
            try:
                option_id = int(user_input)
            except:
                print("ERROR: must be integer.")
                continue
            if (option_id > len(self.options)) or (option_id < 0):
                print("ERROR: no such option.")
                continue
            output = self.commands[self.options[option_id]]()
            if output == "EXIT": break

    def print_options(self):
        for i in range(1, len(self.options)):
            print(i, self.options[i])
        print(0, self.options[0])

    # COMMANDS
    def generate_phrase_and_post(self):
        from generation import PhraseGenerator
        generator = PhraseGenerator()
        generator.vk._TEST_MODE = True
        phrase = generator.generate_phrase_cheap()
        generator.vk.post_message(phrase)
        server_log.add_log("phrase has been posted to the test group", logging.debug)

    def print_logs(self, logs_count=10):
        for log in server_log.get_logs_list()[-logs_count:]:
            print(log)

    def print_database(self):
        database.print_database(to_file=False, on_screen=True)

    def exit(self):
        print("Have a nice day.")
        return "EXIT"


if __name__ == "__main__":
    console = SICE_Console()
