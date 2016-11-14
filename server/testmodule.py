#coding:utf-8
from generation import PhraseGenerator

generator = PhraseGenerator()
generator.vk._TEST_MODE = True
# generator.update_users()
def generate_phrases(amount=100):
    global generator
    for i in range(amount):
        print i+1,
        phrase = generator.generate_phrase_cheap(username="Игорь Шепард", sex="m")
        print phrase

if __name__ == "__main__":
    pass