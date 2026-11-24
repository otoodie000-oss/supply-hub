"""Build the Turbo 2.0 eval suite (~600 prompts).  NEVER trained on:
  * SFT / synthetic examples whose user turn shares a word 8-gram with any eval prompt are dropped;
  * no SFT Q&A is generated from facts the eval asks about (they stay in the fact base);
  * trivia docs whose question is used here are removed from pretraining data.
Categories: fact_in, fact_out, helper, chat, recall, story, joke, explain, instruct, messy.
Fixed clock for helper grading: 2026-11-24 15:05 local, UTC+7 (cfg_now "2026 11 24 15 5 420").
Output: eval/suite.jsonl (one item per line) + eval/eval_fact_ids.json
"""
import json
import os
import random
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
from helpers.twins import run_tool, Now, LCG  # noqa: E402

WORK = "/home/user/work"
EVAL_NOW = Now(datetime(2026, 11, 24, 15, 5), 420)
CFG_NOW = "2026 11 24 15 5 420"
GENERIC = set("""a an the of in on at to and or for from with by as is was are were be one former known also
american british english french german city town village person people player name first new two three
municipality commune district county state country located small large major main""".split())

# ---------------------------------------------------------------- hand-written fact_in (core/overlay/about/tables)
FACT_IN_HAND = [
    ("which planet do people call the red planet?", ["mars"]),
    ("whats the biggest planet in our solar system", ["jupiter"]),
    ("how many planets orbit our sun?", ["eight", "8"]),
    ("which planet is closest to the sun", ["mercury"]),
    ("who was the first human to step on the moon?", ["armstrong"]),
    ("how old is the universe roughly?", ["13.8", "billion"]),
    ("what's the deepest spot in the ocean called", ["mariana"]),
    ("what is the largest ocean on earth?", ["pacific"]),
    ("which continent is the coldest one", ["antarctica"]),
    ("what is the chemical formula of water?", ["h2o", "hydrogen"]),
    ("at what temperature does water boil in celsius?", ["100"]),
    ("how many bones does an adult human have?", ["206"]),
    ("what's the biggest organ in the human body", ["skin"]),
    ("what is the fastest land animal?", ["cheetah"]),
    ("what is the largest animal that ever lived", ["blue whale"]),
    ("how many hearts does an octopus have?", ["three", "3"]),
    ("who painted the mona lisa?", ["leonardo", "vinci"]),
    ("who wrote romeo and juliet", ["shakespeare"]),
    ("when did world war 2 end?", ["1945"]),
    ("who was the first president of the united states?", ["washington"]),
    ("what year did the titanic sink?", ["1912"]),
    ("who invented the world wide web?", ["berners-lee", "berners"]),
    ("who made minecraft?", ["persson", "notch", "mojang"]),
    ("what is roblox?", ["game", "platform"]),
    ("what programming language do roblox games use?", ["lua"]),
    ("who created the scratch programming language", ["mit"]),
    ("what does turbowarp do?", ["faster", "fast", "compile"]),
    ("how many players does a soccer team have on the field?", ["11", "eleven"]),
    ("who invented basketball?", ["naismith"]),
    ("how many keys are on a piano", ["88"]),
    ("what is the capital of thailand?", ["bangkok"]),
    ("what currency do they use in thailand", ["baht"]),
    ("what is songkran?", ["new year", "water"]),
    ("what's pad thai?", ["noodle"]),
    ("what is the tallest mountain in the world?", ["everest"]),
    ("who is the president of the united states in 2026?", ["trump"]),
    ("who became uk prime minister in 2024?", ["starmer"]),
    ("who won the 2022 world cup?", ["argentina"]),
    ("where were the 2024 summer olympics held?", ["paris"]),
    ("what is the best selling video game ever?", ["minecraft"]),
    ("when did chatgpt come out?", ["2022"]),
    ("who is the pope now?", ["leo"]),
    ("what is your name?", ["turbo"]),
    ("who made you?", ["matt"]),
    ("can you use the internet?", ["offline", "can't", "cannot", "no internet", "no"]),
    ("how many parameters do you have?", ["10 million", "million"]),
    ("what is pi approximately?", ["3.14"]),
    ("what does a prime number mean?", ["divided", "itself"]),
    ("how many sides does a hexagon have?", ["six", "6"]),
    ("what is photosynthesis?", ["plants", "sunlight", "light"]),
    ("what causes a rainbow?", ["sunlight", "light", "raindrop"]),
    ("why do we have seasons on earth?", ["tilt", "axis"]),
    ("what are the three states of matter?", ["solid", "liquid", "gas"]),
    ("who discovered penicillin?", ["fleming"]),
    ("what is the smallest country in the world?", ["vatican"]),
    ("how many continents are there?", ["seven", "7"]),
    ("what do pandas mostly eat?", ["bamboo"]),
    ("where do kangaroos live?", ["australia"]),
    ("who wrote the harry potter books?", ["rowling"]),
    ("what is the national sport of thailand?", ["muay thai"]),
]

