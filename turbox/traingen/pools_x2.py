"""Fix pass 2: more TRAINING phrasings (memory, recall, tools, units, tool follow-ups, relations).
Same safeguards as pools_x: templates equal to a test template are dropped at load; 8-gram filter applies."""

RECALL_STATE_X = {
    "name": ["Hi, my name is {v}.", "Hey there, I'm {v}.", "{v} here!", "Hello! Call me {v}.", "My name's {v}.",
             "I'm called {v}.", "Just so you know, my name is {v}.", "btw I'm {v}", "People call me {v}.",
             "Nice to meet you, I'm {v}.", "Hello, {v} speaking.", "The name's {v}.", "Hi! I go by {v}.",
             "Please remember my name: {v}.", "You can just call me {v}, ok?"],
    "city": ["I'm based in {v}.", "I currently live in {v}.", "I grew up in {v}.", "Home for me is {v}.",
             "I'm writing from {v}.", "We live in {v}.", "I moved to {v} last year.", "I stay in {v}.",
             "Remember that I live in {v}."],
    "pet": ["My cat is called {v}.", "I have a dog named {v}.", "Our puppy's name is {v}.", "My hamster is {v}.",
            "I've got a parrot called {v}.", "My pet's name is {v}.", "We named our kitten {v}."],
    "food": ["My favourite meal is {v}.", "I could eat {v} every day.", "Nothing beats {v} for me.",
             "I'm a big fan of {v}.", "{v} is my favorite thing to eat.", "My go-to food is {v}."],
    "job": ["I work as a {v}.", "I'm a {v} by profession.", "My job is {v}.", "I'm employed as a {v}.",
            "For work I'm a {v}.", "I'm a {v}, by the way.", "I make a living as a {v}.", "My profession is {v}."],
    "color": ["My favourite colour is {v}.", "I love the color {v}.", "{v} is my favorite color.",
              "The colour I like most is {v}.", "My best color is {v}."],
}
RECALL_ASK_X = {
    "name": ["Who am I?", "Do you remember who I am?", "What did I say my name was?", "What am I called?",
             "Can you tell me my name?", "Remind me what my name is.", "You remember my name, right?",
             "What name did I give you?"],
    "city": ["Which city am I in?", "Where did I say I live?", "Do you remember where I live?", "What's my home town?",
             "Where am I based?"],
    "pet": ["What's my pet's name?", "What did I call my pet?", "Do you remember my pet's name?", "What is my cat called?"],
    "food": ["What's my favourite meal?", "Do you remember what food I like?", "What did I say I love eating?",
             "Which food do I like most?"],
    "job": ["What do I do for work?", "Remind me what my job is.", "What did I say my profession was?",
            "Do you remember what I do?", "What's my occupation?", "What do I work as?"],
    "color": ["What's my favourite colour?", "Do you remember my favorite color?", "Which color did I say I like?",
              "What colour do I like most?"],
}
FOODS = ["pizza", "ramen", "curry", "pancakes", "salad", "burritos", "falafel", "noodles", "pho", "risotto", "sushi",
         "tacos", "lasagna", "dumplings", "paella", "kebab", "pasta", "steak", "waffles", "soup", "chocolate", "rice",
         "biryani", "hummus", "gnocchi", "croissants", "bagels", "pad thai", "ice cream", "fried chicken", "cheesecake",
         "mango", "strawberries", "omelettes", "nachos", "spaghetti", "tofu", "porridge", "kimchi", "sandwiches"]
COLORS = ["blue", "red", "pink", "black", "gold", "silver", "white", "brown", "lime", "navy", "green", "yellow",
          "purple", "orange", "teal", "turquoise", "maroon", "violet", "grey", "beige", "crimson", "magenta", "cyan"]
PETS = ["Max", "Bella", "Coco", "Simba", "Daisy", "Milo", "Ginger", "Oreo", "Shadow", "Pickles", "Sunny", "Biscuit",
        "Luna", "Rocky", "Peanut", "Mochi", "Toby", "Nala", "Pepper", "Ziggy", "Buddy", "Cleo", "Bruno", "Kiwi"]

