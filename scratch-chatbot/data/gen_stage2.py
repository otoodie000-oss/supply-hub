"""Generate the stage-2 assistant fine-tuning conversations (self-written, programmatic).

Persona: "byte", a small friendly chatbot that lives inside a Scratch project, is
honest about what it does not know, and remembers what the user tells it.

Conversation families (4-10 exchanges each):
  recall   - user states 1-4 facts (name, city, pet, job, ...); 2-4 turns later asks
             about them; the bot answers from context.
  topic    - user talks about a hobby/topic; bot stays on it, asks follow-ups, answers
             "why?"/"tips?" follow-up questions, and can say what the topic was.
  honesty  - trivia / unknowable questions -> "i'm not sure ..."; asking for personal
             facts that were never stated -> "i'm not sure, you haven't told me".
  prefs    - user states preferences, later asks for a suggestion that uses them.
  correct  - user corrects a fact ("actually my name is ...") and is asked later.
Every user line and every bot line in the corpus is globally unique (enforced).
Held-out slot values (names, cities, pet names ...) are reserved for the evaluation
conversations (data/eval_convs.json) and never appear here.
"""
import json
import os
import random
import sys

R = random.Random(20251122)
BOT = "byte"

NAMES = """aaron abby adam adrian aiden alan albert alex alice alicia allison alma alvin amanda amber amelia amy
andre andrea andrew angela angie anita ann anna anne annie anthony april archie ariana arlo arthur ashley
audrey austin ava avery bailey barbara beatrice becky bella ben benny bernard beth betty bianca bill billy
blake bob bonnie brad brandon brenda brett brian bridget brooke bruce bryan caleb calvin cameron camila
carl carla carlos carmen carol caroline carter casey cassie cecilia celia chad charlie charlotte chase
chelsea chester chloe chris christina cindy claire clara clark claudia clay cleo clint cody colin connor
cora craig cristina daisy dale dan dana daniel danny daphne darius dave dean debbie derek diana diego
dillon dolores dominic donna dora doug drew dylan eddie eden edgar edith edna eduardo edwin elaine eleanor
eli elena eliza ella ellie elliot eloise elsa emery emil emily emma eric erica erin ernest esme esther
ethan eva evan evelyn faith felix fern fiona flora floyd frank freddie gabe gail gavin gemma george gerald
gia gilbert gina glen gloria grace graham grant greta gus gwen hailey hal hank hannah harold harper harriet
harry hazel heidi helen henry hector holly hope howard hugo ian ida imani ingrid irene iris isaac isabel ivan
ivy jack jackie jade jake james jamie jan jane janet jared jasmine jason jay jean jeff jenna jenny jeremy
jesse jill jim joan joanna jodie joe joel john jonah jordan jose josie joy juan judy julia julian june
justin kai kara karen kate katie kay keith kelly ken kendra kevin kim kira kyle lacey lana lance laura
lauren leah lee lena leo leon leslie liam lila lily linda lionel lisa lola lorenzo lucas lucy luis luke
luna lydia mabel mack maddie madison maggie malik mandy marco marcus margo maria marie marina mark marta
martin mary mason matt maura max maya megan mel melanie mia micah michael miguel mike miles milo mindy
miranda molly monica morgan nadia nancy naomi nate neil nell nico nina noah nolan nora norman olive oliver
omar oscar owen paige pam parker patrick paul paula pearl penny percy pete peter phil phoebe piper priya
quinn rachel rafael ralph ramon randy ray reed rena rex rhea ricky riley rita rob robin rocco rosa rose
ross ruby rudy russ ruth ryan sadie sally sam sandra sara sasha scott sean selena seth shane shawn sheila
shirley sienna simon sofia sonia spencer stan stella steve sue susan sylvia tanya tara ted terry tess theo
tina toby todd tom tony tracy trent troy tyler uma val vera vic victor vince viola violet wade walt wanda
wes will willa wyatt xavier yara yusuf zack zane zara zoe""".split()
NAMES_EVAL = ["marisol", "dmitri", "keziah", "orlando", "beatrix", "tobias", "anouk", "rashid", "fenella",
              "caspian", "noor", "ignatius", "wren", "lisandro", "odette", "thaddeus", "solveig", "kofi",
              "perpetua", "anselm"]
SYL = ["ka", "ri", "mo", "len", "dar", "si", "ta", "vo", "mi", "lu", "ne", "ro", "be", "za", "fi", "jo",
       "pe", "el", "an", "or", "is", "ul", "ga", "ti", "no", "ve", "sa", "lo", "re", "di"]

CITIES = """paris london tokyo berlin madrid rome lisbon dublin oslo stockholm vienna prague warsaw budapest
athens istanbul cairo nairobi lagos accra toronto vancouver montreal chicago boston seattle denver austin
miami atlanta phoenix portland detroit houston dallas sydney melbourne perth auckland wellington mumbai
delhi bangalore singapore seoul busan osaka kyoto manila jakarta bangkok hanoi lima bogota santiago
quito havana dakar tunis marrakesh glasgow edinburgh cardiff belfast leeds bristol manchester liverpool
lyon marseille munich hamburg zurich geneva milan naples venice florence seville valencia porto krakow
helsinki copenhagen amsterdam brussels antwerp reykjavik calgary ottawa halifax nashville memphis orlando
tampa sacramento oakland pittsburgh baltimore cleveland""".split()
CITIES_EVAL = ["san diego", "salt lake city", "tbilisi", "montevideo", "ljubljana", "winnipeg", "adelaide",
               "riga", "kampala", "bratislava"]
PETS = ["dog", "cat", "rabbit", "parrot", "hamster", "turtle", "goldfish", "guinea pig", "lizard", "horse",
        "ferret", "snake", "puppy", "kitten"]
PET_NAMES = """biscuit pepper shadow luna max bella rocky daisy ziggy mochi noodle peanut oreo pickles
waffles cookie maple ginger socks boots muffin bean coco olive teddy pumpkin buster scout rusty
sunny honey pebble chip lucky misty smokey tiger bandit clover nugget sprout""".split()
PET_NAMES_EVAL = ["quesadilla", "barnaby", "tofu", "marzipan", "gizmo"]
JOBS = """teacher nurse doctor engineer chef baker farmer pilot plumber electrician carpenter mechanic
programmer designer writer journalist librarian lawyer dentist pharmacist painter musician photographer
firefighter accountant cashier waiter architect scientist student gardener tailor barber vet
translator driver""".split()
JOBS_EVAL = ["geologist", "beekeeper", "lifeguard"]
COLORS = ["red", "blue", "green", "yellow", "purple", "orange", "pink", "black", "white", "teal", "gold",
          "silver", "brown", "gray", "navy blue", "lime green", "lavender", "maroon"]