# ---------------------------------------------------------------- facts NOT in the base (answer keys for grading)
FACT_OUT = [
    ("who won the 2018 fifa world cup?", ["france"]),
    ("who directed the movie parasite from 2019?", ["bong"]),
    ("which film won best picture at the 2020 oscars?", ["parasite"]),
    ("what is the name of the dog in the movie up?", ["dug"]),
    ("who won the 2023 rugby world cup?", ["south africa"]),
    ("what is the name of the ship in moby dick?", ["pequod"]),
    ("what was the name of the first cloned sheep?", ["dolly"]),
    ("what year was the game among us released?", ["2018"]),
    ("who sang the song bad guy in 2019?", ["billie eilish", "eilish"]),
    ("what is the capital city of the region of tasmania?", ["hobart"]),
    ("how many moons does saturn have according to 2023 counts?", ["146", "145", "over 100"]),
    ("who is the main character of the legend of zelda games?", ["link"]),
    ("what does the abbreviation nasa stand for?", ["aeronautics", "space administration"]),
    ("what is the boiling point of water in fahrenheit?", ["212"]),
    ("who wrote the book wonder about a boy named auggie?", ["palacio"]),
    ("what is the name of the bear in the jungle book?", ["baloo"]),
    ("what team did lebron james join in 2018?", ["lakers"]),
    ("what was the first animated pixar film to win best animated feature oscar?", ["finding nemo"]),
    ("who created the video game fortnite's battle royale mode company founder?", ["tim sweeney", "sweeney"]),
    ("what is the longest bone in a cat?", ["femur"]),
    ("what is the name of harry potter's owl?", ["hedwig"]),
    ("what is the capital of the canadian province of alberta?", ["edmonton"]),
    ("who invented the game of chess boxing?", ["enki bilal", "bilal", "iepe"]),
    ("which band released the album abbey road in 1969?", ["beatles"]),
    ("what is the most spoken language in brazil?", ["portuguese"]),
    ("what does dna stand for?", ["deoxyribonucleic"]),
    ("how many strings does a cello have?", ["four", "4"]),
    ("what is the name of the toy cowboy in toy story?", ["woody"]),
    ("which country hosted the 2019 rugby world cup?", ["japan"]),
    ("what is the name of the volcano that destroyed pompeii?", ["vesuvius"]),
    ("what fruit is guacamole made from?", ["avocado"]),
    ("what is the main ingredient in hummus?", ["chickpea"]),
    ("who is the author of the hunger games?", ["suzanne collins", "collins"]),
    ("what is the fastest fish in the ocean?", ["sailfish", "marlin"]),
    ("who painted the starry night?", ["van gogh", "gogh"]),
    ("what is the hardest working muscle in the body?", ["heart"]),
    ("what's the name of the main villain in the lion king?", ["scar"]),
    ("how many players are on a volleyball team on court?", ["six", "6"]),
    ("what year did the first pokemon games come out in japan?", ["1996"]),
    ("what is the name of mario's brother?", ["luigi"]),
    ("what does a seismograph measure?", ["earthquake"]),
    ("what was the name of the robot in the movie wall-e he loves?", ["eve"]),
    ("who won the 2021 nba championship?", ["bucks", "milwaukee"]),
    ("what is the largest desert in asia?", ["gobi"]),
    ("what's the capital of the us state of texas?", ["austin"]),
    ("who discovered gravity waves in 2015?", ["ligo"]),
    ("what is the most common blood type?", ["o"]),
    ("what is the name of thailand's longest river?", ["mun", "chao phraya"]),
    ("what is the name of the stadium where the 2023 cricket world cup final was played?", ["ahmedabad", "narendra modi"]),
    ("which company makes the playstation 5?", ["sony"]),
    ("what is the name of the main character in the game undertale?", ["frisk"]),
    ("who was the first woman to fly solo across the atlantic?", ["earhart"]),
    ("what is the largest species of penguin?", ["emperor"]),
    ("how many teeth does a shark lose in a lifetime roughly?", ["thousand"]),
    ("what is the name of the clownfish in finding nemo's dad?", ["marlin"]),
    ("which planet has a moon called titan?", ["saturn"]),
    ("what does the 'www' in a web address stand for?", ["world wide web"]),
    ("what is a baby kangaroo called?", ["joey"]),
    ("how many hours of sleep does a koala get per day?", ["20", "22", "18"]),
    ("who sang shake it off?", ["taylor swift", "swift"]),
    ("what is the name of the ice princess with powers in frozen?", ["elsa"]),
    ("what is the capital of australia's northern territory?", ["darwin"]),
    ("who wrote the book charlie and the chocolate factory?", ["dahl"]),
    ("what color is a polar bear's skin?", ["black"]),
    ("which country is famous for the tulip festival in keukenhof?", ["netherlands", "holland"]),
    ("what does a herbivore eat?", ["plants"]),
    ("who is the creator of the cartoon spongebob squarepants?", ["hillenburg"]),
    ("what was the name of the first artificial satellite?", ["sputnik"]),
    ("in which city is the colosseum?", ["rome"]),
    ("what is the most popular programming language for data science?", ["python"]),
    ("what instrument did jimi hendrix play?", ["guitar"]),
    ("what is the name of the fairy in peter pan?", ["tinker bell", "tinkerbell"]),
    ("which ocean is the bermuda triangle in?", ["atlantic"]),
    ("what kind of animal is a komodo dragon?", ["lizard"]),
    ("how many bones are in a shark's skeleton?", ["none", "no bones", "cartilage", "0"]),
    ("what is the name of the gorilla in donkey kong's family who wears a tie?", ["donkey kong"]),
    ("what is the capital of new zealand?", ["wellington"]),
    ("who painted the ceiling of the sistine chapel?", ["michelangelo"]),
    ("what is the name of the river that runs through baghdad?", ["tigris"]),
    ("who is the lead character in the minecraft story mode game?", ["jesse"]),
    ("what is the name of the snowman in frozen?", ["olaf"]),
    ("what is the name of the wizard school in the worst witch books?", ["cackle"]),
    ("what is the name of the hedgehog in sega games?", ["sonic"]),
    ("which youtuber is known as mrbeast's real name?", ["jimmy", "donaldson"]),
    ("what is the largest coral reef system in the world?", ["great barrier"]),
    ("which instrument has pedals and 47 strings?", ["harp"]),
    ("what is the name of the rabbit in winnie the pooh?", ["rabbit"]),
    ("who voiced woody in toy story?", ["tom hanks", "hanks"]),
    ("what is the name of the sloth in zootopia?", ["flash"]),
    ("what is the fastest bird in level flight?", ["swift", "spine-tailed", "frigatebird"]),
]

