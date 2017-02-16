import datetime, codecs, time

class SingletonDecorator:
    def __init__(self,klass):
        self.klass = klass
        self.instance = None
    def __call__(self,*args,**kwds):
        if self.instance == None:
            self.instance = self.klass(*args,**kwds)
        return self.instance

@SingletonDecorator
class ServerLogger:
    def __init__(self):
        self.startime = time.time()

        self.server_logs_path = "service/server_logs.txt"
        self.logs_queue = self.load_logs()
        self.new_logs = []
        self.last_time = ""
        if len(self.logs_queue) > 500:
            self.logs_queue = [] #cleaning

        date = datetime.datetime.now().strftime("%d.%m.%Y")
        self.logs_queue.append("New session: %s" % date)


    def load_logs(self):
        with codecs.open(self.server_logs_path, "r", "utf-8") as f:
            return f.read().split("\n")


    def save_logs(self):
        if not self.new_logs:
            self.logs_queue.append("No logs.")

        self.logs_queue += self.new_logs
        self.post_logs()
        with codecs.open(self.server_logs_path, "w", "utf-8") as f:
            f.write("\n".join(self.logs_queue))


    def add_log(self, message):
        time = datetime.datetime.now().strftime("%H:%M:%S")

        if time == self.last_time:
            time = "\t"*4
        else:
            self.last_time = time
        self.new_logs.append("\t".join([time, message]))

    def add_key_value_log(self, key, value):
        self.add_log("%s: %s" % (key, value))

    def post_logs(self):
        time_lasted = "%.2f" % (time.time() - self.startime)
        self.logs_queue.append("\t"*4 + "Time elapsed: %s sec" % time_lasted)

        self.logs_queue.append("")



#singletones init
server_log = ServerLogger()