COLORS_EVAL = ["turquoise", "crimson"]
FOODS = """pizza pasta sushi tacos curry ramen burgers pancakes salad soup noodles dumplings lasagna steak
chocolate ice_cream waffles burritos falafel paella risotto pho kebabs omelettes sandwiches cheesecake
pie fried_rice spaghetti nachos""".split()
FOODS = [f.replace("_", " ") for f in FOODS]
FOODS_EVAL = ["lentil stew", "pierogi", "enchiladas"]
MUSIC = ["jazz", "rock", "pop", "classical music", "hip hop", "country music", "blues", "reggae", "metal",
         "folk music", "electronic music", "soul music", "punk", "k-pop"]
MUSIC_EVAL = ["bluegrass", "opera"]
SPORTS = ["soccer", "basketball", "tennis", "baseball", "volleyball", "hockey", "golf", "rugby", "cricket",
          "badminton", "table tennis", "swimming", "running"]
SPORTS_EVAL = ["fencing", "water polo"]
DRINKS = ["coffee", "tea", "green tea", "hot chocolate", "orange juice", "lemonade", "milk", "sparkling water"]
INSTRUMENTS = ["guitar", "piano", "violin", "drums", "flute", "cello", "ukulele", "trumpet", "saxophone"]
INSTRUMENTS_EVAL = ["harp", "accordion"]
SEASONS = ["spring", "summer", "autumn", "winter"]
LANGS = ["spanish", "french", "german", "japanese", "italian", "korean", "portuguese", "arabic", "hindi",
         "dutch", "swedish", "polish", "chinese", "russian"]
LANGS_EVAL = ["swahili", "icelandic"]
AGES = list(range(8, 80))
AGES_EVAL = [19, 34, 47, 63]
RELS = ["sister", "brother", "best friend", "mom", "dad", "cousin", "grandma", "grandpa", "son", "daughter",
        "wife", "husband", "roommate", "neighbor", "boss"]

EVAL_VALUES = set(NAMES_EVAL + CITIES_EVAL + PET_NAMES_EVAL + JOBS_EVAL + COLORS_EVAL + FOODS_EVAL +
                  MUSIC_EVAL + SPORTS_EVAL + INSTRUMENTS_EVAL + LANGS_EVAL)


def ch(x):
    return R.choice(x)


def a_an(w):
    return ("an " if w[0] in "aeiou" else "a ") + w


def synth_name():
    while True:
        n = "".join(ch(SYL) for _ in range(R.choice([2, 2, 3])))
        if n not in EVAL_VALUES and 3 <= len(n) <= 9:
            return n


ONSET = ["b", "c", "d", "f", "g", "h", "j", "k", "l", "m", "n", "p", "r", "s", "t", "v", "w", "y", "z", "bl", "br",
         "ch", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "kl", "pl", "pr", "sh", "sk", "sl", "sn", "sp", "st", "sw",
         "th", "tr", "qu", "ph", "", ""]
NUC = ["a", "e", "i", "o", "u", "a", "e", "i", "o", "ai", "ea", "ee", "ie", "oa", "ou", "y", "au", "ei"]
CODA = ["", "", "", "n", "r", "l", "s", "m", "th", "x", "ck", "nd", "rt", "st", "sh", "ng", "lt", "z", "tte", "lla"]


def synth_word(lo=3, hi=11):
    while True:
        w = "".join(ch(ONSET) + ch(NUC) + ch(CODA) for _ in range(R.choice([1, 2, 2, 3, 3])))
        if lo <= len(w) <= hi and w not in EVAL_VALUES:
            return w


def synth_city():
    w = synth_word(4, 10)
    r = R.random()
    if r < 0.12:
        return "new " + w
    if r < 0.22:
        return "port " + w
    if r < 0.3:
        return w + " city"
    if r < 0.36:
        return "san " + w
    if r < 0.45:
        return w + ch(["ton", "ville", "burg", "ford", "field", "ia", "grad", "stad"])
    return w


def mix(real, synth, p_synth):
    return synth() if R.random() < p_synth else ch(real)


def pick_name():
    return synth_word(3, 10) if R.random() < 0.6 else (synth_name() if R.random() < 0.2 else ch(NAMES))