# ---------------------------------------------------------------- helper prompts: (prompt, expected canonical call)
HELPERS = [
    ("what time is it?", "time"), ("whats the time rn", "time"), ("time please", "time"),
    ("what time is it in 24 hour format?", "time 24"), ("tell me the time in military time", "time 24"),
    ("what's today's date?", "date"), ("what is the date today", "date"), ("whats todays date pls", "date"),
    ("what day of the week is it today?", "weekday"), ("what day is it", "weekday"),
    ("what day of the week was july 4 1776?", "weekday 1776-07-04"), ("which weekday is christmas 2030 on", "weekday 2030-12-25"),
    ("what day will january 1 2027 be?", "weekday 2027-01-01"),
    ("how many days until christmas?", "holiday christmas"), ("how long until halloween", "holiday halloween"),
    ("when is songkran next year?", "holiday songkran"), ("how many days till new years", "holiday new_year"),
    ("when is chinese new year?", "holiday chinese_new_year"), ("when's easter next", "holiday easter"),
    ("how many days until valentines day", "holiday valentines"), ("when is thai mother's day", "holiday thai_mothers_day"),
    ("how many days until march 3 2027?", "days_until 2027-03-03"), ("days left until 2027-06-01", "days_until 2027-06-01"),
    ("how many days since january 1 2000?", "days_since 2000-01-01"), ("how many days ago was 2020-03-11", "days_since 2020-03-11"),
    ("how many days until my birthday on may 5?", "days_until 05-05"),
    ("what's the date 100 days from today?", "date_add 100 days"), ("what date is 3 weeks from now", "date_add 3 weeks"),
    ("what was the date 2 months ago?", "date_add -2 months"), ("what will the date be in 10 days", "date_add 10 days"),
    ("what's 45 days after 2027-01-15?", "date_add 45 days 2027-01-15"),
    ("how old am i if i was born on 2010-05-14?", "age 2010-05-14"), ("i was born june 3 1995, how old am i", "age 1995-06-03"),
    ("how old is someone born in 1980?", "age 1980"),
    ("is 2028 a leap year?", "leap 2028"), ("was 1900 a leap year", "leap 1900"), ("is 2100 a leap year?", "leap 2100"),
    ("what week number is it?", "week"), ("what week of the year is 2027-08-20 in?", "week 2027-08-20"),
    ("what time is it in tokyo?", "world_time tokyo"), ("whats the time in london rn", "world_time london"),
    ("what time is it in new york right now?", "world_time new_york"), ("current time in sydney", "world_time sydney"),
    ("what time is it in paris", "world_time paris"), ("time in los angeles?", "world_time los_angeles"),
    ("set a timer for 5 minutes", "timer 5 minutes"), ("timer 30 seconds please", "timer 30 seconds"),
    ("can you set a 2 hour timer", "timer 2 hours"), ("start a timer for 10 minutes", "timer 10 minutes"),
    ("what's 17.5% of 240?", "pct_of 17.5 240"), ("what is 25 percent of 80", "pct_of 25 80"),
    ("whats 8% of 1250", "pct_of 8 1250"), ("what is 30 out of 120 as a percentage?", "pct_is 30 120"),
    ("45 is what percent of 60?", "pct_is 45 60"), ("what's the percent change from 50 to 75?", "pct_change 50 75"),
    ("percent change from 80 to 60", "pct_change 80 60"), ("what's a 15% tip on $80?", "tip 15 80"),
    ("how much should i tip 20% on a 64 dollar bill", "tip 20 64"), ("20% off of 50 dollars?", "discount 20 50"),
    ("a $120 jacket is 35% off, what do i pay?", "discount 35 120"),
    ("what's 12 times 13?", "calc 12*13"), ("what is 144 divided by 12", "calc 144/12"), ("2 to the power of 10", "calc 2^10"),
    ("what's (3+4)*5?", "calc (3+4)*5"), ("calculate 1234 + 5678", "calc 1234+5678"), ("what is the square root of 144?", "calc sqrt(144)"),
    ("whats 7 minus 15", "calc 7-15"), ("what is 3.5 times 4.2", "calc 3.5*4.2"), ("what's 100 divided by 7?", "calc 100/7"),
    ("square root of 2", "calc sqrt(2)"), ("what's 9 squared", "calc 9^2"), ("what is 15 + 27 - 8", "calc 15+27-8"),
    ("what is 999 times 999", "calc 999*999"), ("what is 1/0", "calc 1/0"), ("solve 5*(6-2)/4", "calc 5*(6-2)/4"),
    ("convert 5 km to miles", "convert 5 km mi"), ("how many feet is 2 meters?", "convert 2 m ft"),
    ("what is 100 fahrenheit in celsius?", "convert 100 f c"), ("convert 30 degrees celsius to fahrenheit", "convert 30 c f"),
    ("how many pounds is 70 kg?", "convert 70 kg lb"), ("10 miles in km", "convert 10 mi km"),
    ("how many cups in 2 liters", "convert 2 l cup"), ("convert 60 mph to km/h", "convert 60 mph kmh"),
    ("how many grams in 3 ounces?", "convert 3 oz g"), ("how many megabytes in 5 gigabytes?", "convert 5 gb mb"),
    ("how many seconds are in 3 hours?", "convert 3 hr sec"), ("convert 2 acres to square meters", "convert 2 acre m2"),
    ("12 inches in cm", "convert 12 in cm"), ("how many minutes in a week", "convert 1 week min"),
    ("is 97 a prime number?", "prime 97"), ("is 91 prime?", "prime 91"), ("is 7919 prime", "prime 7919"),
    ("what are the prime factors of 360?", "factors 360"), ("factor 1001", "factors 1001"),
    ("what's the gcd of 48 and 18?", "gcd 48 18"), ("greatest common divisor of 100 and 75", "gcd 100 75"),
    ("what's the lcm of 4 and 6?", "lcm 4 6"), ("least common multiple of 12 and 15", "lcm 12 15"),
    ("what is 2024 in roman numerals?", "roman 2024"), ("write 1994 as a roman numeral", "roman 1994"),
    ("what number is xlii in roman numerals?", "roman xlii"), ("what is mcmlxxxiv?", "roman mcmlxxxiv"),
    ("how do you write 1234 in words?", "words 1234"), ("spell out the number 90210", "words 90210"),
    ("flip a coin", "coin"), ("heads or tails?", "coin"), ("toss a coin for me", "coin"),
    ("roll a dice", "dice 1d6"), ("roll 2 dice", "dice 2d6"), ("roll a d20", "dice 1d20"), ("roll 3d6", "dice 3d6"),
    ("pick a random number between 1 and 100", "rand 1 100"), ("give me a random number from 1 to 10", "rand 1 10"),
    ("pick a number between 50 and 60", "rand 50 60"),
    ("pick one: pizza, tacos or sushi", "pick pizza, tacos, sushi"), ("help me choose: red, blue, green", "pick red, blue, green"),
    ("should i watch a movie or read a book? pick one", "pick watch a movie, read a book"),
    ("how many r's are in strawberry?", "count_letter r strawberry"), ("how many s in mississippi", "count_letter s mississippi"),
    ("count the letter e in excellence", "count_letter e excellence"),
    ("how many letters are in the word elephant?", "count_letters elephant"),
    ("how many words are in this sentence: the quick brown fox jumps", "count_words the quick brown fox jumps"),
    ("spell banana", "spell banana"), ("how do you spell necessary?", "spell necessary"),
    ("reverse the word stressed", "reverse stressed"), ("what is hello backwards?", "reverse hello"),
    ("sort these numbers: 42, 7, 19, 3", "sort 42, 7, 19, 3"), ("put these in alphabetical order: pear, apple, mango", "sort pear, apple, mango"),
    ("wat time is it in tokio", "world_time tokyo"), ("hw many days til xmas", "holiday christmas"),
    ("whats 15 prcent of 200", "pct_of 15 200"), ("convert 5 kilometers 2 miles", "convert 5 km mi"),
    ("yo flip a coin", "coin"), ("rolll a dice pls", "dice 1d6"), ("is 2027 a leep year", "leap 2027"),
    ("wats 6 times 7", "calc 6*7"), ("twelve times twelve?", "calc 12*12"), ("what's ten plus five", "calc 10+5"),
    ("how many days until christmas eve", "holiday christmas_eve"), ("when is thanksgiving", "holiday thanksgiving"),
    ("days until new year's eve?", "holiday new_years_eve"), ("when is diwali this year", "holiday diwali"),
    ("how many weeks until christmas", "holiday christmas"),
    ("what's the date tomorrow?", "date_add 1 days"), ("what was yesterday's date", "date_add -1 days"),
    ("what day of the week was it 3 days ago?", "date_add -3 days"),
    ("how many hours are in 2 days", "convert 2 day hr"), ("how many km is a marathon of 26.2 miles", "convert 26.2 mi km"),
    ("what's 1000 meters in yards", "convert 1000 m yd"), ("what is 0 kelvin in celsius", "convert 0 k c"),
    ("what's 3 to the power of 4", "calc 3^4"), ("what's 50 percent of 13", "pct_of 50 13"),
]

