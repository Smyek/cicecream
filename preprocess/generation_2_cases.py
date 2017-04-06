#coding:utf-8
import subprocess, codecs, json, operator, random, shutil, string, re

class WordInfo:
    def __init__(self, word):
        self.word = word
        self.books = []


class Phrase:
    def __init__(self):
        self.mystem = [[]]
        self.gram = {}
        self.words_info = {} #сюда добавляется вся информация про то сколько раз и где нграммы встретились
        self.sentence_patterns = {}
        self.sentence_length_dict = {}
        self.nicknames = []
        self.exceptions = []

        self.current_file = u""
        self.patterns_amount = 0
        self.words_amount = 0

        self.reGram = re.compile(u"(,|=)")
        self.rePunctuationFix = re.compile(u" ([.,?!])")
        self.rePunctuationFix_2 = re.compile(u"([.?!])( -\.|\.|\"\.?)")
        self.reSpeechFix = re.compile(u" :\" ")

        self.rePersnFix = re.compile(u",(persn|famn)")


    def load_exceptions(self, ex_file=u"exceptions.txt"):
        with codecs.open(ex_file, "r", "utf-8") as f:
            for line in f:
                self.exceptions.append(line.strip())


    @staticmethod
    def initiate_mystem(inputFile=u"input.txt"):
        command = u"mystem -dig -c -s -d --eng-gr --format json < %s > mystem.json" % (inputFile)
        command = command.split()
        proc = subprocess.call(command, shell=True)
        print(proc)

    #составляем информацию о слове в массиве gram_words
    def gram_info_update(self, word):
        if word not in self.words_info:
            wordClass = WordInfo(word)
            wordClass.books.append(self.current_file)
            self.words_info[word] = wordClass
        else:
            if self.current_file not in self.words_info[word].books:
                self.words_info[word].books.append(self.current_file)

    def gram_process(self, text, gram):
        if gram not in self.gram:
            self.gram[gram] = [text, ]
        else:
            if text not in self.gram[gram]:
                self.gram[gram].append(text)

    #возвращает true, если записываем гр. разбор а не слово
    def gram_check(self, gram):
        if self.reGram.split(gram[:6])[0] in [u"S", u"A", u"V", u"ANUM", u"NUM", u"SPRO"]:
            return True
        return False

    #удаляет последний паттерн в process_mystem_entry, если не соответствует необходимым параметрам
    def accept_sentence(self):

        sentence = self.mystem[-1]
        for gr in sentence:
            grams = self.reGram.split(gr)
            if grams[0] in [u"S", u"SPRO"]:
                if (u'nom' in grams) and (u'sg' in grams)and (u'anim' in grams):
                    return
        self.mystem.pop()

    def username_in_last_array(self):
        for i in self.mystem[-1]:
            if u"username" in i:
                return True

    #ставит тег <username> вместо подходящего существительного
    def username_include(self):
        if self.mystem == []: return
        if self.username_in_last_array(): return
        for i in range(len(self.mystem[-1])):
            gram = self.mystem[-1][i]
            grams = self.reGram.split(gram)
            if grams[0] in [u"S", u"SPRO"]:
                if (u'nom' in grams) and (u'sg' in grams):
                    if u"persn" in grams:
                        self.mystem[-1][i] = u"<username>[%s]" % (u",".join(grams))
                        return
                    elif u"famn" in grams:
                        self.mystem[-1][i] = u"<username>[%s]" % (u",".join(grams))
                        return
                    elif grams[0] == u"SPRO":
                        self.mystem[-1][i] = u"<username>[%s]" % (u",".join(grams))
                        return
                    else:
                        self.mystem[-1][i] = u"<username>[%s]" % (u",".join(grams))
                        return

    def modify_sentence(self):
        if self.mystem == []: return
        for i in range(len(self.mystem[-1])-1):
            try: self.mystem[-1][i+1]
            except: break
            currentW, nextW = self.mystem[-1][i], self.mystem[-1][i+1]
            if (u"<username>" in currentW) and ((u"famn" in nextW) or (u"patrn" in nextW)):
                del self.mystem[-1][i+1]
            if ((u"famn" in currentW) or (u"patrn" in currentW)) and (u"<username>" in nextW):
                del self.mystem[-1][i]
            if (u"famn" in currentW) or (u"persn" in currentW):
                self.mystem[-1][i] = self.rePersnFix.sub(u"", self.mystem[-1][i])

    #возвращает true, если слово - исключение
    def word_exceptions(self, lex, gram):
        if lex in self.exceptions:
            # print lex, gram
            return True
        if (u"abbr" in gram) or (u"obsc" in gram) or (u"inform" in gram) or (u"rare" in gram):
            #print lex, gram
            return True
        if u"#" in lex: return True
        return False

    def process_mystem_entry(self, entry):
        if "analysis" in entry:
            if entry["analysis"] == []: return
            gram = entry["analysis"][0]['gr']
            if self.word_exceptions(entry["analysis"][0]['lex'], gram): return
            if self.gram_check(gram):
                self.gram_process(entry["text"].lower(), gram)
                self.mystem[-1].append(gram) #добавляем в последний список разбор
            else:
                self.gram_process(entry["text"].strip(), entry["text"].strip())
                self.mystem[-1].append(entry['text'].strip())
        else:
            if entry['text'] in [u"\s", "\n"]:
                self.accept_sentence()
                self.username_include()
                self.modify_sentence()
                self.mystem.append([])
            elif (entry['text'] == u" "): return
            else:
                self.gram_process(entry["text"].strip(), entry["text"].strip())
                self.mystem[-1].append(entry['text'].strip())

    def load_mystem_array(self):
        with codecs.open("mystem.json", "r", "utf-8") as f:
            for line in f:
                a = json.loads(line.strip())
                for key in a:
                    ans = self.process_mystem_entry(key)

    def patterns_length(self, length):
        if length in self.sentence_length_dict:
            self.sentence_length_dict[length] += 1
        else:
            self.sentence_length_dict[length] = 1

    def sentence_stats(self, characterAmount, wordsAmount):
        if characterAmount > 140: print(u"Количество слов:", wordsAmount, u"Символов:", characterAmount)

    def sentence_ambiguity(self, sentence):
        if u"S=(" in sentence: return True
        if u"A=(" in sentence: return True

    #проверка предложения, возвращает True, если не подходит
    def sentence_check(self, sent, length):
        if sent == []: return True
        if length < 10: return True
        if length > 25: return True
        if self.sentence_ambiguity(u"_+_".join(sent)): return True



    #берет список списков предложений (self.mystem) и делает n шаблонов предложений, записывает в self.sentence_patterns
    def refine_sentence_patterns(self):
        for sent in self.mystem:
            # print sent, "sentence"
            if self.sentence_check(sent, len(sent)): continue
            self.patterns_length(len(sent))
            sent = u"_+_".join(sent)
            if sent in self.sentence_patterns:
                self.sentence_patterns[sent] += 1
            else:
                self.sentence_patterns[sent] = 1


        #sorted_sp = sorted(self.sentence_patterns.items(), key=operator.itemgetter(1), reverse=True)
        #sorted_length = sorted(self.sentence_length_dict.items(), key=operator.itemgetter(1), reverse=True)
        # for sent in sorted_sp[:30]:
        #     print sent[0], sent[1]
        # for sent in sorted_length[:30]:
        #     print sent[0], sent[1]


    def phrase_refine(self, phrase):
        first_pass = u" ".join(phrase) + "."
        first_pass = first_pass.strip(u" -")
        phrase = first_pass[0].upper() + first_pass[1:]
        phrase = self.rePunctuationFix.sub(u"\\1", phrase)
        phrase = phrase.replace(u"  ", u" ")
        phrase = phrase.replace(u" - -.", u"")
        phrase = phrase.replace(u" :\" ", u": \"")
        phrase = phrase.replace(u"--", u"—")
        phrase = self.rePunctuationFix_2.sub(u"\\1", phrase)
        # phrase = self.reSpeechFix.sub(u":", phrase)
        # phrase = phrase.replace(u". -.", u".")
        # phrase = phrase.replace(u"?.", u"?")
        # phrase = phrase.replace(u"!.", u"!")
        return phrase




    def random_pattern(self):
        with codecs.open("info.txt", "r", "utf-8") as f:
            index = random.randint(0, int(f.read()))
        with codecs.open("patterns.txt", "r", "utf-8") as f:
            count = 0
            for pattern in f:
                if index == count: return pattern
                count += 1

    def load_nicknames(self):
        with codecs.open("nicknames.txt", "r", "utf-8") as f:
            for line in f:
                nick = line
                if nick != u"": self.nicknames.append(nick)


    def generate_phrase_cheap(self, username=None):
        #print "generating..."
        self.load_words()
        self.load_nicknames()
        phrase = []
        pattern = self.random_pattern()[:-2].split(u"_+_")
        for gram in pattern:
            if u"<username>" in gram:
                if username is None:
                    username = random.choice(self.nicknames)
                phrase.append(username)
                continue
            phrase.append(random.choice(self.gram[gram]))
        phrase = self.phrase_refine(phrase)
        self.sentence_stats(len(phrase), len(pattern))
        if len(phrase) > 140: return self.generate_phrase_cheap(username)
        # for i in pattern:
        #     print i,
        # print
        return phrase

    def load_patterns(self):
        with codecs.open("patterns.txt", "r", "utf-8") as f:
            for line in f:
                self.sentence_patterns[line[:-2]] = 1

    def load_words(self):
        with codecs.open("words.txt", "r", "utf-8") as f:
            for line in f:
                line = line[:-2].split(u"\t")
                gram, words = line[0], line[1:]
                self.gram[gram] = words

    def save_patterns_and_words(self):
        with codecs.open("patterns.txt", "w", "utf-8") as f:
            f.write(u"\r\n".join(self.sentence_patterns.keys()))
        with codecs.open("words.txt", "w", "utf-8") as f:
            rows = [u"\t".join([gram, ] + self.gram[gram]) for gram in self.gram]
            f.write(u"\r\n".join(rows))
        with codecs.open("info.txt", "w", "utf-8") as f:
            f.write(str(len(self.sentence_patterns.keys())))

    def exclude_rare_patterns(self):
        stats = {}
        sorted_sp = sorted(self.sentence_patterns.items(), key=operator.itemgetter(1), reverse=True)
        for i in sorted_sp:
            if i[1] in stats:
                stats[i[1]] += 1
            else:
                stats[i[1]] = 1

        ##
        sorted_stats = sorted(stats.items(), key=operator.itemgetter(1), reverse=True)
        # for i in sorted_stats:
        #     print i[0], i[1]
        ##

        result = {}
        for p in self.sentence_patterns:
            if self.sentence_patterns[p] > 30: #rare_patterns here
                result[p] = self.sentence_patterns[p]

        self.sentence_patterns = result


    def update_dataset(self, clear=False, files_=False):
        self.load_exceptions()
        if not clear:
            self.load_patterns()
            self.load_words()
        if files_: return self.many_files()
        Phrase.initiate_mystem()
        self.load_mystem_array()
        self.refine_sentence_patterns()
        self.save_patterns_and_words()

    def many_files(self):
        import os
        for f in [f for f in os.listdir("texts")]:
            self.current_file = f
            shutil.copy2('texts/' + f, 'input.txt')
            Phrase.initiate_mystem()
            self.load_mystem_array()
            self.refine_sentence_patterns()
        self.exclude_rare_patterns()
        self.save_patterns_and_words()


# Phrase.initiate_mystem()
x = Phrase()
# print len(x.mystem)
# for i in x.mystem:
#     print i


x.update_dataset(clear=True, files_=True)


# for i in range(10):
#     phrase = x.generate_phrase_cheap()
#     print  phrase#, len(phrase)
#     print