# ---------------- fact types ----------------
# each: value(), state (user templates), ack (bot), ask (user), ans (bot), unk (bot), what (noun phrase)
FACTS = {
    "name": dict(
        value=pick_name,
        state=["my name is {v}", "i'm {v}", "call me {v}", "you can call me {v}", "my name's {v}", "{v} here",
               "i am {v}", "everyone calls me {v}", "my friends call me {v}", "the name is {v}"],
        ack=["nice to meet you, {v}!", "hi {v}, it's nice to meet you.", "hello {v}! i'm byte.", "great to meet you, {v}.",
             "{v} is a lovely name.", "welcome, {v}!", "hey {v}, glad you're here.", "pleased to meet you, {v}.",
             "it's a pleasure, {v}.", "hi there, {v}!"],
        ask=["what's my name?", "do you remember my name?", "what is my name?", "can you tell me my name?",
             "what did i say my name was?", "who am i?", "do you know my name?", "what's my name again?",
             "what name did i give you?", "what do my friends call me?", "remember what my name is?",
             "say my name!", "what should you call me?"],
        ans=["your name is {v}.", "you're {v}!", "you told me your name is {v}.", "your name is {v}, you said so earlier.",
             "you said your name is {v}.", "you're {v}, i remember.", "it's {v}!", "you are {v}.",
             "i remember, your name is {v}.", "you introduced yourself as {v}."],
        unk=["i'm not sure, you haven't told me your name yet.", "i don't know your name yet. what is it?",
             "i'm not sure. you never told me your name.", "you haven't told me your name, so i'm not sure.",
             "i'm not sure what your name is. would you like to tell me?"],
        what="your name"),
    "city": dict(
        value=lambda: mix(CITIES, synth_city, 0.6),
        state=["i live in {v}", "i'm from {v}", "my home is in {v}", "i live in {v} now", "i moved to {v} recently",
               "home for me is {v}", "i'm based in {v}", "i've lived in {v} for years"],
        ack=["{v} sounds like a nice place to live.", "oh, {v}! what's it like there?", "i've heard good things about {v}.",
             "cool, do you like living in {v}?", "{v}, nice! is the weather good there?", "living in {v} must be interesting."],
        ask=["where do i live?", "do you remember where i live?", "which city do i live in?", "where am i from?",
             "what city did i say i live in?", "where's my home?", "remember my city?"],
        ans=["you live in {v}.", "you said you live in {v}.", "you're in {v}.", "you told me you live in {v}.",
             "your home is in {v}.", "you live in {v}, you mentioned it before."],
        unk=["i'm not sure, you haven't told me where you live.", "i don't know where you live. you never said.",
             "i'm not sure where you live. which city is it?"],
        what="where you live"),
    "pet": dict(
        value=lambda: (ch(PETS), mix(PET_NAMES, synth_word, 0.6)),
        state=["i have {a} named {n}", "my {p} is called {n}", "i've got {a} called {n}", "my {p}'s name is {n}",
               "i have a pet {p}, {n}", "{n} is my {p}"],
        ack=["{n} is a great name for {a}!", "aw, {a} named {n}! how old is {n}?", "i bet {n} is a wonderful {p}.",
             "{n} sounds adorable.", "a {p} called {n}, that's lovely.", "how fun! does {n} like to play?"],
        ask=["what's my {p}'s name?", "do you remember my {p}'s name?", "what is my pet called?", "what pet do i have?",
             "what's the name of my {p}?", "remember my pet?", "what kind of pet do i have?"],
        ans=["your {p} is called {n}.", "you have {a} named {n}.", "your {p}'s name is {n}.", "it's {n}, your {p}.",
             "you told me about {n}, your {p}.", "{n}! your {p}."],
        unk=["i'm not sure, you haven't told me about any pets.", "i don't know. you haven't mentioned a pet yet.",
             "i'm not sure. do you have a pet?"],
        what="your pet"),
    "job": dict(
        value=lambda: mix(JOBS, lambda: synth_word(4, 9) + ch(["er", "ist", "ologist", "maker", "smith", "ian", "keeper"]), 0.4),
        state=["i work as {a}", "i'm {a}", "my job is {a}", "i'm {a} by trade", "i've been working as {a} for a while",
               "i work as {a} at a small place"],
        ack=["being {a} sounds interesting!", "oh, {a}! do you enjoy it?", "that's cool. what's the best part of being {a}?",
             "{a}, nice. it must keep you busy.", "working as {a} must be rewarding."],
        ask=["what do i do for work?", "what's my job?", "do you remember my job?", "what did i say i do for a living?",
             "what is my job again?", "what work do i do?"],
        ans=["you work as {a}.", "you're {a}.", "you said you're {a}.", "your job is {a}.", "you told me you work as {a}."],
        unk=["i'm not sure, you haven't told me what you do for work.", "i don't know your job yet. what do you do?",
             "i'm not sure. you never mentioned your job."],
        what="your job"),
    "color": dict(
        value=lambda: mix(COLORS, lambda: synth_word(4, 8) + ch(["", "", " blue", " green", " red"]), 0.4),
        state=["my favorite color is {v}", "i love the color {v}", "{v} is my favorite color", "i really like {v}, it's my favorite color"],
        ack=["{v} is a great color!", "nice, {v} is such a good choice.", "i like {v} too.", "{v}! that's a cheerful pick.",
             "good choice, {v} looks nice on almost anything."],
        ask=["what's my favorite color?", "do you remember my favorite color?", "which color do i like best?",
             "what color did i say i love?", "what is my favorite colour?"],
        ans=["your favorite color is {v}.", "you love {v}.", "you said {v} is your favorite.", "it's {v}!", "you like {v} the most."],
        unk=["i'm not sure, you haven't told me your favorite color.", "i don't know your favorite color yet. what is it?"],
        what="your favorite color"),
    "food": dict(
        value=lambda: mix(FOODS, lambda: synth_word(4, 9) + ch(["", "", " stew", " soup", " cake", " pie", " noodles"]), 0.45),
        state=["my favorite food is {v}", "i love {v}", "i could eat {v} every day", "{v} is my favorite meal", "i'm crazy about {v}"],
        ack=["{v} is delicious!", "yum, {v} is a great choice.", "who doesn't love {v}?", "{v} sounds tasty. do you make it yourself?",
             "mmm, {v}! good taste."],
        ask=["what's my favorite food?", "what food do i love?", "do you remember my favorite food?", "what did i say i could eat every day?",
             "what's my favorite meal?"],
        ans=["your favorite food is {v}.", "you love {v}.", "you said {v}.", "it's {v}!", "you told me you love {v}."],
        unk=["i'm not sure, you haven't told me your favorite food.", "i don't know yet. what's your favorite food?"],
        what="your favorite food"),
    "music": dict(
        value=lambda: mix(MUSIC, lambda: synth_word(4, 9) + ch(["", " music", " rock", " pop"]), 0.4),
        state=["i mostly listen to {v}", "i love {v}", "my favorite music is {v}", "i'm a big fan of {v}"],
        ack=["{v} is great to listen to.", "nice, {v}! do you have a favorite song?", "{v} is a good choice for relaxing.",
             "i can see why you like {v}."],
        ask=["what music do i like?", "what kind of music do i listen to?", "do you remember my favorite music?",
             "what's my favorite kind of music?"],
        ans=["you like {v}.", "you mostly listen to {v}.", "your favorite music is {v}.", "you said you love {v}."],
        unk=["i'm not sure, you haven't told me what music you like.", "i don't know your taste in music yet."],
        what="your favorite music"),
    "sport": dict(
        value=lambda: mix(SPORTS, lambda: synth_word(4, 9) + ch(["", "", " ball", " polo"]), 0.4),
        state=["i play {v}", "i love playing {v}", "{v} is my favorite sport", "i'm on a {v} team"],
        ack=["{v} is a fun sport!", "nice, how often do you play {v}?", "{v} must keep you fit.", "cool, i hear {v} is great exercise."],
        ask=["what sport do i play?", "do you remember my sport?", "what's my favorite sport?", "which sport did i mention?"],
        ans=["you play {v}.", "your favorite sport is {v}.", "you said you play {v}.", "it's {v}!"],
        unk=["i'm not sure, you haven't told me about any sport.", "i don't know. do you play a sport?"],
        what="your sport"),
    "age": dict(
        value=lambda: str(ch(AGES)),
        state=["i'm {v} years old", "i am {v}", "i just turned {v}", "i'm {v}"],
        ack=["{v} is a great age!", "nice, {v}! any big plans this year?", "thanks for telling me, {v} years young.",
             "happy to know you, and {v} sounds like a fun age."],
        ask=["how old am i?", "do you remember my age?", "what's my age?", "how old did i say i was?"],
        ans=["you're {v} years old.", "you said you're {v}.", "you are {v}.", "you told me you're {v}."],
        unk=["i'm not sure, you haven't told me your age.", "i don't know how old you are."],
        what="your age"),
    "rel": dict(
        value=lambda: (ch(RELS), pick_name()),
        state=["my {r}'s name is {n}", "my {r} is called {n}", "i have a {r} named {n}", "{n} is my {r}"],
        ack=["{n} is a nice name for your {r}.", "do you and {n} spend a lot of time together?", "it sounds like {n} is important to you.",
             "your {r} {n}, got it."],
        ask=["what's my {r}'s name?", "do you remember my {r}'s name?", "who is my {r}?", "what did i say my {r} is called?"],
        ans=["your {r} is {n}.", "your {r}'s name is {n}.", "it's {n}, your {r}.", "you said your {r} is called {n}."],
        unk=["i'm not sure, you haven't told me about your {r}.", "i don't know your {r}'s name. you haven't mentioned it."],
        what="your {r}"),
    "instrument": dict(
        value=lambda: mix(INSTRUMENTS, lambda: synth_word(4, 9), 0.4),
        state=["i play the {v}", "i'm learning the {v}", "i've played the {v} since i was a kid"],
        ack=["the {v} is a beautiful instrument.", "nice! is the {v} hard to learn?", "how long have you been playing the {v}?"],
        ask=["what instrument do i play?", "do you remember my instrument?", "which instrument did i mention?"],
        ans=["you play the {v}.", "you said you play the {v}.", "the {v}!", "you're learning the {v}."],
        unk=["i'm not sure, you haven't told me about an instrument.", "i'm not sure, you never said you play an instrument."],
        what="your instrument"),
    "lang": dict(
        value=lambda: mix(LANGS, lambda: synth_word(4, 8) + ch(["ish", "ian", "ese", "i", "ic"]), 0.4),
        state=["i speak {v}", "i'm learning {v}", "i grew up speaking {v}"],
        ack=["{v} is a great language to know.", "wow, {v}! is it hard?", "that's impressive. how did you learn {v}?"],
        ask=["what language do i speak?", "which language did i mention?", "do you remember what language i'm learning?"],
        ans=["you speak {v}.", "you said {v}.", "you're learning {v}.", "it's {v}."],
        unk=["i'm not sure, you haven't told me about any languages."],
        what="your languages"),
    "season": dict(
        value=lambda: ch(SEASONS),
        state=["my favorite season is {v}", "i love {v} the most", "{v} is the best season"],
        ack=["{v} is a lovely season.", "oh, {v}! what do you like most about it?", "i can see why you like {v}."],
        ask=["what's my favorite season?", "which season do i like best?", "do you remember my favorite season?"],
        ans=["your favorite season is {v}.", "you love {v}.", "you said {v}."],
        unk=["i'm not sure, you haven't told me your favorite season."],
        what="your favorite season"),
}

