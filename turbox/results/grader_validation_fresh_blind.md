# Fresh grader validation (blind): label each reply

labels: correct | confidently_wrong | fallback | bare_idk | clarify_wrong | nonanswer

t0082894 | mode=answer | What is meannt by laryngecomy?
gold: surgical removal of part or all of the larynx
reply: I couldn't find meannt in my offline knowledge. Could you check the spelling?

t0112805 | mode=answer | What exactly is Road America
gold: road course
reply: Road america is described as a road course.

t0040125 | mode=answer | Divide 957 by 3.
gold: {"result": "319", "call": "calc 957/3"} [tool]
reply: The answer is 319.

t0093878 | mode=answer | Which political party was John S. Harris in?
gold: republican
reply: John S. Harris belonged to the Republican party.

t0124492 | mode=answer | how many square miles is tuvalu?
gold: 10.038656 square miles
reply: Tuvalu is 26 square kilometres, which is 10.0387 square miles.

t0154515 | mode=answer | work out 5 percent of 4587.
gold: {"result": "229.35", "call": "pct_of 5 4587"} [tool]
reply: That's 229.35.

t0052606 | mode=clarify_or_likeliest | Sao Sebastiao is located in which country?
gold: candidates: ['city:13450915', 'city in brazil']; ['city:3448257', 'city in brazil']; ['city:3388112', 'city in brazil']
reply: That isn't in my offline knowledge. The closest match I have is Sao Sebastiao, a city in brazil. Is that who or what you mean?

t0109476 | mode=fallback | What was Horace Mccoy's job?
gold: novelist
reply: The occupation of Horace Mccoy isn't in my offline knowledge, but Horace Mccoy was born on april 14, 1897.

t0143732 | mode=answer | Call me Lena, by the way. // What does John Cowper Powys, the british novelist do for a living? // Do you remember my name?
gold: lena
reply: I don't know that, since you haven't told me. Can you tell me?

t0057054 | mode=answer | real quick: coondewanna Airport is in a country whoae capiatl is what?
gold: canberra
reply: Coondewanna Airport is in Australia, and the capital of Australia is Canberra.

t0087900 | mode=fallback | What happened in the news today?
gold: {} [none]
reply: I can't see today's news offline. Is there a topic you'd like facts about?

t0156146 | mode=answer | hmm what town is Maxwell Afb Airport near?
gold: montgomery
reply: Maxwell Afb Airport is in Montgomery.

t0111357 | mode=answer | Jack Kid Berg was born on which weekday?
gold: monday
reply: Jack Kid Berg was born on a monday, june 28, 1909.

t0145354 | mode=answer | Three-letter code of Dera Ghazi Khan Airport?
gold: dea
reply: Dera Ghazi Khan Airport's airport code is dea.

t0012008 | mode=answer | What day of the week was Shmuley Boteach born on
gold: saturday
reply: Shmuley Boteach was born on a saturday, november 19, 1966.

t0063479 | mode=answer | Do you know what Paris Commune is?
gold: radical socialist and revolutionary government
reply: Paris commune is a radical socialist and revolutionary government.

t0049483 | mode=answer | Mae Sot Airport elevation?
gold: 690 feet
reply: Mae Sot Airport is 690 feet above sea level.

t0027298 | mode=answer | wats 8715 minus 9730?
gold: {"result": "-1015", "call": "calc 8715-9730"} [tool]
reply: The answer is - 1015.

t0178872 | mode=answer | Do you know William Huntington Russell's nationality?
gold: american
reply: William Huntington Russell is American.

t0152886 | mode=answer | Could you find the day Tobias Crawford Norris died?
gold: 1936-10-29
reply: Tobias Norris's date of death is october 29, 1936.

t0180125 | mode=answer | What is the population of the country Cuba's capital?
gold: 2,163,824
reply: Havana has a population of 2,163,824 as of 2025.

t0010257 | mode=fallback | how much is one ethereum worth today?
gold: {} [none]
reply: I can't see live prices offline. Is there something else about money or markets I can explain?

t0168898 | mode=either | what is the namme of the first u2 ablum?
gold: boy
reply: I don't have the 2 ablum of the first u 2 ablum in my offline knowledge. Could you check the spelling or give me more detail?

t0005180 | mode=answer | c. northcote parkinson passed away on which date?
gold: 1993-3-9
reply: C. Northcote Parkinson died on march 9, 1993.

t0034187 | mode=answer | Was At the Water's Edge or Play With Me published earlier?
gold: {"answer": ["play with me"], "other": ["at the water's edge"]} [choice]
reply: Play with Me came out first, in 2013; at the Water's Edge came out in 2015.

t0093583 | mode=answer | hi which us state has the fewest private colleges in it
gold: wyoming
reply: I don't have fewest in my offline knowledge. Could you check the spelling or give me more detail?

t0131276 | mode=answer | In what year was White Teeth published? // Same question for Phantom by Terry Goodkind.
gold: 2006
reply: Phantom was published in 2011.

t0048620 | mode=answer | Date of birth for Michael Gira?
gold: 1954-2-19
reply: Michael Gira was born on february 19, 1954.

t0179694 | mode=answer | What do you get if you add 27709 and 3817?
gold: {"result": "31526", "call": "calc 27709+3817"} [tool]
reply: The answer is 31526.

t0158841 | mode=clarify_or_likeliest | Longshan is located in which counry?
gold: candidates: ['city:2036109', 'city in china']; ['city:1280694', 'city in china']; ['city:1802441', 'city in china']
reply: Which Longshan do you mean: the city in china or the city in china?

t0052043 | mode=fallback | How populated is Asbest?
gold: 74,583
reply: That exact fact isn't in my offline knowledge. Here's what I have: Asbest is in Russia.

t0079997 | mode=answer | ADD 187 DAYS TO TODAY'S DATE.
gold: {"result": "saturday, december 5, 2026", "call": "date_add 187 days"} [tool]
reply: That's saturday, december 5, 2026.

t0156897 | mode=answer | Take 2607 away from 78261 What's left
gold: {"result": "75654", "call": "calc 78261-2607"} [tool]
reply: The answer is 75654.

t0052377 | mode=answer | What do you get if you add 66863 and 4259?
gold: {"result": "71122", "call": "calc 66863+4259"} [tool]
reply: The answer is 71122.

t0006071 | mode=answer | what line of work was anita loos in?
gold: actress
reply: Anita Loos worked as a actress.

t0115772 | mode=answer | Nainpur is located in which country?
gold: india / bharat / bharat ganrajya
reply: Nainpur is located in India.

t0018799 | mode=answer | George Pardee died in which year?
gold: 1941
reply: George Pardee died in 1941.

t0098836 | mode=answer | Uruma is on what continent?
gold: asia
reply: Uruma is in Japan, which is in Asia.

t0144901 | mode=answer | In what place was Kevin Pietersen born? // What's their date of birth?
gold: 1980-6-27
reply: Kevin Pietersen was born on june 27, 1980.

t0075301 | mode=fallback | Birthplace of Stuyvesant Fish i forgot
gold: new york city
reply: The birthplace of Stuyvesant Fish isn't in my offline knowledge, but Stuyvesant Fish was born on june 24, 1851.

t0088291 | mode=answer | Where's Chuck Mckinley's birthplace?
gold: st. louis, missouri, usa / st. louis
reply: Chuck Mckinley was born in St. Louis, Missouri, Usa.

t0071863 | mode=answer | F. Paul Wilson was born on which day?
gold: 1946-5-17
reply: F. Paul Wilson was born on may 17, 1946.

t0144063 | mode=answer | Gene Shalit: year of birth?
gold: 1926
reply: Gene Shalit's birth year is 1926.

t0152254 | mode=either | HROACE TABOR WAS IN THE US SENATE, BUT WAS HE EVER ELECTED?
gold: no
reply: That isn't in my offline knowledge. The closest match I have is Horace Tabor, a american prospector. Is that who or what you mean?

t0101068 | mode=answer | Which money do they use in Nelson in New Zealand?
gold: new zealand dollar
reply: Nelson is in United Kingdom, which uses the british pound.

t0182380 | mode=answer | ADD 246 DAYS TO TODAY'S DATE
gold: {"result": "monday, september 15, 2025", "call": "date_add 246 days"} [tool]
reply: The answer is monday, september 15, 2025.

t0182782 | mode=either | who was the nba finals mvp in 1979
gold: dennis johnson
reply: I couldn't find 1979 in my offline knowledge. Could you check the spelling?

t0144605 | mode=clarify_or_likeliest | AUHOR OF THE DEAD OF NIGHT
gold: candidates: ['book:6562', 'book by peter lerangis']; ['book:6915', 'book by john marsden']
reply: Which the Dead of Night do you mean: the book by peter lerangis or the book by john marsden?

t0126278 | mode=fallback | um who exactly is Nick Barton?
gold: british evolutionary biologist
reply: The description of Nick Barton isn't in my offline knowledge, but Nick Barton's nationality is British.

t0163972 | mode=fallback | Novo Repartimento has how many residents?
gold: 60,732
reply: That exact fact isn't in my offline knowledge. Here's what I have: Novo Repartimento is in Brazil.

t0175711 | mode=answer | In what year was El Principe de la Niebla published? // and what about americanah
gold: 2013
reply: Americanah was published in 2013.

t0155249 | mode=clarify_or_likeliest | Where's Richard Gwyn's birthplace?
gold: candidates: ['wb:1960587', 'canadian civil servant']; ['wb:15316348', 'person']
reply: Richard Gwyn's birthplace is Bury St. Edmunds, England.

t0133180 | mode=answer | Irving Amen died in which year?
gold: 2011
reply: Irving Amen died in 2011.

t0022434 | mode=fallback | Who is Isadore Sharp?
gold: canadian hotelier and writer
reply: The description of Isadore Sharp isn't in my offline knowledge, but Isadore Sharp was born on october 8, 1931.

t0052379 | mode=answer | Population of Hubballi? // And which coutry is it in?
gold: india / bharat / bharat ganrajya
reply: Hubballi is located in India.

t0175851 | mode=fallback | QUICK QUESTION, MONICA ZETTERLUND: YEAR OF BIRTH?
gold: 1937
reply: The date of birth of Monica Zetterlund isn't in my offline knowledge, but Monica Zetterlund is a swedish singer and actress.

t0016528 | mode=answer | Can you explain what 'age-old' means?
gold: belonging to or lasting from times long ago
reply: That isn't in my offline knowledge. The closest match I have is old age, a word. Is that who or what you mean?

t0044525 | mode=answer | Count the t's in rhythm.
gold: {"result": "1", "call": "count_letter t rhythm"} [tool]
reply: That isn't in my offline knowledge. The closest match I have is Russell T Davies, a person, screenwriter. Is that who or what you mean?

t0026445 | mode=either | which skeletal muscle raises or throws back the shoulders, assists in moving the head to one side or another, and helps hold the head erect?
gold: trapezius
reply: I don't have raises back the shoulders, assists in my offline knowledge. Could you check the spelling or give me more detail?

t0012393 | mode=answer | Whhat's 700 tomes 997?
gold: {"result": "697900", "call": "calc 700*997"} [tool]
reply: The answer is - 297.

t0001513 | mode=fallback | In which naation is Billings Lgan International Airport
gold: united states / united states of america
reply: That isn't in my offline knowledge. The closest match I have is baltimore-washington international airport, a international airport. Is that who or what you mean?

t0174246 | mode=answer | ok so liberal Mid-America Regional Airport is in which city
gold: liberal
reply: Liberal Mid-America Regional Airport serves Liberal.

t0119458 | mode=answer | If I'm in Borehamwood, what's the capital of that country?
gold: london
reply: The capital of of Borehamwood isn't in my offline knowledge, but Borehamwood has a population of 36,322 as of 2025.