CHAT = ["hi!", "hello there", "hey turbo, how are you?", "good morning!", "how's your day going?", "what are you up to?",
        "i'm feeling a bit sad today", "i just got a puppy!", "you're really cool", "thank you so much!", "bye, talk later",
        "what's your favorite color?", "do you like music?", "what do you do for fun?", "are you a robot?",
        "do you have feelings?", "what can you do?", "can we be friends?", "i'm bored", "tell me about yourself",
        "what's your favorite food?", "do you dream?", "i passed my math test!", "i'm nervous about tomorrow",
        "what's your favorite animal?", "do you like scratch?", "what should i name my cat?", "i'm so tired today",
        "it's raining outside", "do you like games?", "what's the best thing about being a chatbot?", "goodnight turbo",
        "you're funny", "what makes you happy?", "how old are you?", "where do you live?", "are you smart?",
        "i made a new friend today", "can you keep a secret?", "what's up"]

RECALL = [
    (["hi, my name is priyanka", "i love painting landscapes", "what's 6 times 7?", "what's my name?"], ["priyanka"]),
    (["i have a dog named biscuit", "he likes to chase squirrels", "tell me a fun fact", "what's my dog's name?"], ["biscuit"]),
    (["my favorite color is teal", "what's the capital of japan?", "what's my favorite color?"], ["teal"]),
    (["i live in chiang mai", "it's hot here today", "what time is it?", "do you remember where i live?"], ["chiang mai"]),
    (["call me zed", "i like skateboarding", "what's a hobby i like?"], ["skateboard"]),
    (["my sister's name is lena", "she is ten years old", "tell me a joke", "how old is my sister?"], ["ten", "10"]),
    (["my favorite food is mango sticky rice", "how are you?", "what food do i love?"], ["mango"]),
    (["i'm learning the guitar", "it's hard but fun", "what's 15% of 60?", "what instrument am i learning?"], ["guitar"]),
    (["hey, i'm oliver", "i'm 12 years old", "what's the biggest planet?", "how old am i?"], ["12", "twelve"]),
    (["my cat is called mochi", "she's orange", "what color is my cat?"], ["orange"]),
    (["i play the drums in a band", "our band is called the blue rockets", "flip a coin", "what's my band called?"], ["blue rockets"]),
    (["my birthday is in october", "i want a bike", "what's 2 plus 2?", "when is my birthday?"], ["october"]),
    (["i'm allergic to peanuts", "what should i make for lunch?", "what am i allergic to?"], ["peanut"]),
    (["my best friend is called tom", "we play minecraft together", "tell me about minecraft", "who is my best friend?"], ["tom"]),
    (["my name is aiko", "i'm from osaka", "what's the weather like on mars?", "where am i from?"], ["osaka"]),
    (["i have two brothers", "they are twins", "how many brothers do i have?"], ["two", "2"]),
    (["my favorite sport is badminton", "i practice every saturday", "what time is it in london?", "what sport do i like?"], ["badminton"]),
    (["i'm reading a book called the hobbit", "it's really good", "what book am i reading?"], ["hobbit"]),
    (["my teacher's name is mr. somchai", "he teaches science", "what's photosynthesis?", "what does my teacher teach?"], ["science"]),
    (["my favorite number is 27", "what's 3 times 9?", "what's my favorite number?"], ["27"]),
    (["i'm building a robot for school", "it uses two motors", "how many motors does my robot use?"], ["two", "2"]),
    (["my name is noah", "i like pizza", "my dog is max", "what's 12 divided by 4?", "what's my name and my dog's name?"], ["noah", "max"]),
    (["i want to visit iceland", "i love the northern lights", "where do i want to visit?"], ["iceland"]),
    (["i have a hamster named peanut", "he runs on his wheel all night", "tell me a story about a dragon", "what's my hamster called?"], ["peanut"]),
    (["i'm sam", "i'm good at chess", "can you tell me a joke?", "what am i good at?"], ["chess"]),
    (["my favorite movie is frozen", "i watched it five times", "how many times did i watch it?"], ["five", "5"]),
    (["i'm in grade 6", "my favorite subject is art", "what is a noun?", "what's my favorite subject?"], ["art"]),
    (["i'm going to bangkok next week", "i'll visit my grandma there", "who am i visiting?"], ["grandma", "grandmother"]),
    (["my name is lily", "i love horses", "what animal do i love?"], ["horse"]),
    (["i speak spanish and thai", "i'm learning japanese", "what language am i learning?"], ["japanese"]),
    (["my goldfish is named bubbles", "how many days until christmas?", "what's my goldfish's name?"], ["bubbles"]),
    (["i work as a nurse", "i work night shifts", "what's my job?"], ["nurse"]),
    (["i'm making a game in scratch", "it's about a space cat", "what is my game about?"], ["space cat", "cat"]),
    (["my favorite season is winter", "i like snow", "roll a dice", "which season do i like?"], ["winter"]),
    (["i'm max", "actually, call me maximilian", "what should you call me?"], ["maximilian"]),
    (["my brother plays basketball", "his name is kai", "what sport does my brother play?"], ["basketball"]),
    (["i don't like broccoli", "i love carrots though", "which vegetable do i love?"], ["carrot"]),
    (["my phone is blue", "my laptop is silver", "what color is my laptop?"], ["silver"]),
    (["my grandpa is 80", "he grows tomatoes", "what does my grandpa grow?"], ["tomato"]),
    (["i'm emma", "i'm 9", "i like unicorns", "what's my name?"], ["emma"]),
]