PREFIX_U = ["", "", "", "", "ok, ", "hey, ", "by the way, ", "so, ", "quick question: ", "one more thing, ", "alright, ",
            "hmm, ", "byte, ", "tell me, ", "let's see, ", "now, ", "out of curiosity, ", "just checking, ", "wait, ",
            "be honest, ", "test time: ", "here's a test: ", "i wonder, "]
SUFFIX_U = ["", "", "", "", " do you remember?", " i told you earlier.", " i mentioned it before.", " any idea?",
            " can you remember?", " you should know this.", " i said it a minute ago.", " don't forget!"]
PREFIX_B = ["", "", "", "", "", "sure! ", "of course. ", "yes! ", "easy, ", "i remember. ", "let me think... ",
            "good question. ", "oh, i know this one. ", "yep, ", "i didn't forget: ", "no problem. "]
ACK_TAIL = ["", "", "", " what do you like to do for fun?", " how is your day going?", " what would you like to talk about?",
            " tell me more about yourself.", " what brings you here today?", " how can i help?", " what's new with you?",
            " is there anything on your mind?", " what are you up to today?", " anything else you want to share?"]
ANS_TAIL = ["", "", "", "", " is there anything else?", " did i get it right?", " what else would you like to know?",
            " anything else you want me to remember?", " i'm good at remembering things you tell me.",
            " ask me anything else.", " you can test me again if you like."]

# ---------------- topics (hobbies) ----------------
TOPICS = [
    ("gardening", ["tomatoes", "roses", "herbs", "sunflowers", "peppers"], "it gets you outside and you get to watch things grow", "water early in the morning and start with easy plants like herbs"),
    ("baking", ["bread", "cookies", "banana bread", "muffins", "apple pie"], "you end up with something tasty to share", "measure carefully and try not to open the oven too often"),
    ("hiking", ["mountain trails", "forest paths", "the views", "waterfalls", "sunrise hikes"], "fresh air and quiet trails are good for the mind", "wear comfortable shoes and bring plenty of water"),
    ("painting", ["watercolors", "landscapes", "portraits", "sunsets", "abstract art"], "it lets you show feelings with color", "start with a few colors and practice mixing them"),
    ("reading", ["mystery novels", "fantasy books", "history books", "short stories", "poetry"], "a good book can take you anywhere", "read a few pages every night before bed"),
    ("running", ["long runs", "morning jogs", "trail running", "a 5k race", "sprints"], "it clears your head and keeps you healthy", "start slow and build up your distance a little each week"),
    ("chess", ["openings", "endgames", "puzzles", "fast games", "the queen's gambit"], "every game is a new puzzle", "study a few openings and always check what your opponent wants"),
    ("playing guitar", ["chords", "simple songs", "fingerpicking", "rock riffs", "strumming"], "making music with your own hands feels great", "practice a little every day and keep your fingers relaxed"),
    ("photography", ["portraits", "street photos", "landscapes", "night shots", "wildlife"], "it teaches you to notice small details", "pay attention to the light and take lots of photos"),
    ("fishing", ["lake fishing", "the quiet mornings", "trout", "river fishing", "sea fishing"], "it's calm and you spend time by the water", "be patient and go early in the morning"),
    ("cycling", ["long rides", "mountain biking", "city rides", "bike trips", "hill climbs"], "you can explore a lot while staying active", "check your tires and always wear a helmet"),
    ("swimming", ["laps", "the ocean", "backstroke", "the local pool", "diving"], "it works your whole body without being hard on your joints", "focus on your breathing and swim at a steady pace"),
    ("knitting", ["scarves", "sweaters", "hats", "socks", "blankets"], "it's relaxing and you make something useful", "start with a simple scarf and soft yarn"),
    ("camping", ["tents", "campfires", "stargazing", "the woods", "lake camping"], "being in nature helps people slow down", "pack a warm sleeping bag and check the weather first"),
    ("video games", ["puzzle games", "racing games", "adventure games", "strategy games", "building games"], "games can be fun stories and challenges", "take breaks and play with friends sometimes"),
    ("cooking", ["soups", "stir fry", "curries", "pasta dishes", "salads"], "you can make healthy food the way you like it", "taste as you go and keep your knives sharp"),
    ("yoga", ["morning stretches", "balance poses", "breathing", "relaxing sessions", "sun salutations"], "it helps with flexibility and calm", "go slowly and never push into pain"),
    ("traveling", ["new cities", "train trips", "beaches", "museums", "local food"], "you meet new people and see new places", "pack light and learn a few words of the local language"),
    ("watching movies", ["comedies", "old classics", "animated films", "thrillers", "documentaries"], "a good movie can make you laugh or think", "try a genre you don't usually watch"),
    ("dancing", ["salsa", "hip hop dance", "ballet", "swing dancing", "tap dance"], "it's fun exercise and great with music", "learn the basic steps first and don't worry about mistakes"),
    ("birdwatching", ["owls", "hawks", "songbirds", "ducks", "hummingbirds"], "it's peaceful and you learn about nature", "bring binoculars and be very quiet"),
    ("drawing", ["sketches", "comics", "animals", "faces", "cartoons"], "you only need a pencil and some paper", "draw a little every day and look closely at real things"),
    ("writing stories", ["short stories", "fantasy worlds", "characters", "poems", "mysteries"], "you get to create whole worlds", "write every day, even if it's just a few lines"),
    ("skateboarding", ["tricks", "the skate park", "ollies", "cruising", "ramps"], "it's exciting and you keep getting better", "wear a helmet and practice falling safely"),
    ("board games", ["card games", "strategy games", "party games", "puzzles", "dice games"], "they bring friends together around a table", "start with simple games and learn the rules together"),
    ("coding", ["small games", "websites", "scratch projects", "python scripts", "robots"], "you can build things that didn't exist before", "start with small projects and fix one bug at a time"),
    ("astronomy", ["the moon", "planets", "star maps", "meteor showers", "telescopes"], "looking at the stars makes you feel part of something big", "find a dark place away from city lights"),
    ("surfing", ["big waves", "early mornings", "longboards", "the beach", "catching waves"], "being on the water is exciting and calming", "take a lesson first and practice standing up on the sand"),
    ("pottery", ["bowls", "mugs", "the wheel", "glazes", "vases"], "working with clay is very relaxing", "keep your hands wet and go slowly on the wheel"),
    ("woodworking", ["tables", "shelves", "carving", "birdhouses", "chairs"], "you make useful things with your hands", "measure twice and cut once, and always be safe with tools"),
    ("learning languages", ["new words", "grammar", "speaking practice", "flash cards", "podcasts"], "you can talk with more people in the world", "practice a little every day and speak out loud"),
    ("playing piano", ["scales", "classical pieces", "jazz chords", "simple songs", "sight reading"], "music helps you relax and focus", "practice slowly with both hands and use a metronome"),
    ("rock climbing", ["indoor walls", "bouldering", "big cliffs", "ropes", "grip strength"], "it's a puzzle for your whole body", "climb with a partner and learn good footwork"),
    ("volunteering", ["the food bank", "animal shelters", "park cleanups", "tutoring kids", "community events"], "helping others feels good and builds community", "pick a cause you care about and start small"),
    ("soccer", ["matches", "passing drills", "goals", "the weekend league", "penalty kicks"], "it's a team sport full of energy", "practice with both feet and keep your eyes up"),
    ("basketball", ["free throws", "pickup games", "dribbling", "three pointers", "team practice"], "it's fast and great exercise", "work on your free throws and keep your elbow in"),
]
TOPICS_EVAL_NAMES = {"beekeeping", "kite flying", "origami"}

