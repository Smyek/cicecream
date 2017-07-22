#coding:utf-8
import time

from generation import PatternsManager
from generation import VKUser, UserPack
from generation import vkm

from utils import project_paths

patman = PatternsManager()

TEST_USER = VKUser(4909962)
TEST_USER_M2 = VKUser(9693167)
TEST_USER_F = VKUser(11036360)
TEST_PACK = UserPack([TEST_USER])
TEST_PACK_F = UserPack([TEST_USER_F])
TEST_PACK_M1F1 = UserPack([TEST_USER, TEST_USER_F])
TEST_PACK_M2F1 = UserPack([TEST_USER, TEST_USER_M2, TEST_USER_F])

def simple_test(count=1, preset_user=None, post=False):
    results = []
    if not preset_user:
        preset_user = TEST_PACK

    for i in range(count):
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
    simple_test(100, TEST_PACK)


