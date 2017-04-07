import datetime, logging, time

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
        logging.basicConfig(format=u'%(levelname)-8s [%(asctime)s] %(message)s', level=logging.DEBUG,
                            filename=self.server_logs_path)
        self.onstart()

    def onstart(self):
        date = datetime.datetime.now().strftime("%d.%m.%Y")
        self.add_log("New session: %s" % date)

        #cleaning
        self.current_logs = self.load_logs()
        if len(self.current_logs) > 500:
            # TODO
            self.current_logs = []

    def load_logs(self):
        with open(self.server_logs_path, "r", encoding="utf-8") as f:
            return f.read().split("\n")

    def add_log(self, message):
        if isinstance(message, tuple):
            message = "%s: %s" % message
        logging.debug(message)

    def add_key_value_log(self, key, value):
        self.add_log("%s: %s" % (key, value))

    def add_time_elapsed(self):
        time_elapsed = "%.2f" % (time.time() - self.startime)
        self.add_log("\t"*4 + "Time elapsed from start: %s sec" % time_elapsed)

#singletones init
server_log = ServerLogger()