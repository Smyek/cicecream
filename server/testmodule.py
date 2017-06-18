#coding:utf-8
import time

from generation import PatternsManager
from generation import VKUser
from generation import vkm

from utils import project_paths

patman = PatternsManager()

TEST_UID = 4909962
TEST_USER = VKUser(TEST_UID)

def simple_test(count=1, preset_user=None, post=False):
    results = []
    for i in range(count):
        if preset_user:
            preset_user = [TEST_USER]
        else:
            time.sleep(0.5)
        phrase = patman.generate_phrase_cheap(preset_user)
        if post:
            vkm.post_message(phrase)
            time.sleep(0.5)
        results.append(phrase)
        print(phrase)
    save_generation_out(results)

def save_generation_out(result):
    result = "\n".join(result)
    with open(project_paths.test_generation, "w", encoding="utf-8") as f:
        f.write(result)

if __name__ == "__main__":
    vkm._TEST_MODE = True
    simple_test(100, TEST_UID)