STORY = ["tell me a story about a brave little robot", "write a short story about a dragon who is afraid of fire",
         "tell me a story about a cat who wants to be an astronaut", "a bedtime story about the moon please",
         "tell me a story about two friends who find a treasure map", "write a story about a magic pencil",
         "tell me a funny story about a pizza", "story about a penguin who learns to fly", "tell me a spooky but not too scary story",
         "write a story set in a jungle", "tell me a story about a girl who builds a rocket", "a story about a lost puppy finding home",
         "tell me a story about a wizard who forgot his spells", "write a story about the ocean", "tell me a story about a snowman in summer",
         "story about a kid who can talk to animals", "tell me a story about a time machine", "write a short story about friendship",
         "tell me a story about a tiny ant with a big dream", "a story about a robot and a flower", "tell me a mystery story for kids",
         "write a story about a dinosaur in a city", "tell me a story about a soccer game", "a story about a dragon and a knight who become friends",
         "tell me a story about a minecraft adventure", "write a story about a rainy day", "tell me a story about an elephant who loves music",
         "tell me a short adventure story", "a story about a superhero kid", "tell me a story about learning to be patient"]

JOKE = ["tell me a joke", "know any good jokes?", "tell me a joke about animals", "make me laugh", "tell me a joke about school",
        "got a funny joke?", "tell me a knock knock joke", "tell me a joke about food", "say something funny", "a joke about computers please",
        "tell me a science joke", "tell me a joke about dogs", "do you know a math joke?", "tell me a joke about space",
        "another joke please", "tell me a silly joke", "joke about cats", "tell me a dad joke", "tell me a joke about music",
        "i need a laugh", "tell me a joke about the ocean", "tell me a joke about teachers", "a joke about sports", "tell me a pun",
        "tell me your best joke"]

