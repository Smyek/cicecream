#coding:utf-8

TEST_UID = "4894606"

def generate_phrases(amount=100):
    global generator
    for i in range(amount):
        print(i+1)
        phrase = generator.generate_phrase_cheap(username="Игорь Шепард", sex="m")
        print(phrase)

def check_posting_service():
    generator = PhraseGenerator()
    generator.vk._TEST_MODE = True
    generator.user_manager.group_uids = [1, 2, 3]
    generator.user_manager.never_used = []
    generator.user_manager.not_used_on_cycle = [3]
    generator.user_manager.result_selection = generator.user_manager.choose_selection()
    phrase = generator.generate_phrase_cheap()
    print(phrase)
    generator.user_manager.update_uids_files()
    generator.vk.post_message(phrase)


def simple_test():
    global generator
    phrase = generator.generate_phrase_cheap()
    generator.user_manager.update_uids_files()
    generator.vk.post_message(phrase)



if __name__ == "__main__":
    from generation import PhraseGenerator
    import utils
    generator = PhraseGenerator()
    generator.vk._TEST_MODE = True
    simple_test()


