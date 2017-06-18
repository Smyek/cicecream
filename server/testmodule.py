#coding:utf-8
import time

from generation import PatternsManager
from generation import vkm

patman = PatternsManager()

TEST_UID = "4894606"

def simple_test(count=1):
    for i in range(count):
        phrase = patman.generate_phrase_cheap()
        print(phrase)
        vkm.post_message(phrase)
        time.sleep(0.5)

if __name__ == "__main__":
    vkm._TEST_MODE = True
    simple_test(50)