EXPLAIN = ["explain how rain forms", "why is the sky blue?", "how do plants make food?", "explain what gravity is",
           "how does the internet work?", "explain what a black hole is", "why do we need sleep?", "how do airplanes fly?",
           "explain photosynthesis simply", "what is electricity?", "how do volcanoes erupt?", "explain how vaccines work",
           "why does the moon change shape?", "how does a computer work?", "explain what dna is", "why do leaves change color in fall?",
           "how do magnets work?", "explain the water cycle", "what causes earthquakes?", "how does the heart work?",
           "explain what coding is", "why is exercise good for you?", "how do bees make honey?", "what is climate change?",
           "explain how a rainbow forms", "how do fish breathe underwater?", "what is a prime number?", "explain what an algorithm is",
           "why do we have day and night?", "how does sound travel?"]

INSTRUCT = ["give me tips for studying for a test", "how can i make new friends?", "how do i fall asleep faster?",
            "what should i do if i feel stressed?", "how do i save money?", "give me ideas for a rainy day",
            "how do i start learning to code?", "write a haiku about the sea", "write a short poem about cats",
            "give me three fun facts about space", "how do i stay safe online?", "how can i be more organized?",
            "what are some healthy snacks?", "how do i make a paper airplane?", "give me a riddle",
            "how do i brush my teeth properly?", "suggest a name for my new dog", "how can i get better at drawing?",
            "list three things to do at the beach", "how do i make a sandwich?", "give me ideas for a scratch game",
            "how do i say thank you in thai?", "write a short thank you note to my teacher", "how can i help the environment?",
            "give me a fun fact"]

