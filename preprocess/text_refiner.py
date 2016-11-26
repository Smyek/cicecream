import re
import yaml
import pprint
from logger import Log

class TxtRefiner:
    def __init__(self):
        #debug
        self.log = Log("txtrefiner")

        self.text = ""

        #regex patterns lib
        self.patterns_path = "data/refiner_data/patterns.yaml"
        self.patterns = self.load_patterns()



    def set_default_patterns_params(self, pattern_dict, pt_group_name):
        if "Description" not in pattern_dict:
            pattern_dict["Description"] = ""
        if "r_value" not in pattern_dict:
            pattern_dict["r_value"] = " "

    def load_patterns(self):
        with open(self.patterns_path, "r", encoding="utf-8") as yaml_file:
            content = yaml_file.read()
        patterns_dict = yaml.load(content)
        for pt_group in patterns_dict:
            for pattern in patterns_dict[pt_group]:
                pt_dict = patterns_dict[pt_group][pattern]
                pt_dict["regex"] = re.compile(pt_dict["regex"])
                self.set_default_patterns_params(pt_dict, pt_group)
        self.log.write("regex patterns loaded")
        return patterns_dict

    def run_regexp_patterns(self, patterns_type):
        for pattern in self.patterns[patterns_type]:
            pattern_dict = self.patterns[patterns_type][pattern]
            self.text = pattern_dict["regex"].sub(pattern_dict["r_value"], self.text)

    def run_all_regexp_patterns(self):
        pt_types = ["Remover", "Replacer", "Custom"]
        for pt_type in pt_types:
            self.run_regexp_patterns(pt_type)

    def refine_text(self, text):
        self.text = text
        self.run_all_regexp_patterns()
        return self.text

if __name__ == "__main__":
    txtref = TxtRefiner()