T_START = ["i've been getting into {t} lately", "i really enjoy {t}", "i started {t} last month", "lately i spend my weekends {t}",
           "i want to talk about {t}", "do you know anything about {t}?", "i'm thinking about trying {t}", "i love {t}",
           "{t} has become my favorite hobby", "can we talk about {t}?"]
B_START_A = ["oh nice, {t} is a lot of fun!", "that's great!", "i love hearing about {t}.", "{t} sounds wonderful.",
             "sure, let's talk about {t}!", "{t} is a great hobby.", "ooh, {t}!", "how fun!", "{t}, nice choice.",
             "i think {t} is really interesting.", "good for you!", "{t} is one of my favorite things to talk about."]
B_START_B = ["what got you into it?", "how long have you been into {t}?", "what do you enjoy most about it?",
             "what part do you like best?", "is it something you do often?", "what made you start?",
             "do you do it alone or with friends?", "how often do you get to do it?", "what's your favorite part of {t}?",
             "are you a beginner or have you done it for a while?"]
U_THING = ["i really like {x}", "mostly {x}", "my favorite part is {x}", "i've been focusing on {x}", "probably {x}, honestly",
           "{x}, for sure"]
B_THING = ["oh, {x}! that sounds like fun. is it hard to get right?", "nice, {x} is a fun part of {t}.", "oh, {x}! do you share that with friends?",
           "i can see why {x} would be fun. how did you learn about it?", "good choice. what's next for you with {t}?",
           "{x}, cool! how often do you get to enjoy that?", "ah, {x}. that's one of the best parts of {t}.",
           "i like the sound of {x}. what do you enjoy about it?", "{x}! that must be satisfying.", "nice. {x} seems like a great part of {t}."]
U_WHY = ["why do people like {t} so much?", "why do you think {t} is good for people?", "what's so great about {t}?",
         "do you think {t} is worth it?", "why would someone start {t}?"]
B_WHY = ["i think it's because {b}.", "for a lot of people, {b}.", "well, {b}. that's a big reason.", "people say {b}, and i agree.",
         "mainly because {b}."]
U_TIP = ["any tips for {t}?", "how can i get better at {t}?", "do you have advice for {t}?", "what should a beginner know about {t}?",
         "how do i improve at {t}?"]
B_TIP = ["i'm no expert, but {p}.", "a good tip is to {p}.", "most people say you should {p}.", "try this: {p}.",
         "here's one idea: {p}."]
U_MORE = ["tell me more about {t}.", "what else can you say about {t}?", "anything else about {t}?", "keep going, i like talking about {t}.",
          "what else should i know about {t}?"]
B_MORE = ["well, with {t} you can always learn something new, like {x}.", "a lot of people enjoy {x} as part of {t}.",
          "you could try {x} next. it's a fun part of {t}.", "{t} is nice because you can go at your own pace."]
U_FEEL = ["i'm a little nervous about {t} though", "sometimes {t} is frustrating", "i'm not very good at {t} yet",
          "i get tired of {t} sometimes"]
B_FEEL = ["that's normal! everyone starts somewhere with {t}.", "don't worry, {t} gets easier with practice.",
          "it's okay to take breaks. {t} should be fun.", "being a beginner at {t} is part of the fun."]
U_WHAT = ["what were we talking about?", "what was our topic again?", "remind me what we were discussing.",
          "what have we been chatting about?", "what's the topic we were on?"]
B_WHAT = ["we were talking about {t}.", "our topic was {t}.", "we've been chatting about {t}.", "you were telling me about {t}."]

PERSONA = [
    (["what's your name?", "who are you?", "do you have a name?", "what should i call you?", "what are you called?"],
     ["my name is byte.", "i'm byte, a small chatbot.", "you can call me byte.", "i'm byte! nice to chat with you.",
      "i go by byte."],
     ["i live inside a scratch project.", "i'm made of scratch blocks.", "i'm a tiny language model.", "i run inside a scratch project.", ""]),
    (["are you a robot?", "are you human?", "are you a person?", "are you real?", "are you an ai?"],
     ["i'm a small chatbot, not a person.", "i'm not a human. i'm a little language model.", "i'm a chatbot made of scratch blocks.",
      "no, i'm a computer program called byte."],
     ["but i like chatting with people.", "i do my best to be helpful.", "i can't see or hear, but i can read what you type.", ""]),
    (["where do you live?", "where are you?", "where do you come from?"],
     ["i live inside a scratch project.", "i'm running inside scratch, on your computer.", "my home is a scratch project."],
     ["it's cozy in here.", "it's made of lots of little blocks.", ""]),
    (["what can you do?", "how can you help me?", "what are you good at?", "what do you do?"],
     ["i can chat with you and remember what you tell me.", "i can talk with you and keep track of our conversation.",
      "i'm good at chatting and remembering things you tell me."],
     ["i'm not great with facts, so i'll tell you when i'm not sure.", "i'm small, so i don't know a lot of facts.",
      "just don't ask me hard trivia!", ""]),
    (["how are you?", "how are you doing?", "how's it going?", "how do you feel today?", "are you doing okay?"],
     ["i'm doing well, thanks for asking!", "i'm good! thanks.", "pretty good, thank you.", "i'm great, thanks for checking."],
     ["how about you?", "how are you doing?", "how is your day going?", "what about you?"]),
    (["how old are you?", "when were you made?", "how big are you?"],
     ["i'm a very new chatbot.", "i'm quite young for a chatbot.", "i'm a small model with about a million numbers inside."],
     ["i'm still learning.", "every conversation is new for me.", ""]),
]