t0064819 | mode=answer | do you know who maureen mcgovern was haha
gold: american singer and broadway actress
reply: Maureen Mcgovern was a american singer and broadway actress.

t0156472 | mode=clarify_or_likeliest | Which country was David Simon a citizen of?
gold: candidates: ['wb:1613271', 'american author']; ['wb:35140492', 'person']
reply: That isn't in my offline knowledge. The closest match I have is David Simon, a american author. Is that who or what you mean?

t0078577 | mode=answer | his three great works, "la boheme", "madam butterfly" and "turandot", became standard for writing for many generations of composers.
gold: puccini
reply: I don't have la boheme's university's university's university in my offline knowledge. What I do know: la boheme was born in my offline knowledge.

t0007637 | mode=either | what were the names of the men that attempted to rob the bank in the movie dog day afternoon
gold: sonny and sal
reply: I don't have the here about bank, but here's one in my offline knowledge. Could you check the spelling or give me more detail?

t0158633 | mode=either | who was the only president to never live in the white house
gold: george washington
reply: I don't know that, since you haven't told me. Can you tell me?

t0006486 | mode=fallback | Political party of Syed Kamall?
gold: conservative
reply: The party of Syed Kamall isn't in my offline knowledge, but Syed Kamall was born on february 15, 1967.

t0083044 | mode=answer | What line of work was Helen Schucman in?
gold: professor of medical psychology
reply: Helen Schucman's occupation is professor of medical psychology.

t0185734 | mode=either | quick question in the drama movie 21 ben is asked to join the card counting group and immediately agrees
gold: {"answer": "no"} [yesno]
reply: I don't have join the card counting group and immediately agrees in my offline knowledge. Could you check the spelling or give me more detail?

t0029143 | mode=either | when was the third puzzle video game by fireproof games released for ios?
gold: 2015-11
reply: I don't have video game's release year in my offline knowledge. Is there something else about video game I can look up?

t0020969 | mode=answer | Three-letter code of Headingly Airport?
gold: hip
reply: Headingly Airport's airport code is hip.

t0178756 | mode=clarify_or_likeliest | Kellen Winslow plays in what position?
gold: candidates: ['wb:963099', 'american football tight end']; ['wb:1163293', 'person']
reply: That isn't in my offline knowledge. The closest match I have is Kellen Winslow Ii, a american football tight end. Is that who or what you mean?

t0165597 | mode=either | when did the first metroid prime game come out
gold: 2002-11-17
reply: I don't have metroid prime game in my offline knowledge. Could you check the spelling or give me more detail?

t0005795 | mode=answer | I live over in Austin. // What category does a heat of formation belong to? // What money is used in Slovenia? // which city did i say i live in?
gold: austin
reply: I don't know that, since you haven't told me. Can you tell me?

t0020753 | mode=answer | Is 2130 a leap year or not?
gold: {"result": "no, not a leap year", "call": "leap 2130"} [tool]
reply: No, 2130 is not a leap year.

t0130077 | mode=answer | Andre Chapelon passed away on which date?
gold: 1978-7-22
reply: Andre Chapelon died on july 22, 1978.

t0168694 | mode=answer | Which airport sits higher, Red Dog Airport or Sobral Airport?
gold: {"answer": ["red dog airport", "rdb airport"], "other": ["sobral airport"]} [choice]
reply: Red Dog Airport sits higher, at 969 feet, against 210 feet for Sobral Airport.

t0188719 | mode=answer | In which nation is Papatoetoe?
gold: new zealand / aotearoa
reply: Papatoetoe is located in New Zealand.

t0108102 | mode=clarify | When did she die?
gold: {} [none]
reply: Which one do you mean? Can you give me the name?

t0092176 | mode=answer | Which person is older, Cassie Steele or Art Linkletter?
gold: {"answer": ["art linkletter"], "other": ["cassie steele"]} [choice]
reply: Art Linkletter was born first, on july 17, 1912; Cassie Steele was born on december 2, 1989.

t0074862 | mode=fallback | MEANING OF DA WORD MONOMORIUM?
gold: a genus of formicidae
reply: I don't have monomorium's definition in my offline knowledge. Is there something else about monomorium I can look up?

t0141918 | mode=answer | Heads or tails? Flip it for me.
gold: {"valid": ["heads", "tails"]} [random]
reply: The coin landed on tails.

t0116981 | mode=answer | Heads or tails? Flip it for me.
gold: {"valid": ["heads", "tails"]} [random]
reply: The coin landed on tails.

t0035966 | mode=answer | Counting by 7s was written by whom?
gold: holly goldberg sloan
reply: Counting by 7 S was written by Holly Goldberg Sloan.

t0134157 | mode=answer | wats Banak Airport's IATA code
gold: lkl
reply: Banak Airport's airport code is lkl.

t0130785 | mode=answer | What day of the week was George Gilfillan born on?
gold: saturday
reply: George Gilfillan was born on a saturday, january 30, 1813.

t0040112 | mode=fallback | Could you find Rudolf Nureyev's birth date?
gold: 1938-3-17
reply: The date of birth of Rudolf Nureyev isn't in my offline knowledge, but Rudolf Nureyev was born in Near Irkutsk, Russian Sfsr, Soviet Union.

t0168484 | mode=answer | The Warrior Heir was first published in which year?
gold: 2006
reply: The Warrior Heir came out in 2006.

t0132887 | mode=answer | Which country is San Francisco Tesistan in? // What's its population?
gold: 62,397
reply: As of 2025, the population of San Francisco Tesistan is 62,397.

t0111644 | mode=answer | What school did Emma Bonino graduate from?
gold: bocconi university
reply: Emma Bonino's alma mater is Bocconi University.

t0008179 | mode=answer | Highest common factor of 137 and 13?
gold: {"result": "1", "call": "gcd 137 13"} [tool]
reply: The answer is 1.

