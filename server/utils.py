import os
import logging
import datetime, time
import sqlite3
import atexit

class SingletonDecorator:
    def __init__(self, p_class):
        self._class = p_class
        self.instance = None

    def __call__(self,*args,**kwds):
        if self.instance == None:
            self.instance = self._class(*args,**kwds)
        return self.instance

@SingletonDecorator
class DatabaseManager:
    def __init__(self):
        self.database = project_paths.data_file('users.db')
        self.columns = "id, usedCount, usedOnCycle, lastTimeUpdated"
        self.connection = sqlite3.connect(self.database)
        self.cursor = self.connection.cursor()

    # REMINDER
    def create_table(self):
        self.cursor.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, usedCount INTEGER, usedOnCycle BOOLEAN, lastTimeUpdated INTEGER)')
        self.connection.commit()

    # TEMPORARY TEMPORARY TEMPORARY TEMPORARY TEMPORARY TEMPORARY TEMPORARY
    def convert_old_system_to_database(self):
        self.connection.close()
        from collections import defaultdict
        if os.path.isfile(self.database):
            des = input("db already exists. Delete? (y/n)")
            if des.lower().strip() == "y":
                os.remove(self.database)
            else: return
        self.connection = sqlite3.connect(self.database)
        self.cursor = self.connection.cursor()
        self.create_table()

        with open(project_paths.temp_file("uidsUsed.txt"), "r", encoding="utf-8") as f:
            content = f.read().split("\n")
            if content == ['']: return []
            used_uids = list(map(int, content))

        with open(project_paths.temp_file("uids_ever_used.csv"), "r", encoding="utf-8") as f:
            dictionary = defaultdict(int, [list(map(int, row.split("\t"))) for row in f.read().replace("\r\n", "\n").split("\n")])
            ever_used_uids_with_frequency = dictionary

        for user in ever_used_uids_with_frequency:
            print(user)
            usedOnCycle = 1 if user in used_uids else 0
            self.forced_add_user(user, ever_used_uids_with_frequency[user], usedOnCycle)
        self.connection.commit()

    def forced_add_user(self, id, usedCount, usedOnCycle):
        self.cursor.execute('INSERT INTO users (%s) VALUES(%s, %s, %s, %s)' % (self.columns, id, usedCount, usedOnCycle, self.timestamp()))


    # checkers
    def new_users_check(self, group_uids):
        new_users = []
        for id in group_uids:
            result = self.cursor.execute("SELECT * FROM users WHERE id = %s" % id).fetchall()
            if not result:
                self.cursor.execute('INSERT INTO users (%s) VALUES(%s, 0, 0, %s)' % (self.columns, id, self.timestamp()))
                new_users.append(id)
        if new_users:
            server_log.add_log('New users: %s' % ", ".join(list(map(str,new_users))), logging.info)

    def all_usedOnCycle_check(self):
        result = self.cursor.execute("SELECT id FROM users WHERE usedOnCycle = 0").fetchall()
        if not result:
            self.cursor.execute("UPDATE users SET usedOnCycle = 0")
            self.connection.commit()


    # used by UserManager
    def update_users(self, group_uids):
        self.new_users_check(group_uids)
        self.all_usedOnCycle_check()
        self.connection.commit()

    def increment_user_used(self, id):
        result = self.cursor.execute("SELECT * FROM users WHERE id = %s" % id).fetchall()
        if result:
            updated_usedCount = result[0][1] + 1
            self.cursor.execute("UPDATE users SET usedCount = %s, usedOnCycle = 1 WHERE id = %s" % (updated_usedCount, id))
            self.connection.commit()
            server_log.add_log("User %s incremented" % id)
        else:
            server_log.add_log("User %s not found in db while trying to increment" % id, logging.warning)

    def get_never_used_uids(self):
        return self.get_selection_uids("SELECT id FROM users WHERE usedCount = 0",
                                       "All uids were used before")

    def get_not_used_oncycle_uids(self):
        return self.get_selection_uids("SELECT id FROM users WHERE usedOnCycle = 0",
                                       "All uids were used on current cycle")

    # auxiliary
    def timestamp(self):
        # TODO
        return '1491570661'

    def get_selection_uids(self, sql, message_not_found):
        result = self.cursor.execute(sql).fetchall()
        if result:
            return [x[0] for x in result]
        else:
            server_log.add_log(message_not_found)
            return []

    def print_database(self, to_file=True, on_screen=False):
        self.cursor.execute('SELECT * FROM users')
        users = self.cursor.fetchall()
        with open(project_paths.root_file("db_printed.txt"), "w", encoding="utf-8") as f:
            result = ["\t".join(list(map(str, user))) for user in users]
            if to_file:
                f.write("\n".join(result))
            if on_screen:
                for row in result: print(row)

@SingletonDecorator
class ServerLogger:
    def __init__(self, log_path = "server_logs.txt"):
        self.startime = time.time()
        self.server_logs_path = project_paths.service_file(log_path)
        logging.basicConfig(format=u'%(levelname)-8s [%(asctime)s] %(message)s', level=logging.DEBUG,
                            filename=self.server_logs_path)
        self.onstart()

    def onstart(self):
        date = datetime.datetime.now().strftime("%d.%m.%Y")
        self.add_log("New session: %s" % date)

        #cleaning
        self.clean_logs()


    def clean_logs(self):
        logs_size = os.path.getsize(self.server_logs_path)
        if (logs_size / (1024*1024)) > 3:
            with open(self.server_logs_path, "w", encoding="utf-8") as f:
                f.write("")

    def add_log(self, message, level_function=logging.debug):
        if isinstance(message, tuple):
            message = "%s: %s" % message
        level_function(message)

    def add_key_value_log(self, key, value):
        self.add_log("%s: %s" % (key, value))

    def add_time_elapsed(self):
        time_elapsed = "%.2f" % (time.time() - self.startime)
        self.add_log("\t"*4 + "Time elapsed from start: %s sec" % time_elapsed)

@SingletonDecorator
class Paths:
    def __init__(self):
        self.wd = os.path.dirname(os.path.realpath(__file__))
        self.service = os.path.join(self.wd, "service")
        self.data = os.path.join(self.wd, "data")
        self.temp = os.path.join(self.wd, "temp")

        self.check_paths_existence()

    def check_paths_existence(self):
        for path_to in [self.service, self.temp]:
            if not os.path.exists(path_to):
                os.makedirs(path_to)

    def root_file(self, filename):
        return os.path.join(self.wd, filename)

    def service_file(self, filename):
        return os.path.join(self.service, filename)

    def data_file(self, filename):
        return os.path.join(self.data, filename)

    def temp_file(self, filename):
        return os.path.join(self.temp, filename)

# Singletons init
project_paths = Paths()
server_log = ServerLogger()
database = DatabaseManager()

@atexit.register
def close_connection():
    database.connection.close()

if __name__ == "__main__":
    database.print_database()