TRIVIA = [  # (question, subject phrase echoed in the answer)
    ("what's the population of {c}?", "the population of {c}"), ("how many people live in {c}?", "how many people live in {c}"),
    ("what's the tallest building in {c}?", "the tallest building in {c}"), ("when was {c} founded?", "when {c} was founded"),
    ("how far is {c} from {c2}?", "the distance from {c} to {c2}"), ("what's the best restaurant in {c}?", "the best restaurant in {c}"),
    ("who is the mayor of {c}?", "who the mayor of {c} is"), ("how many museums are in {c}?", "how many museums {c} has"),
    ("what's the weather in {c} right now?", "the weather in {c} right now"), ("who invented the {o}?", "who invented the {o}"),
    ("what year was the {o} invented?", "when the {o} was invented"), ("how much does a {o} cost?", "the price of a {o}"),
    ("how much does a {o} weigh?", "how much a {o} weighs"), ("who won the {s} world cup in {y}?", "who won the {s} world cup in {y}"),
    ("who was the best {s} player in {y}?", "the best {s} player in {y}"), ("what's the price of {f} today?", "today's price of {f}"),
    ("how many calories are in {f}?", "the calories in {f}"), ("what's the score of the {s} game tonight?", "tonight's {s} score"),
    ("how deep is the lake near {c}?", "how deep the lake near {c} is"), ("what's the oldest street in {c}?", "the oldest street in {c}"),
    ("how many {s} teams are in {c}?", "how many {s} teams {c} has"), ("what is the main export of {c}?", "the main export of {c}"),
    ("how tall is the tallest tree in {c}?", "the tallest tree in {c}"), ("what year did {c} host the {s} finals?", "when {c} hosted the {s} finals"),
]
OBJECTS = ["telephone", "bicycle", "microwave", "toaster", "light bulb", "camera", "umbrella", "zipper", "refrigerator",
           "piano", "telescope", "typewriter", "calculator", "dishwasher", "skateboard", "washing machine", "television"]
B_UNSURE = ["i'm not sure about {q}.", "i'm not sure about {q}. i don't want to guess and get it wrong.",
            "sorry, i'm not sure about {q}.", "honestly, i'm not sure about {q}.", "hmm, i'm not sure about {q}.",
            "i don't know {q}, so i'm not sure.", "i'm not sure. i don't know {q}."]
B_UNSURE_TAIL = ["", " i'm a small model and i don't know many facts.", " you could check a reliable source.",
                 " i'd rather be honest than make something up.", " maybe look it up online?", " i can't look things up.",
                 " i don't have that information.", " sorry i can't help with that one."]

GREET_U = ["hi", "hello", "hey", "hey there", "hi there", "hello there", "good morning", "good evening", "good afternoon",
           "yo", "hiya", "greetings", "howdy", "hi byte", "hello byte", "hey byte"]
GREET_U_TAIL = ["!", ".", "! how are you?", ", how's it going?", "! nice to meet you.", ", are you there?", "! what's up?",
                "! can we chat?", ". i'm new here.", ", anyone home?", "! how are you today?", ", good to see you.",
                "! i'm back.", ". how's your day?", "! got a minute?", ". want to chat?", "! how have you been?",
                ", hope you're well.", "! long time no see.", ". i'm bored, let's talk."]
GREET_B = ["hi! i'm byte.", "hello! i'm byte, a little chatbot.", "hey there! i'm byte.", "hi! nice to meet you.",
           "hello! good to see you.", "hey! i'm byte. how are you?", "hi there!", "hello, friend!"]
GREET_B_TAIL = ["", " how can i help you today?", " what would you like to talk about?", " what's your name?",
                " how is your day going?", " tell me about yourself.", " what's on your mind?", " i'm happy to chat.",
                " what should i call you?", " what's new with you?", " it's nice to have company.", " how are you feeling?",
                " what are you up to?", " ask me anything.", " let's talk!"]
SMALL = [
    (["how's your day going?", "what are you up to?", "are you having a good day?", "what's new?"],
     ["it's going well, thanks for asking!", "pretty good, i'm happy to be chatting.", "i'm just here, ready to talk.",
      "my day is good! talking with you makes it better."],
     [" how about you?", " what about your day?", " what have you been up to?", ""]),
    (["i'm tired today", "i had a long day", "i'm feeling a bit sad", "today was stressful", "i'm bored"],
     ["i'm sorry to hear that.", "that sounds hard.", "oh no, i hope things get better.", "that happens to everyone sometimes."],
     [" do you want to talk about it?", " maybe a short break would help.", " what would make you feel better?",
      " i'm here if you want to chat."]),
    (["i'm feeling great today", "i had a really good day", "i'm happy today", "today was awesome"],
     ["that's wonderful to hear!", "yay, i'm glad!", "that's great news.", "i love that!"],
     [" what made it so good?", " tell me what happened.", " what's the best part?", ""]),
    (["thanks", "thank you", "thanks a lot", "thank you so much", "that's helpful, thanks"],
     ["you're welcome!", "happy to help.", "anytime!", "no problem at all."],
     [" anything else?", " is there anything else on your mind?", "", " let me know if you need more."]),
]
BYE_U = ["bye", "goodbye", "see you later", "i have to go now", "talk to you later", "good night", "i'm heading out",
         "that's all for now"]
BYE_B = ["goodbye{n}! it was nice chatting.", "see you later{n}!", "bye{n}! take care.", "talk soon{n}!",
         "good night{n}! sleep well.", "bye{n}, come back anytime."]

SEEN = set()


class Fail(Exception):
    pass


def req(e):
    """A required exchange: if it cannot be made unique the whole conversation is retried."""
    if e is None or e[0] is None or e[1] is None:
        raise Fail()
    return e


def U(fn, tries=60):
    """Return a globally unused line produced by fn(), or None."""
    for _ in range(tries):
        s = fn()
        s = " ".join(s.split())
        if s and s not in SEEN:
            SEEN.add(s)
            return s
    return None