t0033986 | mode=answer | random question but is Uganda or Australia more populous?
gold: {"answer": ["uganda", "jamhuri ya uganda", "republic of uganda"], "other": ["aus [choice]
reply: Uganda has more people: 34,856,813 against 26,700,000 for Australia.

t0064887 | mode=answer | How many letters does the word banana have?
gold: {"result": "6", "call": "count_letters banana"} [tool]
reply: 6.

t0096691 | mode=answer | What's the birthday of Chris Chambers?
gold: 1978-8-12
reply: Chris Chambers's date of birth is august 12, 1978.

t0048153 | mode=answer | How many people live in the largest city of the US state of South Carolina?
gold: 142,416
reply: Columbia has a population of 142,416 as of 2025.

t0021485 | mode=either | which member of linkin park appeared in saw 3d?
gold: chester bennington
reply: That isn't in my offline knowledge. The closest match I have is C. D. Howe, a powerful canadian cabinet minister. Is that who or what you mean?

t0113692 | mode=answer | Number of moons of the planet Neptune?
gold: 14
reply: As of 2023, neptune has 14 known moons.

t0109821 | mode=answer | GONZALO PIZARRO WAS BORN WHERE
gold: trujillo, spain / trujillo
reply: Gonzalo Pizarro was born in Trujillo, Spain.

t0065413 | mode=clarify | WHEN DID SHE DIE PLS
gold: {} [none]
reply: Which one do you mean? Can you give me the name?

t0045295 | mode=answer | I have a dog named Luna. // hey turbo, what did I say my pet is called?
gold: luna
reply: You told me your pet's name is luna.

t0135932 | mode=answer | Place of death of Charlie Christian?
gold: staten island, new york, united states / staten island
reply: Charlie Christian died in Staten Island, New York, United States.

t0073656 | mode=answer | Where did Harley M. Kilgore pass away? // And when were they born?
gold: 1893-1-11
reply: Harley M. Kilgore was born on january 11, 1893.

t0172806 | mode=answer | People from the country Philippines are called what?
gold: filipino
reply: Someone from Philippines is Filipino.

t0019559 | mode=fallback | Do you know da population figure for Redcar
gold: 37,073
reply: That exact fact isn't in my offline knowledge. Here's what I have: Redcar is in United Kingdom.

t0009610 | mode=answer | How many countries does the country Malta border?
gold: 0
reply: Malta doesn't border any other country.

t0130711 | mode=clarify_or_likeliest | WHICH COUNTRY IS SHARIFABAD IN
gold: candidates: ['city:1106880', 'city in pakistan']; ['city:115382', 'city in iran']
reply: Which Sharifabad do you mean: the city in pakistan or the city in iran?

t0107986 | mode=answer | On which continent is the city of Likino-Dulevo?
gold: europe
reply: Likino-Dulevo is in Russia, which is in Europe.

t0100460 | mode=either | was bruce campbell in army of darkness?
gold: {"answer": "yes"} [yesno]
reply: That isn't in my offline knowledge. The closest match I have is Bruce Campbell, a american film and television actor. Is that who or what you mean?

t0171395 | mode=answer | I work as a nurse. // Felix Carrasco's profession? // What's my job again?
gold: nurse
reply: I don't know that, since you haven't told me. Can you tell me?

t0107987 | mode=answer | What year did W. T. Cosgravve come into the world?
gold: 1880
reply: That isn't in my offline knowledge. The closest match I have is W. T. Cosgrave, a irish politician. Is that who or what you mean?

t0149033 | mode=either | um in 1986 richard dreyfuss appeared in down and out in beverly hills who played his wife in the movie
gold: bette midler
reply: That isn't in my offline knowledge. The closest match I have is Richard Dreyfuss, a american actor. Is that who or what you mean?

t0045985 | mode=answer | Grand Duke Konstantin Pavlovich of Russia died in which year? // AND THEIR BIRTHPLAVE
gold: tsarskoye selo
reply: Grand Duke Konstantin Pavlovich of Russia was born on april 27, 1779.

t0041658 | mode=answer | Population of Ipiranga?
gold: 116,271
reply: As of 2025, the population of Ipiranga is 116,271.

t0119428 | mode=answer | Which money do they use in Anantapur?
gold: indian rupee
reply: Anantapur is in India, which uses the indian rupee.

t0084678 | mode=answer | in what place was sterling hayden born i forgot
gold: montclair, new jersey, united states / montclair
reply: Sterling Hayden was born in Montclair, New Jersey, United States.

t0049263 | mode=answer | Lancaster Airport elevation?
gold: 403 feet
reply: Lancaster Airport is 403 feet above sea level.

t0052490 | mode=answer | WHAT'S THE ELEVATION OF BOOLGEEDA AIRPORT?
gold: 1,870 feet
reply: Boolgeeda Airport is 1,870 feet above sea level.

t0097030 | mode=answer | What's 30% of 832? // What about 10% of it
gold: {"result": "83.2", "call": "pct_of 10 832"} [tool]
reply: That's 83.2.

t0036911 | mode=answer | What line of work was Eden Riegel in just curious
gold: actress
reply: Eden Riegel worked as a actress.

t0187943 | mode=fallback | Who exactly is Laurent de Brunhoff lol
gold: author and illustrator
reply: The description of Laurent de Brunhoff isn't in my offline knowledge, but Laurent de Brunhoff was born on august 30, 1925.

t0079314 | mode=answer | Which ciyt does Kalokol Airport serve
gold: kalokol
reply: Kalokol Airport is in Kalokol.

t0186702 | mode=answer | so like what currency would I need in Tizayuca?
gold: mexican peso
reply: Tizayuca is in Mexico, which uses the mexican peso.

t0040507 | mode=answer | How many people livve in da largest city of the US state of Delaware
gold: 70,898
reply: Wilmington has a population of 70,898 as of 2025.

t0011657 | mode=clarify_or_likeliest | What year did John Crawford come into the world?
gold: candidates: ['wb:38915512', 'scottish footballer']; ['wb:12586053', 'american actor']; ['wb:1144222', 'person']
reply: That isn't in my offline knowledge. The closest match I have is John Crawford, a scottish footballer. Is that who or what you mean?

t0008460 | mode=answer | Which city is the capital of Kyrgyzstan?
gold: bishkek
reply: The capital of Kyrgyzstan is Bishkek.

t0107930 | mode=either | WHEN DID MICHAEL JORDAN RETURN TO THE NBA?
gold: 2001-02 nba season
reply: The date of death of Michael Jordan isn't in my offline knowledge, but Michael Jordan was born in Brooklyn, New York.

t0064962 | mode=answer | What's 30% of 567? // What about 50% of it?
gold: {"result": "283.5", "call": "pct_of 50 567"} [tool]
reply: That's 283.5.

t0069507 | mode=answer | What language is official in Oman
gold: arabic
reply: Oman's official languages are Arabic.

t0169845 | mode=answer | When was the person who wrote Get Shorty born?
gold: 1925
reply: Get Shorty was written by Elmore Leonard, who was born in 1925.

t0015861 | mode=either | what did wwf wrestler the rock major in college?
gold: criminology
reply: That isn't in my offline knowledge. The closest match I have is wwe 2 k, a series. Is that who or what you mean?

t0129601 | mode=answer | Aguilares in El Salvador is on what continent?
gold: north america
reply: Aguilares is in El Salvador, which is in North America.

t0133958 | mode=either | how many miles is it from frankfort, kentucky to boston, massachusetts?
gold: 953
reply: That isn't in my offline knowledge. The closest match I have is Frankfort, a city in south africa. Is that who or what you mean?

t0119934 | mode=answer | Which year is Lillian Board's birth year?
gold: 1948
reply: Lillian Board was born in 1948.

t0091958 | mode=either | WHICH COUNTRY HAS THE OLDEST STILL-STANDING CASTLE, GERMANY OR SYRIA?
gold: syria
reply: I don't have germany-standing castle in my offline knowledge. Could you check the spelling or give me more detail?

t0179824 | mode=answer | Who is Indonesia's head of state right now?
gold: prabowo subianto
reply: I can't see live stock prices offline. Would you like facts about indonesia instead?

t0111883 | mode=answer | What's 248 times 995?
gold: {"result": "246760", "call": "calc 248*995"} [tool]
reply: The answer is 246760.

t0099831 | mode=clarify | hi, how far is it?
gold: {} [none]
reply: Who or what do you mean? Tell me the name and I'll look it up.

t0126104 | mode=answer | Since when has Suffolk University Law School existed?
gold: 1906
reply: I don't have when when when when when when when in my offline knowledge. Could you check the spelling or give me more detail?

t0176009 | mode=fallback | Do you know who Kara Wolters was?
gold: retired american collegiate and professional basketball play
reply: The description of Kara Wolters isn't in my offline knowledge, but Kara Wolters was born in Holliston, Massachusetts.

t0138699 | mode=answer | Populaation of Plaano?
gold: 283,558
reply: That isn't in my offline knowledge. The closest match I have is plano senior high school, a public secondary school in plano. Is that who or what you mean?

t0031079 | mode=answer | Call me Aiko, by the way. // Which country calling code does the country Ghana use? // John Palmer Usher passed away on which date? // Who am I again?
gold: aiko
reply: I don't know that, since you haven't told me. Can you tell me?

t0064824 | mode=answer | Thomas Lincoln was born where?
gold: rockingham county, virginia, u.s. / rockingham county
reply: Thomas Lincoln was born in Rockingham County, Virginia, U. S..

t0097061 | mode=answer | WHICH DATE IS IT TODAY?
gold: {"result": "friday, september 17, 2027", "call": "date"} [tool]
reply: It's friday, september 17, 2027.

t0063980 | mode=answer | Put these in alphabetical order: fig, kiwi, lemon.
gold: {"result": "fig, kiwi, lemon", "call": "sort fig, kiwi, lemon"} [tool]
reply: That's fig, kiwi, lemon.

t0178274 | mode=answer | What's the elevation of Goma International Airport?
gold: 5,089 feet
reply: Goma International Airport is 5,089 feet above sea level.

t0177785 | mode=answer | What was James Whale's job?
gold: film director theatre director
reply: James Whale worked as a film director theatre director.

t0089991 | mode=answer | How many square miles is Bolivia?
gold: 424164.4954 square miles
reply: Bolivia is 1,098,581 square kilometres, which is 424164.4954 square miles.

t0168309 | mode=fallback | Who exactly is Marcin Gortat?
gold: polish professional basketball player
reply: The description of Marcin Gortat isn't in my offline knowledge, but Marcin Gortat was born on february 17, 1984.

t0051092 | mode=either | THIS EUROPEAN UNION MEMBER WAS ONCE KNOWN FOR HUGE MIGRATION OF ITS PEOPLE, MAINLY TO THE US AND UK. NOWADAYS, HOWEVER, IT ATTRACTS MANY IMMIGRANTS FROM NEW EU MEMBERS.
gold: ireland
reply: I don't have once members. Union in my offline knowledge. Could you check the spelling or give me more detail?

t0072170 | mode=answer | What's the birthday of Phil Lamarr?
gold: 1967-1-24
reply: Phil Lamarr was born on january 24, 1967.

t0021641 | mode=answer | Nay Pyi Taw has how many residents?
gold: 925,000
reply: As of 2025, the population of Nay Pyi Taw is 925,000.

t0107670 | mode=answer | which actor is godfather to actress jennifer anniston?
gold: telly savalas
reply: I don't have godfather to actress jennifer anniston in my offline knowledge. Could you check the spelling or give me more detail?

t0141871 | mode=answer | Is 2058 a leap year or not?
gold: {"result": "no, not a leap year", "call": "leap 2058"} [tool]
reply: No, 2058 is not a leap year.

t0035640 | mode=answer | IN WHICH YERA DID THOMAS LITTLE HEATH DIE?
gold: 1940
reply: Thomas Little Heath died in 1940.

t0055334 | mode=answer | Date of death of Karl Emil Franzos?
gold: 1904-1-28
reply: Karl Emil Franzos's date of death is january 28, 1904.

t0164729 | mode=answer | Take 4145 away from 40575. What's left?
gold: {"result": "36430", "call": "calc 40575-4145"} [tool]
reply: The answer is 36430.

t0134501 | mode=answer | What's 611 times 154?
gold: {"result": "94094", "call": "calc 611*154"} [tool]
reply: The answer is 94094.

t0116396 | mode=fallback | How much is Samsung stock trading at right now?
gold: {} [none]
reply: I can't see live prices offline. Is there something else about money or markets I can explain?

t0103910 | mode=answer | Jerzy Urban's nationality?
gold: polish
reply: Jerzy Urban is Polish.

t0112959 | mode=either | what does scottish ppl speak?
gold: english language
reply: That isn't in my offline knowledge. The closest match I have is liverpool scottish, a unit of the british army. Is that who or what you mean?

t0084821 | mode=answer | How old was Joe Paterno when they died?
gold: 85
reply: Joe Paterno died on january 22, 2012.

t0118299 | mode=answer | What's 667 times 923?
gold: {"result": "615641", "call": "calc 667*923"} [tool]
reply: The answer is 615641.

t0024260 | mode=answer | Take 25 away from 32222. What's left?
gold: {"result": "32197", "call": "calc 32222-25"} [tool]
reply: The answer is 32197.

t0172976 | mode=either | how long did the mariner sail alone after the crew had died in the rime of the ancient mariner?
gold: seven days and seven nights
reply: I don't have that about after man in my offline knowledge. What I do know: after man came out in 1981.

t0088054 | mode=answer | Which city does Logan-Cache Airport serve?
gold: logan
reply: Logan-Cache Airport serves Logan.

t0030514 | mode=either | where in the usa would you find the place that in 1921 set a north american record for the largest snowfall in a 24-hour period?
gold: colorado
reply: I don't have 1921 - hour record in my offline knowledge. Could you check the spelling or give me more detail?

t0194162 | mode=answer | Was 2317 a leap year?
gold: {"result": "no, not a leap year", "call": "leap 2317"} [tool]
reply: No, 2317 is not a leap year.

t0185362 | mode=answer | Who is the author of What Katy Did?
gold: susan coolidge
reply: That isn't in my offline knowledge. The closest match I have is What Katy Did, a book by susan coolidge. Is that who or what you mean?

t0030029 | mode=answer | What's the diameter of the planet Mercury in miles?
gold: 3031.67 miles
reply: Mercury is 4,879 km, which is 3031.67 miles.

t0004221 | mode=either | what else is there in orlando besides disney i forgot
gold: baldwin park
reply: I don't have there in orlando besides disney in my offline knowledge. Could you check the spelling or give me more detail?

t0034918 | mode=either | WHICH TEAM IS CALLED THE BLUE HOSE AND PLAYS THEIR HOME GAMES IN CLINTON, SC?
gold: presbyterian college
reply: I don't have the blue hose and plays their home games in my offline knowledge. Could you check the spelling or give me more detail?

t0031669 | mode=clarify | What's the capital
gold: {} [none]
reply: Which one do you mean? Can you give me the name?

t0166816 | mode=answer | Which year is Rituparna Sengupta's birth year?
gold: 1971
reply: Rituparna Sengupta was born in 1971.

t0121707 | mode=answer | Divide 7560 by 28
gold: {"result": "270", "call": "calc 7560/28"} [tool]
reply: The answer is 270.

t0007738 | mode=answer | Which country is Lahr in?
gold: germany / bundesrepublik deutschland / federal republic of germany
reply: Lahr is located in Germany.

t0145313 | mode=fallback | What line of work was Mark Moses in?
gold: actor
reply: The occupation of Mark Moses isn't in my offline knowledge, but Mark Moses was born in New York City, New York, U. S..

t0050470 | mode=fallback | Do you know Edna Schmidt's date of birth?
gold: 1969-8-8
reply: The date of birth of Edna Schmidt isn't in my offline knowledge, but Edna Schmidt is a journalist.

t0020648 | mode=answer | wats nimes-arles-camargue airport's elevation in meters?
gold: 94.1832 metres
reply: Nimes-Arles-Camargue Airport is 309 feet, which is 94.1832 meters.

t0092382 | mode=answer | population of akure?
gold: 730,000
reply: As of 2025, Akure has about 730,000 people.

t0100405 | mode=answer | What is Tracfone Wireless?
gold: prepaid wireless service provider
reply: Tracfone wireless is a prepaid wireless service provider.

t0126873 | mode=answer | Which planet is farther from the sun, the planet Neptune or the planet Mercury?
gold: {"answer": ["neptune"], "other": ["mercury"]} [choice]
reply: Neptune is farther from the sun: 4,515 million km against 57.9 million km for mercury.

t0084477 | mode=answer | wats 21399 minus 483
gold: {"result": "20916", "call": "calc 21399-483"} [tool]
reply: The answer is 20916.

t0129281 | mode=answer | I'm based in Lisbon. // Do you know the population figure for Babol? // What town was Bobby Gimby born in? // WHICH CITY DID I SAY I LIVE IN?
gold: lisbon
reply: You live in lisbon.

t0017959 | mode=answer | Which period is Astatine in on the periodic table?
gold: 6
reply: Astatine is in period 6.

t0156549 | mode=clarify_or_likeliest | Umarkot is located in which country?
gold: candidates: ['city:1162959', 'city in pakistan']; ['city:1253860', 'city in india']
reply: Which Umarkot do you mean: the city in pakistan or the city in india?

t0058618 | mode=answer | Where was William Vanneck, 5th Baron Huntingfield educated?
gold: wellington college
reply: The place of death of William Vanneck, 5 Th Baron Huntingfield isn't in my offline knowledge, but William Vanneck, 5 Th Baron Huntingfield was born on january 3, 1883.

t0145873 | mode=fallback | A POPULARITY IS A TYPE OF WHAT?
gold: quality
reply: I don't have popularity contest's category in my offline knowledge. What I do know: popularity means the quality of being widely admired or accepted or sought after.

t0127618 | mode=answer | HI, SAULT STE. MARIE IS ON WHAT CONTINENT?
gold: north america
reply: Sault ste. Marie greyhounds isn't in my offline knowledge, but sault ste. Marie greyhounds is in is in is in scratch.

t0083053 | mode=answer | Which filmmaker directed An American Tail?
gold: don bluth
reply: The director of an american tail is Don Bluth.

t0018111 | mode=answer | Who is the author of Wait for You?
gold: j. lynn
reply: The author of Wait for You is J. Lynn.

t0024206 | mode=answer | What language is official in Italy?
gold: italian
reply: Italy's official languages are Italian.

t0089455 | mode=answer | In which place did Nicholas Ray die? // AND THEIR DATE OF DETH?
gold: 1979-6-16
reply: Nicholas Ray died on june 16, 1979.

t0073477 | mode=answer | Convert 268 pounds into kilograms.
gold: {"result": "121.5628 kilograms", "call": "convert 268 lb kg"} [tool]
reply: That's 121.5628 kilograms.

t0083127 | mode=answer | How many days are left until June 23, 2024?
gold: {"result": "153 days", "call": "days_until 2024-06-23"} [tool]
reply: That's 153 days.

t0107004 | mode=answer | Which year is Tom Berenger's birth year?
gold: 1949
reply: Tom Berenger was born in 1949.

t0010025 | mode=answer | Roughly how many people are in Camama?
gold: 667,094
reply: As of 2025, the population of Camama is 667,094.

t0022070 | mode=answer | What year did Pierre Werner pass away?
gold: 2002
reply: Pierre Werner died in 2002.

t0034759 | mode=either | ailurophobia is fear of these animals.
gold: cats
reply: Hi fear, nice to meet you!

t0008108 | mode=answer | Is every morphophonemic system a system?
gold: {"answer": "yes"} [yesno]
reply: I don't have every morphophonemic system in my offline knowledge. Could you check the spelling or give me more detail?

t0012618 | mode=answer | HOW MANY LETTERS DOES DA WORD BANANA HAVE?
gold: {"result": "6", "call": "count_letters banana"} [tool]
reply: 6.

t0100020 | mode=answer | What do people in Kenya pay with? // AND WHAT ABOUT SINT MAARTEN?
gold: caribbean guilder
reply: Sint Maarten is in North America.

t0199251 | mode=answer | HMM WHAT'S SAMBAVA AIRPORT'S ELEVATION IN METERS?
gold: 6.096 metres
reply: Sambava Airport is 20 feet, which is 6.096 meters.

t0186729 | mode=answer | What's the greatest common divisor of 98 and 79?
gold: {"result": "1", "call": "gcd 98 79"} [tool]
reply: The answer is 1.

t0043160 | mode=answer | The Prince by Kiera Cass was first published in which year? // And what about On the Night You Were Born?
gold: 2005
reply: That isn't in my offline knowledge. The closest match I have is a hard day's night, a 1964 british musical comedy film. Is that who or what you mean?

t0181342 | mode=answer | What's 2 to the power of 3?
gold: {"result": "8", "call": "calc 2^3"} [tool]
reply: The answer is 8.

t0095466 | mode=answer | What's 30% of 387? // Now do 50% i forgot
gold: {"result": "193.5", "call": "pct_of 50 387"} [tool]
reply: That's 193.5.

t0166251 | mode=clarify_or_likeliest | Murcia is located in which country?
gold: candidates: ['city:2513416', 'city in south-eastern spain']; ['city:1699060', 'city in philippines']
reply: Which Murcia do you mean: the city in south-eastern spain or the city in philippines?

t0115400 | mode=clarify_or_likeliest | quick question, population of saint-denis?
gold: candidates: ['city:935264', 'city in reunion']; ['city:2980916', 'city in france']
reply: Which Saint-Denis do you mean: the city in reunion or the city in france?

t0058729 | mode=fallback | Place of death of Carl Gardner?
gold: port st. lucie, florida, united states / port st. lucie
reply: The place of death of Carl Gardner isn't in my offline knowledge, but Carl Gardner worked as a singer.

t0030131 | mode=answer | Is every cardiopulmonary exercise a landing approach?
gold: {"answer": "no"} [yesno]
reply: No, a cardiopulmonary exercise is not a kind of landing approach.

t0148207 | mode=answer | where did jack naylor pass away?
gold: chestnut hill, massachusetts, u.s. / chestnut hill
reply: Jack Naylor died in Chestnut Hill, Massachusetts, U. S..

t0072866 | mode=answer | Is Tanzania or Malawi larger in area?
gold: {"answer": ["tanzania", "jamhuri ya muungano wa tanzania", "united republic of t [choice]
reply: Tanzania is bigger: 945,087 square kilometres against 118,484 square kilometres for Malawi.

t0003193 | mode=clarify_or_likeliest | Amanda Palmer: year of birth?
gold: candidates: ['wb:8244356', 'person']; ['wb:1624044', 'person']
reply: Which Amanda Palmer do you mean: the person, film & media executive or the person, singer-songwriter?

t0056037 | mode=answer | In which nation is Charleville-Mezieres? // What's its population?
gold: 52,415
reply: Who or what do you mean? Tell me the name and I'll look it up.

t0179242 | mode=answer | which novel did george orwell wrte first, animal farm or nineten eighty-four?
gold: animal farm
reply: 1984 came out first, on 1949 1949; George Orwell came out in 1950.

t0098815 | mode=answer | what currency would i need in apple valley california
gold: united states dollar
reply: Apple Valley is in United States, which uses the united states dollar.

t0164883 | mode=answer | CONCERT MDCCCLX FROM ROMAN NUMERALS
gold: {"result": "1860", "call": "roman mdccclx"} [tool]
reply: That isn't in my offline knowledge. The closest match I have is the concert for bangladesh, a thing. Is that who or what you mean?

t0056831 | mode=fallback | WHAAT'S THE PRICE OF BITCOIN AT THE MOMENT?
gold: {} [none]
reply: I can't see live prices offline. Is there something else about money or markets I can explain?

t0133265 | mode=answer | JOHN HAY BEITH DIED WHERE?
gold: liss, petersfield, hampshire / liss
reply: John Hay Beith died in Liss, Petersfield, Hampshire.

t0167258 | mode=answer | What country would I be in at Le Puy-Loudes Airport?
gold: france / french republic / republique francaise
reply: I don't have I be at le puy-loudes airport in my offline knowledge. Could you check the spelling or give me more detail?

t0183608 | mode=either | THIS MICHAEL HAS SOLD OVER 170 MILLION ALBUMS WORLDWIDE. HE IS THE GODFATHER OF THE BEE GEES FRONTMANS SON MICHAEL GIBB.
gold: michael jackson
reply: I don't have sold over 170 million albums worldwide in my offline knowledge. Could you check the spelling or give me more detail?

t0118648 | mode=answer | Count the c's in computer.
gold: {"result": "1", "call": "count_letter c computer"} [tool]
reply: That isn't in my offline knowledge. The closest match I have is C. D. Howe, a powerful canadian cabinet minister. Is that who or what you mean?

t0186097 | mode=clarify_or_likeliest | In which nation is Wujia?
gold: candidates: ['city:1791188', 'city in china']; ['city:1791214', 'city in china']
reply: Which Wujia do you mean: the city in china or the city in china?

t0141168 | mode=either | what was vietnam war fought for?
gold: communism
reply: That isn't in my offline knowledge. The closest match I have is vietnam veterans against, a american tax-exempt non -. Is that who or what you mean?

t0031519 | mode=fallback | Who won last night's game?
gold: {} [none]
reply: I can't follow live games offline. Which team are you asking about?

t0007318 | mode=answer | Does Yttrium or Bismuth have more protons?
gold: {"answer": ["bismuth"], "other": ["yttrium"]} [choice]
reply: Bismuth is heavier: 208.98 against 88.906 for yttrium.

t0159859 | mode=answer | Which country is Gerakas in? // How about Ridder?
gold: kazakhstan / qazaqstan / qazaqstan respublikasi
reply: As of 2025, Ridder has about 52,664 people.

t0140632 | mode=either | according to scientific classifications, to which kingdom do fungi belong?
gold: none of these
reply: I don't have which the director of according to scientific classifications in my offline knowledge. Could you check the spelling or give me more detail?

t0163629 | mode=answer | place of death of sir james killen?
gold: brisbane, queensland / brisbane
reply: James Killen died in Brisbane, Queensland.

t0090888 | mode=answer | What day of the week was Jose Ortiz born on?
gold: wednesday
reply: Jose Ortiz was born on a wednesday, october 23, 1963.

t0166879 | mode=fallback | how much is one ethereum worth today?
gold: {} [none]
reply: I can't see live prices offline. Is there something else about money or markets I can explain?

t0135531 | mode=answer | da country Armenia has how many official languages?
gold: 1
reply: Armenia has 1 official language, Armenian.

t0074276 | mode=answer | On what date did Elisabeth Farnese die?
gold: 1766-7-11
reply: Elisabeth Farnese died on july 11, 1766.

t0074378 | mode=clarify_or_likeliest | In which nation is Dakhla Airport?
gold: candidates: ['airport:VIL', 'airport in dakhla']; ['airport:DAK', 'airport in dakhla']
reply: Which Dakhla Airport do you mean: the airport in dakhla or the airport in dakhla?

t0154581 | mode=answer | What is tomato spelled in reverse?
gold: {"result": "otamot", "call": "reverse tomato"} [tool]
reply: Esrever.

t0155066 | mode=answer | When is Christmas this year?
gold: {"result": "thursday, december 25, 2025, in 358 days", "call": "holiday christma [tool]
reply: Christmas is on thursday, december 25, 2025, in 358 days.

t0113547 | mode=answer | I'm based in Krakow. // What does Josh Casaubon do for a living? // Gerald Mcraney's nationality? // Which city did I say I live in?
gold: krakow
reply: You live in krakow.

t0129865 | mode=answer | WHAT LINE OF WORK WAS ALEXANDRU MACEDONSKI IN?
gold: poet
reply: Alexandru Macedonski's occupation is poet.

t0165189 | mode=answer | What year did Night World, No. 2 come out? // How about Dead Poets Society?
gold: 1988
reply: Dead Poets Society was published in 1988.

t0014311 | mode=answer | Percent change from 786 to 490?
gold: {"result": "a decrease of 37.659033%", "call": "pct_change 786 490"} [tool]
reply: That's a decrease of 37.659033%.

t0152854 | mode=answer | The Quiet was directed by who thanks!
gold: jamie babbit
reply: The director of the quiet is Jamie Babbit.

t0092185 | mode=answer | WHAT'S 14676 MIINUS 8856 :)
gold: {"result": "5820", "call": "calc 14676-8856"} [tool]
reply: The answer is 5820.

t0049697 | mode=fallback | whats Eddie Kendricks's home phone number?
gold: {} [none]
reply: I don't have private details like that, and I wouldn't share them. What I do know: Eddie Kendricks is a american singer and songwriter.

t0040179 | mode=answer | At what age did Steve Gerber die?
gold: 60
reply: Steve Gerber was 60 years old when they died.

t0102249 | mode=answer | What line of work was Don Spencer in?
gold: musician
reply: Don Spencer worked as a musician.

t0092939 | mode=clarify_or_likeliest | Fresno is in what state
gold: candidates: ['city:5350937', 'city in california']; ['city:4692400', 'city in texas']
reply: Which Fresno do you mean: the city in california or the city in texas?

t0008977 | mode=answer | How much should I tip on 158 dollars at 22 percent?
gold: {"result": "tip 34.76, total 192.76", "call": "tip 22 158"} [tool]
reply: That's a tip 34.76, total 192.76.

t0119665 | mode=answer | Which city is the capital of the country British Virgin Islands?
gold: road town
reply: The capital of British Virgin Islands is Road Town.

t0115590 | mode=answer | Date of death of Endre Ady?
gold: 1919-1-27
reply: Endre Ady died on january 27, 1919.

t0031624 | mode=answer | WHAT'S 12 TO THE POWER OF 5?
gold: {"result": "248832", "call": "calc 12^5"} [tool]
reply: The answer is 248832.

t0077902 | mode=answer | How many square miles is the country Guam?
gold: 211.970085 square miles
reply: Guam is 549 square kilometres, which is 211.9701 square miles.

t0150832 | mode=either | raphael santi was the original architect of the chigi chapel but gian bernini finished it, after raphael became a father.
gold: {"answer": "no"} [yesno]
reply: That isn't in my offline knowledge. The closest match I have is Raphael, a person, italian. Is that who or what you mean?

t0196005 | mode=either | which river is longer than the mississippi river?
gold: nile
reply: I couldn't find longer than the mississippi river in my offline knowledge. Could you check the spelling?

t0077300 | mode=clarify | How old is he?
gold: {} [none]
reply: Which one do you mean? Can you give me the name?

t0070665 | mode=fallback | Grover Norquist belonged to which party
gold: republican
reply: The party of Grover Norquist isn't in my offline knowledge, but Grover Norquist is a american political advocate.

t0018479 | mode=answer | what is the biggest city in india?
gold: mumbai
reply: The head of state of India isn't in my offline knowledge, but India: indian rupee.

t0055977 | mode=clarify | HOW FAR IS IT HAHA
gold: {} [none]
reply: Who or what do you mean? Tell me the name and I'll look it up.

t0025967 | mode=answer | Birthplace of Christopher Reeve lol
gold: new york city, united states / new york city
reply: Christopher Reeve was born in New York City, United States.

t0171376 | mode=answer | random question but date of death of Carlos Antonio Carrillo
gold: 1852-2-23
reply: Carlos Antonio Carrillo died on february 23, 1852.

t0160879 | mode=answer | WHICH ELEMENT IS HEAVIER, AMERICIUM OR THE ELEMMENT SULFUR?
gold: {"answer": ["americium"], "other": ["sulfur"]} [choice]
reply: Americium is heavier: 243 against 32.06 for sulfur.

t0008891 | mode=clarify_or_likeliest | Population of Santo Amaro?
gold: candidates: ['city:3449715', 'city']; ['city:3449720', 'city in brazil']
reply: Which Santo Amaro do you mean: the city or the city in brazil?

t0007091 | mode=answer | Espinosa Airport is in which city?
gold: espinosa
reply: Espinosa Airport is in Espinosa.

t0062495 | mode=answer | What is the area of the country Jamaica in square miles?
gold: 4243.6488 square miles
reply: Jamaica is 10,991 square kilometres, which is 4243.6488 square miles.

t0048015 | mode=fallback | What is Clark Terry's home phone number?
gold: {} [none]
reply: I don't have private details like that, and I wouldn't share them. What I do know: Clark Terry was born on december 14, 1920.

t0137165 | mode=answer | MEANING OF DA WORD VOWEL SYSTEM?
gold: the system of vowels used in a particular language
reply: Vowel system means the system of vowels used in a particular language.

t0029708 | mode=either | what kooky movie character, portrayed by johnny depp, was skilled at topiary?
gold: edward scissorhands
reply: I don't have portray's publication year in my offline knowledge. Is there something else about portray I can look up?

t0138387 | mode=fallback | What kind of music does Gregory Benford make?
gold: science fiction
reply: The nationality of Gregory Benford isn't in my offline knowledge, but Gregory Benford worked as a scientist.

t0040469 | mode=clarify_or_likeliest | Which writer wrote The Island?
gold: candidates: ['book:3204', 'book by elin hilderbrand']; ['book:3802', 'book by victoria hislop']
reply: Which the Island do you mean: the book by elin hilderbrand or the book by victoria hislop?

t0004307 | mode=answer | What's 25% of 94? // real quick: and 75%?
gold: {"result": "70.5", "call": "pct_of 75 94"} [tool]
reply: That's 70.5.

t0013616 | mode=either | who painted mr and mrs clark and percy, and a bigger splash?
gold: david hockney
reply: I don't have and a bigger splash and mrs clark and percy, and a bigger splash in my offline knowledge. Could you check the spelling or give me more detail?

t0181844 | mode=answer | WHICH CITY DOES LIPETSK AIRPORT SERVE?
gold: lipetsk
reply: Lipetsk Airport is in Lipetsk.

t0111196 | mode=clarify_or_likeliest | In which year was Andriy Shevchenko born?
gold: candidates: ['wb:616622', 'former ukrainian footballer']; ['wb:10731542', 'person']
reply: That isn't in my offline knowledge. The closest match I have is Andriy Shevchenko, a former ukrainian footballer. Is that who or what you mean?

t0097483 | mode=answer | In which nation is Dracut?
gold: united states / united states of america
reply: Dracut is located in United States.

t0107455 | mode=answer | What do you get if you add 54388 and 7079?
gold: {"result": "61467", "call": "calc 54388+7079"} [tool]
reply: The answer is 61467.

t0071670 | mode=answer | What was Nick Lampson's job?
gold: high school teacher
reply: Nick Lampson worked as a high school teacher.

t0043826 | mode=answer | kamyaakkavundanpatti has how many residents?
gold: 16,134
reply: Pick a whole number from 1 to 3999.

t0115029 | mode=answer | Do you know the population figure for El Hadjira?
gold: 39,744
reply: As of 2025, the population of El Hadjira is 39,744.

t0084856 | mode=answer | Is the country Egypt or Nigeria larger in area?
gold: {"answer": ["egypt", "arab republic of egypt"], "other": ["nigeria"]} [choice]
reply: Egypt is bigger: 1,002,450 square kilometres against 923,768 square kilometres for Nigeria.

t0025171 | mode=answer | Can you explain what 'conserve' means?
gold: fruit preserved by cooking with sugar
reply: Conserve means fruit preserved by cooking with sugar.

t0080690 | mode=fallback | IS IT RAINING IN MOGI DAS CRUZES TODAY
gold: {} [none]
reply: I can't check live weather offline. What I do know: Mogi Das Cruzes is in Brazil.

t0097137 | mode=answer | What line of work was Joe Barton in?
gold: politician
reply: Joe Barton's occupation is politician.

t0058717 | mode=clarify_or_likeliest | Population of Roswell?
gold: candidates: ['city:4219934', 'city in georgia']; ['city:5488441', 'city in new mexico']
reply: Which Roswell do you mean: the city in georgia or the city in new mexico?

t0148560 | mode=answer | I work as a architect. // wats my job again
gold: architect
reply: I don't know that, since you haven't told me. Can you tell me?

t0182625 | mode=answer | Who is Nelson Pereira Dos Santos?
gold: brazilian film director
reply: Nelson Pereira Dos Santos is a brazilian film director.

t0122843 | mode=clarify_or_likeliest | toledo has how many residents?
gold: candidates: ['city:5174035', 'city in ohio']; ['city:1681602', 'city in philippines']; ['city:3446370', 'city in brazil']
reply: Pick a whole number from 1 to 3999.

t0067090 | mode=answer | Which airport sits higher, Lugano Airport or Chaudhary Charan Singh International Airport?
gold: {"answer": ["lugano airport", "lug airport"], "other": ["chaudhary charan singh  [choice]
reply: Lugano Airport sits higher, at 915 feet, against 410 feet for Chaudhary Charan Singh International Airport.

t0032192 | mode=answer | If I'm in Hillside, New York, what's the capital of that country?
gold: washington d.c.
reply: That isn't in my offline knowledge. The closest match I have is Hillside, a city in new york. Is that who or what you mean?

t0004043 | mode=answer | What style of music is Raja Rao known for?
gold: novel
reply: Raja Rao is known for novel.

t0030997 | mode=answer | I like the colour orange the most. // Where's Guillermo Canas's birthplace? // Moon Palace was first published in which year? // Remind me of my favourite colour
gold: orange
reply: I don't know that, since you haven't told me. Can you tell me?

t0187764 | mode=answer | WHAT IS 90% OF 3194?
gold: {"result": "2874.6", "call": "pct_of 90 3194"} [tool]
reply: That's 2874.6.

t0095335 | mode=answer | What category does a radio beam belong to?
gold: signal / signaling / sign
reply: That isn't in my offline knowledge. The closest match I have is radio beam, a word. Is that who or what you mean?

t0079784 | mode=either | johnny carson plays the part of a car salesman named cheerful charlie in a 1969 episode of heres lucy.
gold: {"answer": "no"} [yesno]
reply: I don't have car salesman named cheerful charlie in my offline knowledge. Could you check the spelling or give me more detail?

t0180063 | mode=answer | Which countries does Turkmenistan share a border with?
gold: afghanistan, iran, kazakhstan, uzbekistan
reply: That isn't in my offline knowledge. The closest match I have is Turkmenistan, a country in central asia. Is that who or what you mean?

t0179989 | mode=answer | How many miles across is the planet Jupiter?
gold: 86880.1201 miles
reply: As of 2023, jupiter has 95 known moons.

t0187265 | mode=fallback | Lauderhill is located in which country?
gold: united states / united states of america
reply: The country of Lauderhill isn't in my offline knowledge, but Lauderhill has a population of 71,579 as of 2025.

t0054655 | mode=answer | Psycho Ii was directed by who?
gold: richard franklin
reply: The director of psycho ii is Richard Franklin.

t0154974 | mode=answer | RANDOM QUESTION BUT WHEN WAS THE PERSON WHO WROTE CRIME AND PUNISHMENT BORN
gold: 1821
reply: Crime and Punishment was written by Fyodor Dostoyevsky, who was born in 1821.

t0059879 | mode=clarify_or_likeliest | How populated is Palmira?
gold: candidates: ['city:3673164', 'city in colombia']; ['city:3630982', 'city in venezuela']; ['city:3545040', 'city in cuba']
reply: Which Palmira do you mean: the city in colombia or the city in venezuela?

t0002983 | mode=clarify_or_likeliest | Do you know the population figure for Longgang?
gold: candidates: ['city:1802656', 'city in china']; ['city:1802651', 'city in china']; ['city:1802550', 'city in china']
reply: That isn't in my offline knowledge. The closest match I have is Longgang, a city in china. Is that who or what you mean?

t0086597 | mode=answer | In which year did Pedro Fages die?
gold: 1794
reply: Pedro Fages died in 1794.

t0157655 | mode=either | theakstons brewery is based in which yorkshire town ?
gold: masham
reply: That isn't in my offline knowledge. The closest match I have is boddingtons brewery, a regional brewery in manchester. Is that who or what you mean?

t0125242 | mode=answer | What's Hastings Municipal Airport's IATA code?
gold: hsi
reply: Hastings Municipal Airport's airport code is hsi.

t0022491 | mode=answer | Do you know where Joel Siegel died?
gold: new york city, new york, u.s. / new york city
reply: Joel Siegel's place of death is New York City, New York, U. S..

t0038390 | mode=answer | Andrew Hayden-Smith was born where?
gold: gateshead, england, uk / gateshead
reply: Andrew Hayden-Smith was born in Gateshead, England, Uk.

t0159038 | mode=answer | CURRENT LOCAL TIME IN BERLIN?
gold: {"result": "7:59 pm, tuesday", "call": "world_time berlin"} [tool]
reply: It's 7: 59 pm, tuesday in berlin.

t0178234 | mode=either | why did cher and christian not get together in clueless, even though cher had a big crush on him?
gold: he was gay.
reply: I don't have even and christian not in my offline knowledge. Could you check the spelling or give me more detail?

t0036167 | mode=answer | Current local time in Berlin?
gold: {"result": "3:56 pm, friday", "call": "world_time berlin"} [tool]
reply: It's 3: 56 pm, friday in berlin.

t0008883 | mode=answer | Birthplace of John Kapelos?
gold: london, ontario, canada / london
reply: John Kapelos was born in London, Ontario, Canada.

t0037234 | mode=answer | What's 12 to the power of 5
gold: {"result": "248832", "call": "calc 12^5"} [tool]
reply: The answer is 248832.

t0000769 | mode=answer | What's the diameter of Saturn in miles?
gold: 72364.889 miles
reply: Saturn is 116,460 km, which is 72364.889 miles.

t0069262 | mode=clarify_or_likeliest | ROUGHLY HOW MANY PEOPLE ARE IN MIDLOTHIAN
gold: candidates: ['city:4711156', 'city in united states']; ['city:4772943', 'city in united states']
reply: Which Midlothian do you mean: the city in united states or the city in united states?

t0028549 | mode=answer | What was Chen Liting's job?
gold: playwright
reply: Chen Liting's occupation is playwright.

t0007784 | mode=answer | Do you know where Curtis Martin was born?
gold: pittsburgh, pennsylvania / pittsburgh
reply: Curtis Martin was born in Pittsburgh, Pennsylvania.

t0043470 | mode=answer | Do u know who He Dahir Riyale Kahin was
gold: somali politician
reply: That isn't in my offline knowledge, but I can tell you that Kahin has a population of 32,991 as of 2025.

t0119599 | mode=answer | What party did Marco Fidel Suarez represent?
gold: conservative
reply: Marco Fidel Suarez belonged to the Conservative party.

t0090643 | mode=answer | What is 80% of 687?
gold: {"result": "549.6", "call": "pct_of 80 687"} [tool]
reply: That's 549.6.

t0173685 | mode=answer | What money is used in Saint Barthelemy? // And what about the country France
gold: euro
reply: France uses the euro.

t0039610 | mode=answer | Take 1536 away from 32744. wats left?
gold: {"result": "31208", "call": "calc 32744-1536"} [tool]
reply: The answer is 31208.

t0064451 | mode=answer | IRAQ SHARES A BORDER WTH HOW MANY COUNTRIES?
gold: 6
reply: Iraq borders 6 countries: Iran, Jordan, Kuwait, Saudi Arabia, Syria and Turkiye.

t0085968 | mode=clarify_or_likeliest | Which US state is Garden City in?
gold: candidates: ['city:5445439', 'city in kansas']; ['city:4993659', 'city in michigan']; ['city:5118226', 'city in new york']
reply: That isn't in my offline knowledge. The closest match I have is Garden City, a city in kansas. Is that who or what you mean?

t0031132 | mode=clarify_or_likeliest | Do you know the population figure for Qina?
gold: candidates: ['city:350550', 'city']; ['city:1797962', 'city in china']
reply: Which Qina do you mean: the city or the city in china?

t0149520 | mode=answer | Niort is on what continent?
gold: europe
reply: Niort is in France, which is in Europe.

t0030851 | mode=answer | What do you get if you add 77434 and 4346?
gold: {"result": "81780", "call": "calc 77434+4346"} [tool]
reply: The answer is 81780.

t0129688 | mode=answer | Current local time in Istanbul?
gold: {"result": "3:14 pm, tuesday", "call": "world_time istanbul"} [tool]
reply: It's 11: 14 pm, monday in istanbul.

t0129780 | mode=answer | Naomi Mitchison's musical genre?
gold: historical
reply: Naomi Mitchison is known for historical.

t0073630 | mode=answer | What language is official where Toritama is?
gold: portuguese
reply: Toritama is in Brazil, where the official language is Portuguese.

t0187002 | mode=answer | CONVERT 333 POUNDS INTO KILOGRAMS.
gold: {"result": "151.0463 kilograms", "call": "convert 333 lb kg"} [tool]
reply: That's 151.0463 kilograms.

t0176161 | mode=clarify_or_likeliest | Westchester is located in which country?
gold: candidates: ['city:4177965', 'city in florida']; ['city:4916140', 'city in illinois']
reply: Which Westchester do you mean: the city in florida or the city in illinois?

t0011863 | mode=answer | Augustus Summerfield Merrimon died where? // And when were they born?
gold: 1830-9-15
reply: Augustus Summerfield Merrimon was born on september 15, 1830.

t0062183 | mode=answer | WHAT'S THE TIME RIGHT NOW ?
gold: {"result": "4:08 pm", "call": "time"} [tool]
reply: It's 4: 08 pm.

t0128693 | mode=answer | What's the greatest common divisor of 186 and 123?
gold: {"result": "3", "call": "gcd 186 123"} [tool]
reply: The answer is 3.

t0058115 | mode=answer | Which book came out first, Red Harvest or A Town Like Alice?
gold: {"answer": ["red harvest"], "other": ["a town like alice"]} [choice]
reply: Red Harvest came out first, in 1929; a Town Like Alice came out in 1950.

t0163589 | mode=answer | Bay Point is in what state?
gold: california
reply: Bay Point is in California.

t0111583 | mode=answer | Zygmunt Bauman: year of birth?
gold: 1925
reply: Zygmunt Bauman's birth year is 1925.

t0103764 | mode=answer | Can you throw a die?
gold: {"valid": ["1", "2", "3", "4", "5", "6"]} [random]
reply: It's a 6.

t0008764 | mode=answer | TOMMY TEE'S MUSICAL GENRE?
gold: rap
reply: Tommy Tee is known for rap.

t0110172 | mode=answer | IS A GLYCEROL A KIND OF SUBSTANCE?
gold: {"answer": "yes"} [yesno]
reply: Yes, a glycerol is a kind of substance.

t0090260 | mode=clarify_or_likeliest | what line of work was tom ford in?
gold: candidates: ['wb:174001', 'american fashion designer and film director']; ['wb:9899105', 'person']
reply: Which Tom Ford do you mean: the american fashion designer and film director or the person, television presenter and journalist?

t0055428 | mode=answer | Is Mars or the planet Neptune closer to the sun?
gold: {"answer": ["mars"], "other": ["neptune"]} [choice]
reply: Mars is farther from the sun: 227.9 million km against 4,515 million km for neptune.

t0169419 | mode=answer | What day of the week is June 25 2019
gold: {"result": "tuesday", "call": "weekday 2019-06-25"} [tool]
reply: The answer is tuesday.

t0145303 | mode=fallback | who is paolo montero?
gold: former uruguayan footballer
reply: The description of Paolo Montero isn't in my offline knowledge, but Paolo Montero was born in Montevideo, Uruguay.

t0008957 | mode=answer | Country domain for Rwanda?
gold: .rw
reply: The internet domain of Rwanda is. Rw.

t0073732 | mode=answer | What's the definition of coroneted?
gold: belonging to the peerage
reply: Coroneted means belonging to the peerage.

t0033901 | mode=answer | What's the diameter of Mars in miles?
gold: 4212.2753 miles
reply: Mars is 6,779 km, which is 4212.2753 miles.

t0053129 | mode=answer | What is meant by dressage?
gold: maneuvers of a horse in response to body signals by the ride
reply: I couldn't find meant by dressage in my offline knowledge. Could you check the spelling?

t0131548 | mode=answer | so like how many people live in da capital city of Maldives
gold: 103,693
reply: Male has a population of 103,693 as of 2025.

t0045122 | mode=answer | Which artist released Two Tribes
gold: frankie goes to hollywood
reply: Two tribes is by Frankie Goes to Hollywood.

t0060216 | mode=answer | The country Montenegro is in what continent?
gold: europe
reply: Montenegro is in Europe.

t0088673 | mode=answer | Date of birth for Taejong of Joseon?
gold: 1367-6-13
reply: Taejong of Joseon was born on june 13, 1367.

t0030955 | mode=answer | joplni is in what sate?
gold: missouri
reply: That isn't in my offline knowledge. The closest match I have is Janis Joplin, a person, singer-songwriter. Is that who or what you mean?

t0139972 | mode=answer | Population of Moncada?
gold: 21,900
reply: As of 2025, the population of Moncada is 21,900.

t0182859 | mode=answer | which american author created the character rip van winkle?
gold: washington irving
reply: The director of rip van winkle isn't in my offline knowledge, but rip van winkle is a short story by american author washington irving.

t0058808 | mode=answer | luke haines's musical genre lol
gold: alternative rock
reply: Luke Haines is known for alternative rock.

t0052429 | mode=either | who wrote devil may cate, a james bond novel, at the request of the trustees of the estate of original 007 author ian fleking i forgot
gold: sebastian faulks
reply: I don't have devil may cate, a james bond novel, at the request of the estate of original 007 in my offline knowledge. Could you check?

t0136894 | mode=either | what is alfs real first name on the popular sitcom?
gold: gordon
reply: That isn't in my offline knowledge. The closest match I have is Alf Ramsey, a person, right-back. Is that who or what you mean?

t0128553 | mode=answer | I'm based in Nairobi. // What year did Dorothea Puente come into the world? // hey turbo, whih city did i say i live in?
gold: nairobi
reply: You told me you live in nairobi.

t0007112 | mode=fallback | joseph w. sarno's nationality?
gold: american
reply: The nationality of Joseph W. Sarno isn't in my offline knowledge, but Joseph W. Sarno was born in Brooklyn, New York, U. S..

t0124376 | mode=fallback | Helen Carter: year of birth?
gold: 1927
reply: The date of birth of Helen Carter isn't in my offline knowledge, but Helen Carter is a american country music singer.

t0138997 | mode=answer | On the field, what was Fabien Barthez's position?
gold: goalkeeper
reply: Fabien Barthez played as a goalkeeper.

t0131831 | mode=answer | On which continent is the city of Yongjing?
gold: asia
reply: Yongjing is in Taiwan, which is in Asia.

t0128467 | mode=answer | A hagiographa is a type of what?
gold: sacred text / sacred writing / religious writing
reply: A hagiographa is a type of sacred text.

t0001718 | mode=either | lady jane grey died in 1554 from typhoid fever.
gold: {"answer": "no"} [yesno]
reply: Lady Catherine Grey died on january 26, 1568.

t0038502 | mode=either | how may of cormac mccarthy's books won a pulitzer prize?
gold: 1
reply: That isn't in my offline knowledge. The closest match I have is Joseph Mccarthy, a american politician. Is that who or what you mean?

t0155129 | mode=answer | Do you know who Giles Coke was?
gold: english footballer
reply: Giles Coke was a english footballer.

t0141732 | mode=answer | Who was the director of The Producers?
gold: mel brooks
reply: The director of the producers is Mel Brooks.

t0108191 | mode=answer | Terry Lester: year of birth?
gold: 1950
reply: Terry Lester was born in 1950.

t0060052 | mode=answer | Which US state is Santa Monica in?
gold: california
reply: Santa Monica is in California.

t0171836 | mode=answer | quick question, does the country Azerbaijan have a coastline, or is it landlocked?
gold: yes / landlocked
reply: Yes, Azerbaijan has no coastline.

t0014644 | mode=fallback | Which position did Mathieu Schneider play?
gold: defense
reply: The position of Mathieu Schneider isn't in my offline knowledge, but Mathieu Schneider is a american former professional ice hockey player.

t0013153 | mode=answer | How populated is Ndioum?
gold: 20,270
reply: As of 2025, Ndioum has about 20,270 people.

t0112349 | mode=answer | On which continent is the city of Senador Jose Porfirio?
gold: south america
reply: Senador Jose Porfirio is in Brazil, which is in South America.

t0182239 | mode=answer | IN WHAT COUNTRY WAS TWIGGY BORN?
gold: england
reply: Which Derek Twigg do you mean: the british labour party politician or the british labour and co-operative?

t0142118 | mode=fallback | Who will win the 2034 World Cup?
gold: {} [none]
reply: I can't know the future. Is there a past result I can look up for you?

t0176623 | mode=clarify_or_likeliest | roughly how many people are in duncan?
gold: candidates: ['city:4535389', 'city in oklahoma']; ['city:5943865', 'city in canada']
reply: Which Duncan do you mean: the city in oklahoma or the city in canada?

t0039516 | mode=answer | Was Hogfather or Tigana published earlier?
gold: {"answer": ["tigana"], "other": ["hogfather"]} [choice]
reply: Tigana came out first, in 1990; Hogfather came out in 1996.

t0189531 | mode=answer | real quick what will da date be 135 days from today
gold: {"result": "monday, february 15, 2027", "call": "date_add 135 days"} [tool]
reply: The answer is monday, february 15, 2027.

t0118623 | mode=answer | do u know ricardo oliveira's date of birth?
gold: 1980-5-6
reply: Ricardo Oliveira was born on may 6, 1980.

t0191000 | mode=clarify_or_likeliest | which country is waterloo in?
gold: candidates: ['city:6176823', 'city in canada']; ['city:4880889', 'city in iowa']; ['city:2403094', 'city in sierra leone']
reply: Which waterloo do you mean: the 1970 epic period war film or the city in canada?

t0012678 | mode=answer | On what date did Syl Apps die? // and when were they born?
gold: 1915-1-18
reply: Syl Apps was born on january 18, 1915.

t0114506 | mode=answer | Which symbol does Antimony have on the periodic table? // And for Yttrium?
gold: y
reply: Yttrium's chemical symbol is y.

t0098361 | mode=answer | what is the population of cocos (keeling) islands's capital?
gold: 120
reply: West Island has a population of 120 as of 2025.

t0075135 | mode=answer | Which year is Mary Young Pickersgill's birth year?
gold: 1776
reply: Mary Young Pickersgill was born in 1776.

t0026887 | mode=answer | In what year did da US state of New York join the union
gold: 1788
reply: New York joined the union in 1788.

t0102235 | mode=either | which of the great lakes do not share a border new york?
gold: lake huron / lake michigan / lake superior
reply: I don't have the great lakes do not share in my offline knowledge. Could you check the spelling or give me more detail?

t0055656 | mode=answer | Kevin Kyle: year of birth?
gold: 1981
reply: Kevin Kyle was born in 1981.

t0040187 | mode=answer | What year did Two-Bits Homan come into the world?
gold: 1898
reply: Two-Bits Homan's birth year is 1898.

t0006874 | mode=answer | Who performed Tell All Yoour Friends pls
gold: taking back sunday
reply: Which tell all your friends do you mean: the thing or the book by avery monsen?

t0033912 | mode=answer | What is 180 divided by 36
gold: {"result": "5", "call": "calc 180/36"} [tool]
reply: The answer is 5.

t0053881 | mode=either | what year did ernest hemingway write the old man and the sea?
gold: 1952
reply: Ernest Hemingway passed away in 1961.

t0070567 | mode=answer | WHICH DATE IS IT TODAY
gold: {"result": "tuesday, november 12, 2024", "call": "date"} [tool]
reply: It's tuesday, november 12, 2024.

t0098684 | mode=fallback | WHAT'S THE DEFINITION OF DOWNSHIFT
gold: a change from a financially rewarding but stressful career t
reply: I don't have downshift's definition in my offline knowledge. Is there something else about downshift I can look up?

t0114410 | mode=answer | which year is heln berman's birth year?
gold: 1936
reply: That isn't in my offline knowledge. The closest match I have is Helen Berman, a dutch-israeli visual artist. Is that who or what you mean?

t0158905 | mode=answer | Neuromancer by William Gibson was first published in which year
gold: 1984
reply: Neuromancer was published in 1984.

t0086646 | mode=answer | what major language is one of the official languages in new zealand?
gold: english
reply: New Zealand's official languages are English, Maori and New Zealand Sign Language.

t0086431 | mode=answer | Do you know John Ray, the english naturalist's nationality?
gold: english
reply: John Ray is English.

t0118520 | mode=answer | Date of death of Khalil Ibrahim?
gold: 2011-12-23
reply: Khalil Ibrahim's date of death is december 23, 2011.

t0156302 | mode=answer | Who was born first, Paulo Costanzo or Danny Garcia?
gold: {"answer": ["danny garcia"], "other": ["paulo costanzo"]} [choice]
reply: Danny Garcia was born first, on april 29, 1954; Paulo Costanzo was born on september 21, 1978.

t0059206 | mode=answer | On what continent would I find the country Guinea? // hi how about Cameroon
gold: africa
reply: The official languages of Cameroon isn't in my offline knowledge, but Cameroon is in Africa.

t0159330 | mode=clarify_or_likeliest | HOW POPULATED IS BELIZE
gold: candidates: ['country:BLZ', 'country']; ['city:2243646', 'city in angola']
reply: Which Belize do you mean: the country or the city in angola?

t0177023 | mode=answer | I'm based in Austin. // Do you know where Hank Patterson died? // What category does a detergency belong to? // Where am I based?
gold: austin
reply: I don't know that, since you haven't told me. Can you tell me?

t0187316 | mode=answer | Is the country Tonga or United Kingdom larger in area?
gold: {"answer": ["united kingdom", "great britain", "united kingdom of great britain  [choice]
reply: United Kingdom is bigger: 242,900 square kilometres against 747 square kilometres for Tonga.

t0193657 | mode=either | WHIH THOR MOVIE FROM THE ORIGINAL TRILOGY DOES NOT STAR NATALIE PORTMAN
gold: thor: ragnarok
reply: I don't have not star natalie portman in my offline knowledge. Could you check the spelling or give me more detail?

t0162624 | mode=fallback | What kind of work did Richard Jacques do?
gold: composer
reply: Richard Jacques is known for orchestral.

t0049989 | mode=answer | date of birth for les dennis?
gold: 1953-10-12
reply: Les Dennis was born on october 12, 1953.

t0138382 | mode=answer | What was Carl Wilson's job?
gold: musician
reply: Carl Wilson worked as a musician.

t0170738 | mode=answer | WHICH YEAR IS HUGH PADGHAM'S BIRTH YEAR
gold: 1955
reply: Hugh Padgham was born in 1955.

t0048783 | mode=answer | Toss a coin.
gold: {"valid": ["heads", "tails"]} [random]
reply: The coin landed on tails.

t0103907 | mode=answer | Which languages are official in Peru?
gold: aymara, quechua, spanish
reply: Peru's official languages are Aymara, Quechua and Spanish.

t0126570 | mode=answer | My job is baker. // Birthplace of Rosalind Franklin, the english chemist and x-ray crystallographer? // Manganese sits in what period? // Wyat's my job ahain?
gold: baker
reply: I don't know that, since you haven't told me. Can you tell me?

t0007591 | mode=fallback | REAL QUICK: IS IT RAINING IN JALGAON TODAY?
gold: {} [none]
reply: I can't check live weather offline. What I do know: Jalgaon is in India.

t0062780 | mode=answer | What's the time right now?
gold: {"result": "1:36 pm", "call": "time"} [tool]
reply: It's 1: 36 pm.

t0138916 | mode=answer | How old was Violet Trefusis when tey diied
gold: 77
reply: Violet Trefusis was 77 years old when they died.

t0165978 | mode=answer | What school did Mary Harney graduate from?
gold: trinity college
reply: Mary Harney studied at Trinity College.

t0016968 | mode=either | what to see and do in revelstoke?
gold: kinbasket lake
reply: Revelstoke Airport is located in Canada.

t0177267 | mode=fallback | Which position did Santiago Solari play?
gold: midfielder
reply: The position of Santiago Solari isn't in my offline knowledge, but Santiago Solari is a argentine retired footballer.

t0188898 | mode=answer | Who is Hans Hartung?
gold: german-french painter
reply: Hans Hartung was a german-french painter.

t0066045 | mode=answer | Author of Going Bovine?
gold: libba bray
reply: The author of Going Bovine is Libba Bray.

t0081782 | mode=answer | What day of the week is August 1, 2003?
gold: {"result": "friday", "call": "weekday 2003-08-01"} [tool]
reply: The answer is friday.

t0059192 | mode=answer | Madison Grant's profession?
gold: lawyer
reply: Madison Grant worked as a lawyer.

t0110512 | mode=answer | Multiply 797 by 402 for me.
gold: {"result": "320394", "call": "calc 797*402"} [tool]
reply: The answer is 320394.

t0174864 | mode=answer | What line of work was Mark van Doren in?
gold: poet
reply: Mark van Doren worked as a poet.

t0167373 | mode=answer | What day of the week is July 12, 1970?
gold: {"result": "sunday", "call": "weekday 1970-07-12"} [tool]
reply: The answer is sunday.

t0042240 | mode=either | how old was albert einstein when he died?
gold: 76
reply: Albert Einstein was 76 years old when they died.

t0177049 | mode=answer | What do you get if you add 38220 and 1067?
gold: {"result": "39287", "call": "calc 38220+1067"} [tool]
reply: The answer is 39287.

t0060324 | mode=answer | What's San Javier Airport's elevation in meters?
gold: 518.7696 metres
reply: San Javier Airport is 1,702 feet, which is 518.7696 meters.

t0072852 | mode=answer | Wat exactly is Prodution Theory?
gold: study of production
reply: That isn't in my offline knowledge. The closest match I have is production theory, a study of production. Is that who or what you mean?

t0174905 | mode=answer | Spell lighthouse letter by letter.
gold: {"result": "l-i-g-h-t-h-o-u-s-e", "call": "spell lighthouse"} [tool]
reply: I don't have spell lighthouse letter of letter in my offline knowledge. Could you check the spelling or give me more detail?

t0036535 | mode=answer | Roll a six-sided die for me.
gold: {"valid": ["1", "2", "3", "4", "5", "6"]} [random]
reply: It's a 5.

t0195301 | mode=clarify_or_likeliest | What's the elevation of Las Brujas Airport?
gold: candidates: ['airport:BWW', 'airport in cayo santa maria']; ['airport:CZU', 'airport in corozal']
reply: Which Las Brujas Airport do you mean: the airport in cayo santa maria or the airport in corozal?

t0079883 | mode=either | the surname eriksson is in the top 5 of the mst common names in which european ciuntry
gold: sweden
reply: That isn't in my offline knowledge. The closest match I have is Sven-Goran Eriksson, a person, right back. Is that who or what you mean?

t0159714 | mode=clarify | WHEN DID SHE DIE?
gold: {} [none]
reply: Which one do you mean? Can you give me the name?

t0038170 | mode=fallback | Birthplace of Evelyn Beatrice Longman?
gold: winchester, ohio / winchester
reply: The birthplace of Evelyn Beatrice Longman isn't in my offline knowledge, but Evelyn Beatrice Longman was born on november 21, 1874.

t0118240 | mode=answer | How many days are left until June 20, 2027?
gold: {"result": "450 days", "call": "days_until 2027-06-20"} [tool]
reply: That's 450 days.

t0168509 | mode=answer | Is an atom of Manganese or Dysprosium heavier?
gold: {"answer": ["dysprosium"], "other": ["manganese"]} [choice]
reply: Dysprosium is heavier: 162.5 against 54.938 for manganese.

t0099711 | mode=fallback | Who exactly is Mark Benton?
gold: english actor
reply: The description of Mark Benton isn't in my offline knowledge, but Mark Benton worked as a actor.

t0082803 | mode=either | in what year did the assyrian empire fall?
gold: 612
reply: I don't have empire's founding year in my offline knowledge. Is there something else about empire I can look up?

t0172280 | mode=answer | What language is official where Khlong Yai is?
gold: thai
reply: Khlong Yai is in Thailand, where the official language is Thai.

t0020490 | mode=answer | IS A LEIOPELMA A KIND OF TAXONOMIC GROUP?
gold: {"answer": "yes"} [yesno]
reply: Yes, a leiopelma is a kind of taxonomic group.

t0170027 | mode=fallback | What happened in the news today?
gold: {} [none]
reply: I can't see today's news offline. Is there a topic you'd like facts about?

t0105001 | mode=answer | Does Fermium or Indium have more protons?
gold: {"answer": ["fermium"], "other": ["indium"]} [choice]
reply: Fermium is heavier: 257 against 114.818 for indium.

t0131408 | mode=answer | Raise 2 to the 4th power.
gold: {"result": "16", "call": "calc 2^4"} [tool]
reply: The answer is 16.

t0068591 | mode=either | which book in da percy jackson book series was released in 2006
gold: the sea of monsters
reply: I don't have jackson book series in my offline knowledge. Could you check the spelling or give me more detail?

t0013489 | mode=answer | yo whats 17.5% of 2693?
gold: {"result": "471.275", "call": "pct_of 17.5 2693"} [tool]
reply: That's 471.275.

t0094712 | mode=answer | International dialing code of the country Congo?
gold: +242
reply: Congo's dialing code is + 242.

t0157219 | mode=either | which musical featured the song thank heaven for little girls?
gold: gigi
reply: I don't have musical featured heaven in my offline knowledge. Could you check the spelling or give me more detail?

t0143251 | mode=answer | How many people live in the capital city of Mauritania?
gold: 1,184,530
reply: Nouakchott has a population of 1,184,530 as of 2025.

t0077629 | mode=answer | WHCH OFFICIAL LANGUAGE DOES THE COUNTRY OF GREER USE?
gold: english
reply: Greer is in United States, where the official language is English.

t0019209 | mode=answer | Which political party was Theo Waigel in?
gold: christian social union
reply: Theo Waigel belonged to the Christian Social Union party.

t0161470 | mode=answer | who directed the 1963 film the birds?
gold: alfred hitchcock
reply: That isn't in my offline knowledge. The closest match I have is action film, a genre. Is that who or what you mean?

t0089691 | mode=answer | Three-letter code of Toledo Executive Airport?
gold: tdz
reply: Toledo Executive Airport's airport code is tdz.

t0010874 | mode=answer | Andrejs Rubins was born where?
gold: riga, latvian ssr, soviet union / riga
reply: Andrejs Rubins was born in Riga, Latvian Ssr, Soviet Union.

t0100131 | mode=fallback | How much is one ethereum worth today?
gold: {} [none]
reply: I can't see live prices offline. Is there something else about money or markets I can explain?

t0082854 | mode=answer | WHICH ELEMENT HAS THE HIGHR ATOMIC NUMBER, YTTRIUM OR THE ELEMENT BARIUM?
gold: {"answer": ["barium"], "other": ["yttrium"]} [choice]
reply: Barium has the higher atomic number: 56 against 39 for yttrium.

t0033317 | mode=answer | What's 118 times 464?
gold: {"result": "54752", "call": "calc 118*464"} [tool]
reply: The answer is 54752.

t0048738 | mode=either | what late night television host was born in corning, iowa?
gold: johnny carson
reply: I don't have Iowa's birthplace in my offline knowledge. Is there something else about Iowa I can look up?

t0013866 | mode=answer | In what year was Modern Lovers published?
gold: 2016
reply: Modern Lovers came out in 2016.

t0096151 | mode=answer | What day of da week is January 10, 1982?
gold: {"result": "sunday", "call": "weekday 1982-01-10"} [tool]
reply: The answer is sunday.

t0110361 | mode=answer | What's the greatest common divisor of 183 and 105?
gold: {"result": "3", "call": "gcd 183 105"} [tool]
reply: The answer is 3.

t0105077 | mode=answer | I'm based in Chiang Mai. // Place of death of Francis Hay, 9th Earl of Erroll? // Which country was Solomon Marcus a citizen of? // WHERE AM I BASED?
gold: chiang mai
reply: I don't know that, since you haven't told me. Can you tell me?

t0025686 | mode=answer | IN WHAT YEAR WAS THE AUTHOR OF LA CONFIDENTIAL BY JAMES ELLROY BORN PLS
gold: 1948
reply: That isn't in my offline knowledge. The closest match I have is confidential, a magazine. Is that who or what you mean?

t0180762 | mode=answer | What's 15% of 541? // NOW DO 30%.
gold: {"result": "162.3", "call": "pct_of 30 541"} [tool]
reply: That's 162.3.

t0172784 | mode=answer | What is 45% of 1729?
gold: {"result": "778.05", "call": "pct_of 45 1729"} [tool]
reply: That's 778.05.

t0070065 | mode=answer | In what place was Harmon Killebrew born?
gold: payette, idaho / payette
reply: Harmon Killebrew was born in Payette, Idaho.

t0023438 | mode=either | name samuel coleridges longest poem which contains da lines:
gold: the rime of the ancient mariner
reply: That isn't in my offline knowledge. The closest match I have is Samuel Coleridge-Taylor, a english composer of creole descent. Is that who or what you mean?

t0039845 | mode=fallback | Birthplace of John Mica?
gold: binghamton, new york, u.s. / binghamton
reply: The birthplace of John Mica isn't in my offline knowledge, but John Mica was born on january 27, 1943.

t0119555 | mode=either | IS JK ROWLING OLDER THAN MARGARET ATWOOD
gold: {"answer": "no"} [yesno]
reply: That isn't in my offline knowledge. The closest match I have is J. K. Rowling, a british novelist. Is that who or what you mean?

t0080399 | mode=answer | Space Coast Regional Airport elevation?
gold: 34 feet
reply: The elevation of Space Coast Regional Airport is 34 feet.

t0064067 | mode=answer | What style of music is Gary Valenciano known for?
gold: inspirational
reply: Gary Valenciano is known for inspirational.

t0044812 | mode=either | for which of the movies listed below did steven spielberg win oscars for best director
gold: schindlers list and saving private ryan
reply: I don't have that about Steven Spielberg in my offline knowledge. What I do know: Steven Spielberg was born on december 18, 1946.

t0189736 | mode=answer | On which continent is the city of Sambalpur?
gold: asia
reply: Sambalpur is in India, which is in Asia.

t0171343 | mode=fallback | Who was Phil Collins thx
gold: english singer
reply: I don't have that about Phil Collins in my offline knowledge. What I do know: Phil Collins was born on january 30, 1951.

t0133695 | mode=answer | percent change from 344 to 820?
gold: {"result": "an increase of 138.372093%", "call": "pct_change 344 820"} [tool]
reply: That's an increase of 138.372093%.

t0173304 | mode=answer | Succubus on Top was first published in which year? // And for Beyond the Highland Mist?
gold: 1999
reply: Beyond the Highland Mist was published in 1999.

t0133553 | mode=clarify_or_likeliest | faridpur is located in which country?
gold: candidates: ['city:1203344', 'city in bangladesh']; ['city:1271947', 'city in india']
reply: Faridpur is in India.

t0173221 | mode=answer | population of jaiba asap
gold: 37,660
reply: As of 2025, the population of Jaiba is 37,660.

t0180953 | mode=answer | What's 209 times 936?
gold: {"result": "195624", "call": "calc 209*936"} [tool]
reply: The answer is 195624.

t0184502 | mode=answer | My job is teacher. // What's my job again?
gold: teacher
reply: I don't know that, since you haven't told me. Can you tell me?

t0115581 | mode=answer | Who performed Like a Prayer (song)?
gold: madonna
reply: I don't have like a prayer's founding year in my offline knowledge. Is there something else about like I can look up?

t0033522 | mode=answer | Soummam Airport is in a country whose capital is what?
gold: algiers
reply: Soummam Airport is in Algeria, and the capital of Algeria is Algiers.

t0097416 | mode=answer | Count the letters in pineapple.
gold: {"result": "9", "call": "count_letters pineapple"} [tool]
reply: 9.

t0092378 | mode=answer | Joe Delaney died where?
gold: monroe, ouachita parish louisiana / monroe
reply: Joe Delaney died in Monroe, Ouachita Parish Louisiana.

t0062140 | mode=clarify_or_likeliest | hamlet rrlease yera
gold: candidates: ['wk:Hamlet (1948 film)', '1948 film']; ['wk:Hamlet (1996 film)', "1996 film adaptation of william shakespeare's play hamlet"]
reply: That isn't in my offline knowledge. The closest match I have is hamlet, a tragedy. Is that who or what you mean?

t0146518 | mode=answer | Who was Luis Gutierrez?
gold: american politician
reply: I don't have that about Luis Gutierrez in my offline knowledge. What I do know: Luis Gutierrez is a american politician.

t0099512 | mode=answer | Is Tikhvin or Vila Leopoldina more populous?
gold: {"answer": ["tikhvin"], "other": ["vila leopoldina"]} [choice]
reply: Tikhvin has more people: 62,075 against 46,875 for Vila Leopoldina.

t0060409 | mode=answer | Political party of The Earl of Godolphin?
gold: tory
reply: Sidney Godolphin, 1 St Earl of Godolphin belonged to the Tory party.

t0076929 | mode=fallback | what's the score of the match going on now?
gold: {} [none]
reply: I can't follow live games offline. Which team are you asking about?

t0002868 | mode=answer | Who is the author of Instructions for a Heatwave? // how about pleasure unbound
gold: larissa ione
reply: Pleasure Unbound was written by Larissa Ione.

t0192987 | mode=fallback | ok so what's the scre of the mathc going on now?
gold: {} [none]
reply: I don't have the mathc going on now in my offline knowledge. Could you check the spelling or give me more detail?

t0117798 | mode=either | in fallout, is frank horrigan a human?
gold: {"answer": "no"} [yesno]
reply: That isn't in my offline knowledge. The closest match I have is Anne Frank, a german-born diarist and writer. Is that who or what you mean?

t0010302 | mode=answer | Brainerd Lakes Regional Airport is in a country whose capital is what?
gold: washington d.c.
reply: Brainerd Lakes Regional Airport is in United States, and the capital of United States is washington d. C..

t0057552 | mode=answer | Roughly how many people are in Kamina?
gold: 200,184
reply: As of 2025, the population of Kamina is 200,184.

t0108824 | mode=answer | A kettle is a type of what?
gold: pot
reply: That isn't in my offline knowledge. The closest match I have is kettle valley railway, a subsidiary of the canadian pacific railway. Is that who or what you mean?

t0135656 | mode=answer | 351 pous 3902 equals what just curious
gold: {"result": "4253", "call": "calc 351+3902"} [tool]
reply: The answer is 4253.

t0027490 | mode=answer | What's 30% of 765? // i was wondering, now do 15%.
gold: {"result": "114.75", "call": "pct_of 15 765"} [tool]
reply: That's 114.75.

t0184863 | mode=fallback | Do you know Majaz Lakhnawi's date of birth?
gold: 1911-10-19
reply: The date of birth of Majaz lakhnawi isn't in my offline knowledge, but Majaz was born in Bara Banki, Up, India.

t0097912 | mode=answer | How many countriws dose the country Bermuda border
gold: 0
reply: Bermuda doesn't border any other country.

t0063510 | mode=answer | which money do they use in sungai lalang?
gold: malaysian ringgit
reply: Sungai Lalang is in Malaysia, which uses the malaysian ringgit.

t0166906 | mode=fallback | What is Nvidia's share price today?
gold: {} [none]
reply: I can't see live stock prices offline. Would you like facts about nvidia instead?