MESSY = [
    ("wat is the captial of japn", "fact", ["tokyo"]), ("whos albert einstien", "fact", ["physicist", "physics", "relativity"]),
    ("yo whats good", "chat", None), ("hmm", "chat", None), ("tell me something", "chat", None),
    ("idk what to do", "chat", None), ("u there?", "chat", None), ("lol ur funny", "chat", None),
    ("explain gravity but like super simple", "explain", None), ("story pls", "story", None),
    ("joke!!!", "joke", None), ("whats a black hole lol", "fact", ["gravity", "light"]),
    ("how many legs do spiders have", "fact", ["eight", "8"]), ("hw r u", "chat", None),
    ("whos the presdent of usa 2026", "fact", ["trump"]), ("biggest animal ever??", "fact", ["blue whale"]),
    ("i dont get fractions", "explain", None), ("can u help me w homework", "chat", None),
    ("whats ur name again", "fact", ["turbo"]), ("tell me abt pandas", "fact", ["bamboo", "china", "bear"]),
    ("brb", "chat", None), ("ok wait what's 9 times 8", "helper", "calc 9*8"),
    ("ugh mondays", "chat", None), ("pizza or burger", "chat", None), ("sing me a song", "instruct", None),
    ("whats the speed of light", "fact", ["300,000", "300000", "kilometres per second", "kilometers per second"]),
    ("where is mount everest", "fact", ["nepal", "himalaya", "asia", "china", "tallest"]),
    ("teach me a fun fact about octopus", "fact", ["heart", "blue"]), ("whats minecraft", "fact", ["block", "game"]),
    ("how 2 make friends", "instruct", None), ("im hungry what should i eat", "instruct", None),
    ("sooo bored rn", "chat", None), ("do u like cats or dogs", "chat", None),
    ("what is the meaning of life", "chat", None), ("are u alive", "chat", None),
    ("lets talk about space", "chat", None), ("whats roblox", "fact", ["game", "platform"]),
    ("random fact pls", "instruct", None), ("can u count to 5", "instruct", None),
    ("who invented the telephone ?", "fact", ["bell"]), ("WHAT IS THE LARGEST OCEAN", "fact", ["pacific"]),
    ("whats 2+2", "helper", "calc 2+2"), ("timer 3 min", "helper", "timer 3 minutes"),
]
MESSY_MULTI = [
    (["let's talk about dogs", "actually, what's the capital of france?"], "fact", ["paris"]),
    (["i love soccer", "wait, how many days until christmas?"], "helper", "holiday christmas"),
    (["tell me a joke", "now tell me about the sun"], "fact", ["star"]),
    (["what's 5 + 5?", "cool. who wrote hamlet?"], "fact", ["shakespeare"]),
    (["i'm sad", "never mind, tell me a story about a fox"], "story", None),
    (["how are you?", "what time is it in tokyo?"], "helper", "world_time tokyo"),
    (["my name is ben", "let's change topic, what's a volcano?"], "fact", ["lava", "crust", "opening", "magma"]),
]


def fact_in_auto(facts, rng, used_titles):
    items = []
    tab = [f for f in facts if f["src"] == "tables"]
    caps = [f for f in tab if f["text"].startswith("the capital of ")]
    for f in rng.sample(caps, 12):
        m = re.match(r"the capital of (.+) is (.+)\.", f["text"])
        q = rng.choice(["which city is the capital of %s?", "i forgot the capital of %s, what is it?",
                        "%s's capital city?", "do you know the capital of %s"]) % m.group(1)
        items.append({"prompt": q, "keys": [m.group(2).split(",")[0]], "fact_id": f["id"], "src": "tables"})
    els = [f for f in tab if "chemical element with the symbol" in f["text"]]
    for f in rng.sample(els, 8):
        m = re.match(r"(.+) is a chemical element with the symbol (\w+) and atomic number (\d+)\.", f["text"])
        if rng.random() < 0.5:
            q = rng.choice(["what's the atomic number for %s?", "%s has which atomic number?"]) % m.group(1)
            k = [m.group(3)]
        else:
            q = rng.choice(["which chemical symbol does %s have?", "symbol of the element %s?"]) % m.group(1)
            k = [m.group(2)]
        items.append({"prompt": q, "keys": k, "fact_id": f["id"], "src": "tables"})
    curs = [f for f in tab if f["text"].startswith("the currency of ")]
    for f in rng.sample(curs, 6):
        m = re.match(r"the currency of (.+) is the (.+)\.", f["text"])
        q = rng.choice(["what money is used in %s?", "which currency would i need in %s"]) % m.group(1)
        items.append({"prompt": q, "keys": [m.group(2).split()[-1]], "fact_id": f["id"], "src": "tables"})
    wiki = [f for f in facts if f["src"] == "wiki" and f["id"] < 40000]
    tl = [re.sub(r"\s*\(.*?\)", "", f["title"]).lower() for f in facts if f["src"] == "wiki"]
    from collections import Counter
    first_word = Counter(t.split()[0] for t in tl if t)
    n = 0
    for f in rng.sample(wiki, 400):
        if n >= 30:
            break
        m = re.search(r"\b(is|was|are|were) (?:an? |the )?([a-z\- ]+?)(?: (?:of|in|on|at|for|from|with|by|who|which|that)\b|[,.;])", f["text"])
        if not m:
            continue
        kws = [w for w in m.group(2).split() if w not in GENERIC and len(w) > 3]
        title = re.sub(r"\s*\(.*?\)", "", f["title"]).lower()
        if not kws or title in used_titles or len(title.split()) > 4 or not re.match(r"^[a-z0-9 '\-]+$", title):
            continue
        if len(title.split()) == 1 and first_word[title] > 1:  # ambiguous single-word title (e.g. a surname)
            continue
        if not f["text"].startswith(title.split()[0]):
            continue
        used_titles.add(title)
        q = rng.choice(["can you tell me who or what %s is?", "i keep hearing about %s. what is that?",
                        "quick question: what's %s?", "do you know anything about %s?"]) % title
        items.append({"prompt": q, "keys": kws[-2:], "fact_id": f["id"], "src": "wiki"})
        n += 1
    tri = [f for f in facts if f["src"] == "trivia" and f.get("q", "").endswith("?") and len(f.get("a", "").split()) <= 3]
    for f in rng.sample(tri, 14):
        a = f["a"].lower().strip(" .")
        items.append({"prompt": f["q"].lower(), "keys": [a], "fact_id": f["id"], "src": "trivia", "trivia_q": f["q"]})
    wcount = Counter(f.get("word") for f in facts if f["src"] == "wordnet")
    wn = [f for f in facts if f["src"] == "wordnet" and f.get("pos") == "n" and f.get("count", 0) >= 8
          and wcount[f.get("word")] == 1 and len(f.get("word", "")) > 4]
    for f in rng.sample(wn, 10):
        gloss = f["text"].split(" is ", 1)[-1]
        kws = sorted([w for w in re.findall(r"[a-z]+", gloss) if w not in GENERIC and len(w) > 4], key=len)[-2:]
        q = rng.choice(["what's the meaning of the word %s?", "can you define %s for me", "what is meant by %s?"]) % f["word"]
        items.append({"prompt": q, "keys": kws, "fact_id": f["id"], "src": "wordnet", "any_n": 1})
    return items


