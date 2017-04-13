#!/usr/bin/python3.5

import os, shutil, ntpath, hashlib
import platform
import logging
import datetime, time
import sqlite3
import atexit
import yaml

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
        self.database = project_paths.users
        self.columns = ["id", "usedCount", "usedOnCycle", "isInGroup", "lastTimeUpdated"]
        self.columns_sql = ", ".join(self.columns)
        self.connection = sqlite3.connect(self.database)
        self.cursor = self.connection.cursor()

    # REMINDER
    def create_table(self):
        self.cursor.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, usedCount INTEGER, usedOnCycle BOOLEAN, isInGroup BOOLEAN, lastTimeUpdated INTEGER)')
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
            usedOnCycle = 1 if user in used_uids else 0
            self.forced_add_user(user, ever_used_uids_with_frequency[user], usedOnCycle)
        self.connection.commit()

    def forced_add_user(self, id, usedCount, usedOnCycle):
        self.cursor.execute('INSERT INTO users (%s) VALUES(%s, %s, %s, 1, %s)' % (self.columns_sql, id, usedCount, usedOnCycle, self.timestamp()))


    # checkers (doesn't need commit if run by self.update_users)
    def new_users_check(self, group_uids):
        new_users = []
        for id in group_uids:
            result = self.cursor.execute("SELECT * FROM users WHERE id = %s" % id).fetchall()
            if not result:
                self.cursor.execute('INSERT INTO users (%s) VALUES(%s, 0, 0, 1, %s)' % (self.columns_sql, id, self.timestamp()))
                new_users.append(id)
        if new_users:
            server_log.add_log('New users: %s' % ", ".join(list(map(str,new_users))), logging.info)

    def users_not_in_group_check(self, group_uids):
        for row in self.cursor.execute("SELECT id FROM users"):
            uid = row[0]
            if uid not in group_uids:
                self.cursor.execute("UPDATE users SET isInGroup = 0 WHERE id = %s" % uid)

    def all_usedOnCycle_check(self):
        result = self.cursor.execute("SELECT id FROM users WHERE usedOnCycle = 0 AND isInGroup = 1").fetchall()
        if not result:
            self.cursor.execute("UPDATE users SET usedOnCycle = 0")


    # used by UserManager
    def update_users(self, group_uids):
        self.new_users_check(group_uids)
        self.users_not_in_group_check(group_uids)
        self.all_usedOnCycle_check()
        self.connection.commit()

    def increment_user_used(self, id):
        result = self.cursor.execute("SELECT * FROM users WHERE id = %s" % id).fetchall()
        if result:
            updated_usedCount = result[0][1] + 1
            self.cursor.execute("UPDATE users SET usedCount = %s, lastTimeUpdated = %s, usedOnCycle = 1 WHERE id = %s" % (updated_usedCount, self.timestamp(), id))
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


    # extra tools
    def run_sql(self, sql_command):
        result = self.cursor.execute(sql_command)
        if result:
            result = result.fetchall()
            print(len(result), result)
        self.connection.commit()
        server_log.add_log("SQL query executed: %s" % sql_command)

    def clear_usedOnCycle_by_uid(self, id):
        result = self.cursor.execute("SELECT * FROM users WHERE id = %s" % id).fetchall()
        if result:
            self.cursor.execute("UPDATE users SET usedOnCycle = 0 WHERE id = %s" % id)
            self.connection.commit()
        else:
            server_log.add_log("User %s was not found in db" % id, logging.warning)

    def get_user_by_uid(self, id):
        result = self.cursor.execute("SELECT * FROM users WHERE id = %s" % id).fetchall()
        if result:
            return result
        else:
            server_log.add_log("User %s was not found in db" % id, logging.warning)

    def get_user_by_col_value(self, colname, value):
        result = self.cursor.execute("SELECT * FROM users WHERE %s = %s" % (colname, value)).fetchall()
        if result:
            return result
        else:
            print("Users with this parameters were not found")

    def set_all_usedCount_n(self, n=1):
        self.cursor.execute("UPDATE users SET usedCount = %s" % n)
        self.connection.commit()

    def set_all_as_usedOnCycle(self, all_uids=True):
        condition = " WHERE isInGroup = 1" if all_uids else ""
        self.cursor.execute("UPDATE users SET usedOnCycle = 1%s" % condition)
        self.connection.commit()

    # auxiliary
    def timestamp(self):
        return timemanager.time_now()

    def add_column(self, colname, coltype):
        self.cursor.execute("ALTER TABLE users ADD COLUMN %s %s" % (colname, coltype));
        self.connection.commit()

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
        result = ["\t".join(list(map(str, user))) for user in users]
        if to_file:
            with open(project_paths.root_file("db_printed.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(result))
        if on_screen:
            for row in result: print(row)

@SingletonDecorator
class ServerLogger:
    def __init__(self, log_path = "server_logs.txt"):
        self.startime = time.time()
        self.server_logs_path = project_paths.service_file(log_path)
        logging.basicConfig(format=u'%(levelname)-8s [%(asctime)s] %(message)s', level=logging.DEBUG,
                            handlers=[logging.FileHandler(self.server_logs_path, 'a', encoding='utf-8')])
        self.onstart()

    def onstart(self):
        date = datetime.datetime.now().strftime("%d.%m.%Y")
        self.add_log("New session: %s" % date)

        #cleaning
        self.clean_logs_procedures()

    def get_logs_list(self):
        with open(self.server_logs_path, "r", encoding="utf-8") as f:
            logs = f.read().strip().split("\n")
        return logs

    def clean_logs_procedures(self):
        logs_size = os.path.getsize(self.server_logs_path)
        if (logs_size / (1024*1024)) > 3:
            self.delete_logs()

    def delete_logs(self):
        with open(self.server_logs_path, "w", encoding="utf-8") as f:
            f.write("")
        server_log.add_log("Logs were cleaned")

    def add_log(self, message, level_function=logging.debug):
        if isinstance(message, tuple):
            message = "%s: %s" % message
        level_function(message)

    def add_key_value_log(self, key, value):
        self.add_log("%s: %s" % (key, value))

    def add_time_elapsed(self):
        time_elapsed = "%.2f" % (time.time() - self.startime)
        self.add_log("Time elapsed from start: %s sec" % time_elapsed)

@SingletonDecorator
class Paths:
    def __init__(self):
        self.wd = os.path.dirname(os.path.realpath(__file__))
        self.service = os.path.join(self.wd, "service")
        self.data = os.path.join(self.wd, "data")
        self.temp = os.path.join(self.wd, "temp")
        self.backups = os.path.join(self.service, "backups")

        self.check_paths_existence()

        # Constant file paths
        self.config = self.data_file("config.yaml")
        self.users = self.data_file('users.db')

    def check_paths_existence(self):
        for path_to in [self.service, self.temp, self.backups]:
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

    def backup_file(self, filename):
        return os.path.join(self.backups, filename)

@SingletonDecorator
class ServerConfig:
    def __init__(self):
        self.config = None
        self.meta = {}
        self.load()

    def is_test(self):
        return self.config.get_alias_value("config.test_mode")

    def load(self):
        self.config = YamlHandler(project_paths.config)
        self.meta["is_server"] = True if platform.system() == "Linux" else False

    def save(self):
        self.config.save_doc()

    def set_to_release(self):
        self.config.set_alias_value("config.test_mode", False)

    def set_to_test(self):
        self.config.set_alias_value("config.test_mode", True)

    def version(self):
        return self.config.get_alias_value("config.ver")

    def get_config(self):
        return self.config.doc, self.meta

@SingletonDecorator
class BackupManager:
    def __init__(self):
        pass

    def backupfilename(self, filename, mode=None):
        return '%s.backup' % filename

    def backupfilename_clear(self, filename, mode=None):
        return filename.replace(".backup", "")

    def make_file_backup(self, filepath, to_dir=None):
        if to_dir is None:
            to_dir = project_paths.temp_file
        filename = ntpath.basename(filepath)
        output_path = to_dir(self.backupfilename(filename))
        shutil.copy(filepath, output_path)
        server_log.add_log("Backup of %s saved to %s" % (filename, output_path))

    def load_backup(self, filepath, from_dir=None):
        if from_dir is None:
            from_dir = project_paths.temp_file
        backup_filename = self.backupfilename(ntpath.basename(filepath))
        backup_filepath = from_dir(backup_filename)
        if os.path.isfile(backup_filepath):
            if self.md5(backup_filepath) != self.md5(filepath):
                shutil.copy(backup_filepath, filepath)
                server_log.add_log("Backup (%s) has been loaded" % backup_filepath, logging.debug)
            else:
                print("Files are equal. Loading backup has been aborted")
        else:
            message = "No backup file (%s) found" % backup_filepath
            print(message)
            server_log.add_log(message, logging.error)

    def save_temporary_backup(self, filepath):
        self.make_file_backup(filepath, to_dir=project_paths.temp_file)

    def clear_temporary_backup(self, filepath):
        filename = ntpath.basename(filepath)
        backupfilepath = project_paths.temp_file(self.backupfilename(filename))
        os.remove(backupfilepath)

    def md5(self, fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

class YamlHandler:
    def __init__(self, document):
        self.pth = document
        self.doc = self.load_doc()

    def load_doc(self):
        with open(self.pth, "r", encoding="utf-8") as f:
            return yaml.load(f)

    def save_doc(self):
        with open(self.pth, "w", encoding="utf-8") as f:
            yaml.dump(self.doc, f, default_flow_style=False)

    def alias_split(self, alias):
        return alias.split(".")

    def get_alias_value(self, alias):
        alias = self.alias_split(alias)
        alias_value, last_subtree, key = self.walk_yaml(alias, self.doc)
        return alias_value

    def set_alias_value(self, alias, value):
        alias = self.alias_split(alias)
        alias_value, last_subtree, key = self.walk_yaml(alias, self.doc)
        last_subtree[key] = value

    def walk_yaml(self, alias, sub_tree=None):
        if sub_tree is None: sub_tree = self.doc
        if len(alias) > 1:
            alias_parts = alias[1:]
            return self.walk_yaml(alias_parts, sub_tree[alias[0]])
        else:
            return sub_tree[alias[0]], sub_tree, alias[0]



@SingletonDecorator
class TimeManager:
    def time_now(self):
        return int(time.time())

    def time_difference(self, t1, t2):
        return abs(int(t1-t2))

    def time_readable(self):
        # TODO
        pass


# Singletons init
project_paths = Paths()
server_log = ServerLogger()

backups = BackupManager()
timemanager = TimeManager()
server_config = ServerConfig()
database = DatabaseManager()

@atexit.register
def close_connection():
    database.connection.close()

if __name__ == "__main__":
    pass