# unit surface names (training side)
UNIT_NAMES = {
    "mm": ["mm", "millimeters", "millimetres"], "cm": ["cm", "centimeters", "centimetres"],
    "m": ["m", "meters", "metres"], "km": ["km", "kilometers", "kilometres", "kms"],
    "in": ["inches", "in"], "ft": ["feet", "ft", "foot"], "yd": ["yards", "yd"], "mi": ["miles", "mi"],
    "g": ["grams", "g", "gr"], "kg": ["kg", "kilograms", "kilos"], "oz": ["ounces", "oz"],
    "lb": ["pounds", "lbs", "lb"], "st": ["stone"], "t": ["tonnes", "metric tons"],
    "ml": ["ml", "milliliters", "millilitres"], "l": ["liters", "litres", "l"], "gal": ["gallons", "gal"],
    "cup": ["cups"], "pt": ["pints"], "qt": ["quarts"], "tsp": ["teaspoons", "tsp"], "tbsp": ["tablespoons", "tbsp"],
    "kmh": ["km/h", "kph", "kilometers per hour"], "mph": ["mph", "miles per hour"],
    "m2": ["square meters"], "km2": ["square kilometers", "sq km"], "ft2": ["square feet", "sq ft"],
    "mi2": ["square miles", "sq mi"], "acre": ["acres"], "ha": ["hectares"],
    "sec": ["seconds", "secs"], "min": ["minutes", "mins"], "hr": ["hours", "hrs"], "day": ["days"],
    "week": ["weeks"], "year": ["years"],
    "kb": ["kilobytes", "kb"], "mb": ["megabytes", "mb"], "gb": ["gigabytes", "gb"], "tb": ["terabytes", "tb"],
    "byte": ["bytes"], "bit": ["bits"],
    "c": ["celsius", "degrees celsius"], "f": ["fahrenheit", "degrees fahrenheit"], "k": ["kelvin"],
}
CONVERT_Q = ["Convert {x} {u1} to {u2}.", "{x} {u1} in {u2}?", "How much is {x} {u1} in {u2}?",
             "How many {u2} is {x} {u1}?", "What's {x} {u1} in {u2}?", "{x} {u1} to {u2} please",
             "Change {x} {u1} into {u2}.", "{x} {u1} equals how many {u2}?", "Could you convert {x} {u1} into {u2}?",
             "I need {x} {u1} in {u2}.", "{x} {u1} = ? {u2}", "Turn {x} {u1} into {u2} for me.",
             "Express {x} {u1} in {u2}.", "What does {x} {u1} come to in {u2}?", "{u2} in {x} {u1}?"]

TOOL_X2 = {
    "count_letters": ["Count how many letters are in the word {w}.", "Number of letters in the word {w}?",
                      "The word {w} has how many letters?", "How many characters are in {w}?",
                      "Letter count for {w}?", "Tell me how many letters {w} has.", "{w}: how many letters?"],
    "count_letter": ["In the word {w}, how many {l}'s are there?", "How often does the letter {l} show up in {w}?",
                     "Count the letter {l} in the word {w}.", "Number of {l}s in {w}?", "How many {l}'s does {w} have?"],
    "reverse": ["Can you write {w} in reverse?", "Flip the word {w} around.", "What do you get if you reverse {w}?",
                "{w} reversed please", "Write the word {w} back to front."],
    "spell": ["Can you spell out {w}?", "Spell out the word {w} for me.", "What's the spelling of {w}?",
              "Please spell {w}.", "How would you spell {w}?", "I need the spelling of {w}."],
    "sort": ["Sort alphabetically: {list}", "Can you alphabetize {list}?", "Arrange these words A-Z: {list}",
             "List these in alphabetical order: {list}", "Put {list} in order", "Order alphabetically: {list}"],
    "calc_div": ["Can you divide {x} by {y}?", "What is {x} divided by {y}?", "Please divide {x} by {y}.",
                 "{x} split by {y}?", "How many times does {y} go into {x}?", "What's {x} / {y}?"],
    "calc_mul": ["Can you multiply {x} and {y}?", "Please multiply {x} by {y}.", "{x} multiplied by {y}?"],
    "calc_add": ["Can you add {x} and {y}?", "Please add {x} to {y}.", "{x} added to {y}?"],
    "calc_sub": ["Can you subtract {y} from {x}?", "Please take {y} from {x}.", "{x} minus {y} equals?"],
    "time": ["What time do you have?", "Can you tell me the time?", "Tell me what time it is.", "Clock check: what time is it?"],
    "date": ["Can you tell me the date?", "What date is it?", "Tell me today's date please."],
    "world_time": ["What is the time in {c} right now?", "Tell me the time in {c}.", "Local time in {c} please.",
                   "It's what time in {c} now?"],
    "weekday": ["Can you tell me what day {d} is?", "What day of the week does {d} fall on?", "{d} is which weekday?"],
    "leap": ["Is {yr} leap or not?", "Tell me if {yr} is a leap year.", "Can {yr} be a leap year?"],
    "prime": ["Can you check whether {x} is prime?", "Is {x} prime or composite?", "{x}: prime number or not?"],
    "roman": ["Can you write {x} in Roman numerals?", "{x} to Roman numerals please", "Roman numerals for {x}?"],
    "c_to_f": ["What is {x} C in F?", "{x} degrees celsius to fahrenheit?", "Turn {x} Celsius into Fahrenheit."],
}