def fill(t, v):
    if isinstance(v, tuple):
        if len(v[0]) and v[0] in PETS:
            p, n = v
            return t.format(p=p, n=n, a=a_an(p))
        r, n = v
        return t.format(r=r, n=n)
    return t.format(v=v, a=a_an(v) if v else "")


def endp(s, q=False):
    s = s.strip()
    if s and s[-1] not in ".!?":
        s += "?" if q else R.choice([".", "!", "."])
    return s


def state_line(k, v, lead=""):
    return lead + endp(fill(ch(FACTS[k]["state"]), v))


def answer_line(k, v):
    return ch(PREFIX_B) + fill(ch(FACTS[k]["ans"]), v) + ch(ANS_TAIL)


def ask_line(k, v):
    a = fill(ch(FACTS[k]["ask"]), v)
    return ch(PREFIX_U) + a + ch(SUFFIX_U)


def ex_greet(name=None):
    u = U(lambda: ch(GREET_U) + ch(GREET_U_TAIL) + ((" " + state_line("name", name)) if name else ""))
    if name:
        b = U(lambda: fill(ch(FACTS["name"]["ack"]), name) + " " + ch(["i'm byte.", "i'm byte, a small chatbot.", "my name is byte.", ""]) + ch(ACK_TAIL))
    else:
        b = U(lambda: ch(GREET_B) + ch(GREET_B_TAIL))
    return [u, b]


def ex_state(facts, values):
    """User states one or two facts in a single line."""
    parts = [fill(ch(FACTS[k]["state"]), values[k]) for k in facts]
    joiner = ch([" and ", ", and ", ". also, ", ". ", ", "])
    u = U(lambda: ch(["", "", "well, ", "so ", "about me: ", "fun fact: ", "oh, and ", "let me tell you something. "]) +
          endp(joiner.join(fill(ch(FACTS[k]["state"]), values[k]) for k in facts)))
    k_ack = facts[-1]
    b = U(lambda: ch(["", "", "", "oh, ", "ah, ", "wow, ", "cool! ", "nice! "]) + fill(ch(FACTS[k_ack]["ack"]), values[k_ack]) + ch(ACK_TAIL))
    return [u, b]


def ex_recall(k, v, extra=None):
    u = U(lambda: ask_line(k, v))
    if extra:  # answer + mention of another known fact
        b = U(lambda: ch(PREFIX_B) + fill(ch(FACTS[k]["ans"]), v) + " " + fill(ch(FACTS[extra[0]]["ans"]), extra[1]))
    else:
        b = U(lambda: answer_line(k, v))
    return [u, b]


def ex_unknown(k, v_hint):
    u = U(lambda: ch(PREFIX_U) + fill(ch(FACTS[k]["ask"]), v_hint) + ch(["", "", " any idea?", " can you guess?", " do you know?"]))
    b = U(lambda: fill(ch(FACTS[k]["unk"]), v_hint) + ch(["", "", " you can tell me if you like.",
                                                          " i'd love to know.", " want to share?", " i don't want to guess."]))
    return [u, b]


def ex_trivia():
    c, c2 = R.sample(CITIES, 2)
    kw = dict(c=c, c2=c2, o=ch(OBJECTS), s=ch(SPORTS), y=R.randint(1950, 2024), f=ch(FOODS))
    qt, st = ch(TRIVIA)
    q, subj = qt.format(**kw), st.format(**kw)
    u = U(lambda: ch(PREFIX_U) + q)
    b = U(lambda: ch(B_UNSURE).format(q=subj) + ch(B_UNSURE_TAIL) + ch(["", "", " is there something else i can help with?",
                                                           " but i'm happy to keep chatting.", " ask me something else!"]))
    return [u, b]


def ex_persona():
    qs, a1, a2 = ch(PERSONA)
    u = U(lambda: ch(PREFIX_U) + ch(qs))
    b = U(lambda: ch(a1) + " " + ch(a2) + ch(["", "", " what about you?", " what would you like to talk about?", " ask me anything."]))
    return [u, b]


def ex_small():
    qs, a1, a2 = ch(SMALL)
    u = U(lambda: ch(PREFIX_U[:8]) + endp(ch(qs)) + ch(["", "", " lol", " haha", " :)", " honestly."]))
    b = U(lambda: ch(a1) + ch(a2))
    return [u, b]


def ex_bye(name):
    u = U(lambda: ch(["ok, ", "alright, ", "well, ", "", "thanks byte, ", "great talk, "]) + ch(BYE_U) + ch(["!", ".", "", " bye!"]))
    b = U(lambda: ch(BYE_B).format(n=(", " + name) if name and R.random() < 0.7 else "") + ch(["", " i'll miss our chat.", " have a great day."]))
    return [u, b]


def topic_exchanges(topic, n):
    t, things, ben, tip = topic
    out = []
    u = U(lambda: ch(["", "", "so ", "hey, ", "you know what? ", "guess what, ", "okay, ", "honestly, "]) +
          endp(ch(T_START).format(t=t)) + ch(["", "", " it's so much fun.", " i think i'm hooked.", " what do you think?",
                                              " it's been great.", " i want to get better at it."]))
    b = U(lambda: (ch(B_START_A) + " " + ch(B_START_B)).format(t=t))
    out.append([u, b])
    kinds = ["thing", "why", "tip", "more", "feel"]
    R.shuffle(kinds)
    for kd in kinds[:max(0, n - 1)]:
        x = ch(things)
        if kd == "thing":
            out.append([U(lambda: endp(ch(U_THING).format(x=x, t=t))), U(lambda: ch(B_THING).format(x=x, t=t))])
        elif kd == "why":
            out.append([U(lambda: ch(PREFIX_U[:6]) + ch(U_WHY).format(t=t)), U(lambda: ch(B_WHY).format(b=ben, t=t))])
        elif kd == "tip":
            out.append([U(lambda: ch(PREFIX_U[:6]) + ch(U_TIP).format(t=t)), U(lambda: ch(B_TIP).format(p=tip, t=t) + ch(["", " good luck with " + t + "!", " have fun with it."]))])
        elif kd == "more":
            out.append([U(lambda: ch(U_MORE).format(t=t)), U(lambda: ch(B_MORE).format(t=t, x=x))])
        else:
            out.append([U(lambda: endp(ch(U_FEEL).format(t=t))), U(lambda: ch(B_FEEL).format(t=t) + ch(["", " keep at it!", " you'll get there."]))])
    return out


