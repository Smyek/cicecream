#coding:utf-8
from generation import Phrase

generator = Phrase()
# generator.update_users()

for i in range(100):
    print i+1,
    phrase = generator.generate_phrase_cheap(username="Игорь Шепард", sex="m")
    print phrase