# follow-ups that change one argument of the previous helper call (the context carries the call)
TOOL_FOLLOW = {
    "pct_of_p": ["And {p}%?", "What about {p} percent?", "Now do {p}%.", "And {p} percent of it?", "How about {p}%?"],
    "pct_of_x": ["And of {x}?", "What about {x}?", "Same percent of {x}?", "Now for {x}."],
    "tip_p": ["What about a {p}% tip?", "And at {p} percent?", "How about {p}%?"],
    "calc_y": ["And with {y}?", "What about {y}?", "Now with {y} instead.", "Same with {y}?"],
    "convert_x": ["And {x}?", "What about {x} {u1}?", "Now do {x}.", "How about {x} {u1}?"],
    "world_time_c": ["And in {c}?", "What about {c}?", "How about in {c}?", "And {c}?"],
}

REL_NOUN_X2 = {
    "alma_mater": ["education", "school", "college degree"],
    "artist": ["recording artist", "musician who made it"],
    "internet_domain": ["domain ending", "web suffix", "country domain"],
    "is_a": ["classification", "category it belongs to"],
    "occupation": ["work", "trade", "employment"],
    "founded_year": ["year of establishment", "founding date"],
    "release_year": ["year it came out"],
    "publication_year": ["year it came out", "year it was published"],
}
REL_Q_X2 = {
    "alma_mater": ["Where was {e} educated?", "What school did {e} attend?", "Where did {e} get their degree?",
                   "Which college did {e} graduate from?", "{e} studied where?"],
    "occupation": ["What was {e}'s job?", "What did {e} do for work?", "What line of work is {e} in?",
                   "What is {e}'s profession?", "{e} did what for a living?"],
    "artist": ["Who released {e}?", "Which band released {e}?", "Who made the album {e}?", "{e} is by which artist?"],
    "internet_domain": ["What's the internet suffix for {e}?", "Which web domain does {e} use?", "{e} domain ending?"],
    "release_year": ["When was {e} released?", "In what year did {e} come out?", "{e} release year?"],
    "founded_year": ["In what year was {e} set up?", "When did {e} start?", "Year {e} was founded?"],
    "definition": ["What does the word {e} mean?", "Meaning of {e}?", "Give me the definition of {e}."],
    "is_a": ["{e} belongs to what category?", "Is {e} a type of something? What?", "What broader type is {e}?"],
    "elevation": ["How high above sea level is {e}?", "{e} altitude?", "What's the altitude of {e}?"],
    "population": ["What's the population of {e}?", "How many inhabitants does {e} have?", "Population count for {e}?"],
    "nationality": ["What was {e}'s nationality?", "Which country was {e} a citizen of?"],
}

# unsupported-relation questions that resemble real relations were removed (job, height, films, death cause)
UNSUPPORTED_DROP = ["What was {e}'s first job?", "How tall was {e}?", "Which films did {e} appear in?",
                    "What was {e}'s cause of death?", "What is {e}'s net worth?"]
