import datetime

class Log:
    def __init__(self, name):
        self.logger_name = name
        self.logger_path = "logs/%s_%s.log" % (self.logger_name, self.timestamp("day"))
        self.logfile = self.open_filestream()
        self.new_launch()

    def timestamp(self, style="full"):
        styles = {"full": "%H.%M.%S-%d.%m.%Y",
                  "day": "%d.%m.%Y",
                  "time": "%H:%M:%S"}
        return datetime.datetime.now().strftime(styles[style])

    def open_filestream(self):
        fstream = open(self.logger_path, "a", encoding="utf-8")
        return fstream

    def close_filestream(self):
        self.logfile.close()

    def write(self, content):
        self.logfile.write("\n%s: " % self.timestamp("time") + content)

    def new_launch(self):
        content = "%s\n%sNEW LAUNCH%s\n%s" % ("="*20, "="*5, "="*5, "="*20)
        self.logfile.write("\n" + content)