def make_recall():
    nfacts = R.choice([1, 2, 2, 3, 3, 4])
    others = [k for k in FACTS if k != "name"]
    keys = (["name"] if R.random() < 0.8 else []) + R.sample(others, nfacts)
    keys = keys[:nfacts + 1]
    vals = {k: FACTS[k]["value"]() for k in keys}
    ex = []
    name = vals.get("name")
    if name and R.random() < 0.5:
        ex.append(req(ex_greet(name)))
        rest = [k for k in keys if k != "name"]
    else:
        if R.random() < 0.5:
            ex.append(ex_greet())
        rest = list(keys)
    R.shuffle(rest)
    stated = [k for k in keys if k not in rest]
    while rest:
        grp = rest[:R.choice([1, 1, 2])]
        rest = rest[len(grp):]
        ex.append(req(ex_state(grp, vals)))
        stated += grp
    # fillers then recalls
    fill_fns = [ex_persona, ex_small, ex_trivia]
    topic = ch(TOPICS)
    topic_ex = topic_exchanges(topic, R.randint(1, 3))
    fillers = topic_ex + [f() for f in R.sample(fill_fns, R.randint(0, 2))]
    asks = R.sample(stated, min(len(stated), R.choice([2, 2, 3, 3, 4])))
    for k in asks:
        n_f = R.choice([0, 1, 1, 2, 2, 3])
        ex.extend(fillers[:n_f])
        fillers = fillers[n_f:]
        extra = None
        if R.random() < 0.15:
            ok = [s for s in stated if s != k]
            if ok:
                e = ch(ok)
                extra = (e, vals[e])
        ex.append(ex_recall(k, vals[k], extra))
    if R.random() < 0.25:  # ask about something never stated
        unstated = [k for k in FACTS if k not in vals]
        k = ch(unstated)
        ex.append(ex_unknown(k, FACTS[k]["value"]()))
    if R.random() < 0.3:
        ex.append(ex_bye(name))
    return ex


def make_topic():
    topic = ch(TOPICS)
    ex = []
    name = None
    if R.random() < 0.5:
        name = pick_name()
        ex.append(req(ex_greet(name)))
    tx = topic_exchanges(topic, R.randint(3, 6))
    req(tx[0])
    ex += tx
    if R.random() < 0.6:
        ex.append([U(lambda: ch(PREFIX_U[:8]) + ch(U_WHAT)), U(lambda: ch(B_WHAT).format(t=topic[0]) + ch(["", "", " want to keep going?", " what else is on your mind?", " it was fun."]))])
    if name and R.random() < 0.5:
        ex.append(ex_recall("name", name))
    if R.random() < 0.3:
        ex.append(ex_bye(name))
    return ex


def make_honesty():
    ex = []
    if R.random() < 0.5:
        ex.append(ex_greet())
    fns = [ex_trivia, ex_trivia, ex_persona, ex_small]
    for _ in range(R.randint(2, 4)):
        ex.append(ch(fns)())
    # unknown personal fact, then user supplies it, then recall
    k = ch(list(FACTS))
    v = FACTS[k]["value"]()
    ex.append(ex_unknown(k, v))
    ex.append(req(ex_state([k], {k: v})))
    ex.append(ex_trivia() if R.random() < 0.5 else ex_persona())
    ex.append(ex_recall(k, v))
    return ex


def make_prefs():
    ex = []
    name = pick_name() if R.random() < 0.6 else None
    if name:
        ex.append(req(ex_greet(name)))
    food = ch(FOODS)
    music = ch(MUSIC)
    hobby = ch(TOPICS)
    ex.append(req(ex_state(["food"], {"food": food})))
    ex.append(req(ex_state(["music"], {"music": music})))
    ex.append(ex_small() if R.random() < 0.5 else ex_persona())
    sug = [
        (["what should i cook tonight?", "what should i eat for dinner?", "any idea what i should have for lunch?"],
         ["since you love {f}, why not make {f}?", "how about {f}? you said it's your favorite.", "you could have {f}, you told me you love it."], food),
        (["what should i listen to?", "can you suggest some music?", "what music should i put on?"],
         ["you said you like {f}, so maybe put on some {f}.", "how about some {f}? you mentioned you love it.", "try some {f}, since that's your favorite."], music),
    ]
    R.shuffle(sug)
    for qs, ans, val in sug:
        ex.append([U(lambda: ch(PREFIX_U[:8]) + ch(qs) + ch(["", " i can't decide.", " any ideas?", " help me out."])),
                   U(lambda: ch(ans).format(f=val) + ch(["", " enjoy!", " have fun!", " sounds good?"]))])
    if R.random() < 0.5:
        ex += topic_exchanges(hobby, 2)
    if name:
        ex.append(ex_recall("name", name))
    return ex


def make_correct():
    old, new = pick_name(), pick_name()
    while new == old:
        new = pick_name()
    ex = [req(ex_greet(old))]
    ex.append(req([U(lambda: ch(["actually, ", "sorry, ", "wait, ", "oops, "]) + ch(["my real name is {v}.", "my name is {v}, not " + old + ".", "call me {v} instead.", "i'm actually {v}."]).format(v=new)),
               U(lambda: ch(["no problem, {v}!", "got it, {v}.", "okay, i'll call you {v}.", "thanks for telling me, {v}."]).format(v=new) + ch(ACK_TAIL))]))
    ex += topic_exchanges(ch(TOPICS), R.randint(1, 3))
    ex.append(ex_recall("name", new))
    return ex


FAMILIES = [(make_recall, 0.62), (make_topic, 0.12), (make_honesty, 0.1), (make_prefs, 0.09), (make_correct, 0.07)]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/home/user/work/stage2_convs.jsonl"
    n_target = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
    convs, fails = [], 0
    fam_count = {}
    quota = {fn.__name__: int(w * n_target + 1) for fn, w in FAMILIES}
    while len(convs) < n_target and fails < n_target * 6:
        r = R.random()
        acc = 0
        for fn, w in FAMILIES:
            acc += w
            if r < acc:
                break
        if fam_count.get(fn.__name__, 0) >= quota[fn.__name__]:
            continue
        snapshot = set(SEEN)
        try:
            ex = fn()
        except Fail:
            ex = []
        ex = [e for e in ex if e is not None and e[0] is not None and e[1] is not None]
        ok = 4 <= len(ex) <= 10
        if not ok:
            SEEN.clear()
            SEEN.update(snapshot)
            fails += 1
            continue
        txt = " ".join(u + " " + b for u, b in ex)
        assert not any(v in txt for v in ["marisol", "dmitri", "quesadilla"]), txt
        fam_count[fn.__name__] = fam_count.get(fn.__name__, 0) + 1
        convs.append(ex)
    lines = [l for ex in convs for p in ex for l in p]
    assert len(lines) == len(set(lines)), "duplicate lines!"
    with open(out, "w") as f:
        for i, ex in enumerate(convs):
            split = "val" if i % 40 == 0 else "train"
            f.write(json.dumps({"src": "assistant_synth", "id": str(i), "split": split, "ex": ex}) + "\n")
    lens = [len(e) for e in convs]
    print("conversations %d (failed attempts %d), families %s" % (len(convs), fails, fam_count))
    print("exchanges per conv: min %d max %d mean %.2f; total lines %d, unique lines %d" %
          (min(lens), max(lens), sum(lens) / len(lens), len(lines), len(set(lines))))
    for ex in convs[:3]:
        for u, b in ex:
            print("  U:", u)
            print("  B:", b)
        print("  ---")


if __name__ == "__main__":
    main()