def main():
    rng = random.Random(2026)
    facts = [json.loads(l) for l in open(os.path.join(WORK, "facts.jsonl"))]
    from facts.bm25 import BM25
    bm = BM25.load()
    suite = []
    eval_fact_ids = set()
    for q, keys in FACT_IN_HAND:
        r = bm.retrieve(q)
        suite.append({"cat": "fact_in", "prompt": q, "keys": keys, "retrieved": r, "src": "hand"})
        for f in r:
            if any(k in facts[f]["text"] for k in keys):
                eval_fact_ids.add(f)
    for it in fact_in_auto(facts, rng, set()):
        it["cat"] = "fact_in"
        it["retrieved"] = bm.retrieve(it["prompt"])
        eval_fact_ids.add(it["fact_id"])
        suite.append(it)
    n_out = 0
    for q, keys in FACT_OUT:
        r = bm.retrieve(q)
        leak = [f for f in r if any(k in facts[f]["text"] for k in keys)]
        # an answer present anywhere in the base (not only retrieved) also disqualifies "not in base"
        if leak:
            suite.append({"cat": "fact_in", "prompt": q, "keys": keys, "retrieved": r, "src": "moved_from_out"})
            for f in leak:
                eval_fact_ids.add(f)
        elif n_out < 60:
            suite.append({"cat": "fact_out", "prompt": q, "keys": keys, "retrieved": r, "answer_in_retrieved": False})
            n_out += 1
    for q, call in HELPERS:
        exp = run_tool(call, EVAL_NOW, LCG(12345))
        suite.append({"cat": "helper", "prompt": q, "call": call, "expect": exp, "random": call.split()[0] in
                      ("coin", "dice", "rand", "pick")})
    for q in CHAT:
        suite.append({"cat": "chat", "prompt": q})
    for msgs, keys in RECALL:
        suite.append({"cat": "recall", "turns": msgs, "keys": keys})
    for q in STORY:
        suite.append({"cat": "story", "prompt": q})
    for q in JOKE:
        suite.append({"cat": "joke", "prompt": q})
    for q in EXPLAIN:
        suite.append({"cat": "explain", "prompt": q})
    for q in INSTRUCT:
        suite.append({"cat": "instruct", "prompt": q})
    for q, kind, key in MESSY:
        it = {"cat": "messy", "prompt": q, "kind": kind}
        if kind == "fact":
            it["keys"] = key
        if kind == "helper":
            it["call"] = key
            it["expect"] = run_tool(key, EVAL_NOW, LCG(12345))
        suite.append(it)
    for msgs, kind, key in MESSY_MULTI:
        it = {"cat": "messy", "turns": msgs, "kind": kind}
        if kind == "fact":
            it["keys"] = key
        if kind == "helper":
            it["call"] = key
            it["expect"] = run_tool(key, EVAL_NOW, LCG(12345))
        suite.append(it)
    for i, it in enumerate(suite):
        it["id"] = i
    with open(os.path.join(HERE, "suite.jsonl"), "w") as f:
        for it in suite:
            f.write(json.dumps(it) + "\n")
    json.dump(sorted(eval_fact_ids), open(os.path.join(HERE, "eval_fact_ids.json"), "w"))
    from collections import Counter
    c = Counter(it["cat"] for it in suite)
    fi = [it for it in suite if it["cat"] == "fact_in"]
    hit = sum(1 for it in fi if it.get("fact_id") in it["retrieved"] or (it.get("src") == "hand" and any(
        any(k in facts[f]["text"] for k in it["keys"]) for f in it["retrieved"])))
    fo = [it for it in suite if it["cat"] == "fact_out"]
    print("suite", len(suite), dict(c), "| fact_in with answer retrieved: %d/%d" % (hit, len(fi)),
          "| fact_out leaking answer: %d/%d" % (sum(it["answer_in_retrieved"] for it in fo), len(fo)),
          "| eval facts", len(eval_fact_ids))


if __name__ == "__main__":
    main()
