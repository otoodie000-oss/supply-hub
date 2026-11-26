# TurboX 1M test: 20 random samples per category

Drawn from shards 00-03 with seed 7 after the freeze (results/test_freeze.json). Gold shown compactly.


## kb_fact

| id | sub | question | expected | messy |
|---|---|---|---|---|
| t0105954 | occupation | Rosemary Sutcliff's profession? | writer (answer) |  |
| t0049330 | group | What group does the element Chlorine belong to on the periodic table | 17 (answer) | nopunct |
| t0129165 | death_date | what year did daniel carleton gajdusek psss away? | 2008 (answer) | typo,lower |
| t0015867 | borders | The country Reunion bordes which countries? | none / no countries / no neighbo (answer) | typo |
| t0023897 | occupation | WHAT WAS HUGH HUDSON'S JOB? | director (answer) | caps |
| t0175597 | nationality | What nationality was David Mumford? | american (answer) |  |
| t0030879 | nationality | Carsten Niebuhr's nationality? | german (answer) |  |
| t0119646 | region | Benin is in which subregion? | western africa (answer) |  |
| t0190908 | is_a | What category does a wisp belong to | tuft / tussock (answer) | nopunct |
| t0019021 | birth_place | Where's Rodolphe Lemieux's birthplace? | montreal, canada east / montreal (answer) |  |
| t0166077 | death_place | Do you know where Don Lawrence died? | jevington, england / jevington (answer) |  |
| t0069987 | occupation | WHAT KIND OF WORK DID MARIEL HEMINGWAY DO? | actress (answer) | caps |
| t0012328 | region | What region of da world is the countty Thailand in? | south-eastern asia (answer) | typo,slang |
| t0028264 | elevation | How high above sea level is Salem Airport? | 1,008 feet (answer) |  |
| t0142077 | death_date | 2nd Dalai Lama died in which year? | 1542 (answer) |  |
| t0136994 | country | which country is teshi old town in? | ghana / republic of ghana (answer) | lower |
| t0023022 | death_place | Where did Adnan Gulshair El Shukrijumah pass away? | s. waziristan, fata, pakistan / s. waziristan (answer) |  |
| t0078475 | director | Who was the director of Mississippi Burning? | alan parker (answer) |  |
| t0029826 | founded_year | What year was Aberystwyth University established? | 1872 (answer) |  |
| t0180551 | position | Which position did Lou Saban play? | linebacker (answer) |  |

## derived

| id | sub | question | expected | messy |
|---|---|---|---|---|
| t0093005 | compare_elevation | Which airport sits higher, Labo Airport or Danbury Municipal Airport just curious | {"answer": ["danbury municipal airport", "dxr airport"], "other": ["labo airport [choice] (answer) | filler |
| t0012862 | age_at_death | At what age did Eugene Thomas Maleska die? | 77 (answer) |  |
| t0180942 | pop_of_largest_city | What's the population of the US state of New Hampshire's biggest city? | 110,229 (answer) |  |
| t0124065 | birth_weekday | WHAT DAY OF DA WEEK WAS BEV DESJARLAIS BORN ON? | friday (answer) | slang,caps |
| t0026860 | pop_of_largest_city | What's the population of the US state of California's biggest city? | 3,820,914 (answer) |  |
| t0048907 | pop_of_largest_city | what's the population of the us state of massachusetts's biggest city? | 653,833 (answer) | lower |
| t0138100 | compare_died | Which of them passed away earlier, James Buchanan Eads or Rochus Misch? | {"answer": ["james buchanan eads"], "other": ["rochus misch"]} [choice] (answer) |  |
| t0137354 | isa | Is a submarine ball a kind of ordering? | {"answer": "no"} [yesno] (answer) |  |
| t0127723 | convert_elev_m | What's Zahedan International Airport's elevation in meters? | 1391.1072 metres (answer) |  |
| t0013515 | author_birth_place | The writer of Dragonfly in Amber was born where? | arizona, u.s. / arizona (answer) |  |
| t0126545 | convert_diameter_mi | How many miles across is Saturn? | 72364.889 miles (answer) |  |
| t0128251 | compare_elevation | WHICH AIRPORT SITS HIGHER ESPERADINHA AIRPORT OR MOUNT VERNON AIRPORT | {"answer": ["mount vernon airport", "mvn airport"], "other": ["esperadinha airpo [choice] (answer) | nopunct,caps |
| t0087022 | age_at_death | At what age did Roscoe Lee Browne die? | 84 (answer) |  |
| t0010822 | capital_of_country_of_city | What's the capital of the country that Tabuk in Saudi Arabia is in? | riyadh (answer) |  |
| t0048431 | count_languages | United States Minor Outlying Islands has how many official languages | 1 (answer) | nopunct |
| t0010138 | population_of_capital | What is the population of Bahamas's capital? | 227,940 (answer) |  |
| t0121988 | isa | IS EVERY SOCIALISM A PLEASURE? | {"answer": "no"} [yesno] (answer) | caps |
| t0188144 | isa | IS EVERY LEGAL HOLIDAY A CALENDAR DAY | {"answer": "yes"} [yesno] (answer) | nopunct,caps |
| t0028933 | convert_elev_m | How high is Sasstown Airport in metres? | 1.8288 metres (answer) |  |
| t0063853 | author_birth_year | IN WHAT YEAR WAS DA AUTHOR OF THE ELFSTONES OF SHANNARA BY TERYR BROOKS BORN? | 1944 (answer) | typo,slang,caps |

## tool

| id | sub | question | expected | messy |
|---|---|---|---|---|
| t0091445 | lcm | Smallest number divisible by both 156 and 5? | {"result": "780", "call": "lcm 156 5"} [tool] (answer) |  |
| t0031486 | words | How do u write 234922 in words | {"result": "two hundred thirty-four thousand nine hundred twenty-two", "call": " [tool] (answer) | slang,nopunct |
| t0117313 | gcd | What's the greatest common divisor of 137 and 50? | {"result": "1", "call": "gcd 137 50"} [tool] (answer) |  |
| t0025764 | date | wht is today's date? | {"result": "thursday, january 8, 2026", "call": "date"} [tool] (answer) | typo,lower |
| t0124121 | time | What's the time right now? | {"result": "10:44 pm", "call": "time"} [tool] (answer) |  |
| t0066797 | calc_pow | What's 8 to the power of 5? | {"result": "32768", "call": "calc 8^5"} [tool] (answer) |  |
| t0121764 | world_time | What time is it in Manila at da moment | {"result": "10:47 pm, tuesday", "call": "world_time manila"} [tool] (answer) | slang,nopunct |
| t0177871 | count_letter | count the r's in dinosaur. | {"result": "1", "call": "count_letter r dinosaur"} [tool] (answer) | lower |
| t0148347 | tip | HOW MUCH SHOULD I TIP ON 241 DOLLARS AT 22 PERCENT? | {"result": "tip 53.02, total 294.02", "call": "tip 22 241"} [tool] (answer) | caps |
| t0039174 | calc_add | 26263 plus 5704 equals what? | {"result": "31967", "call": "calc 26263+5704"} [tool] (answer) |  |
| t0022260 | calc_div | divide 5952 by 24 i forgot | {"result": "248", "call": "calc 5952/24"} [tool] (answer) | filler,nopunct,lower |
| t0126588 | gcd | Highest common factor of 150 and 45? | {"result": "15", "call": "gcd 150 45"} [tool] (answer) |  |
| t0124164 | count_letters | How many letters does the word volcano have? | {"result": "7", "call": "count_letters volcano"} [tool] (answer) |  |
| t0139090 | convert | How many centimeters are in 307 inches? | {"result": "779.78 centimeters", "call": "convert 307 in cm"} [tool] (answer) |  |
| t0040659 | calc_div | WHT IS 5760 DIVIDDE BY 36? | {"result": "160", "call": "calc 5760/36"} [tool] (answer) | typo,caps |
| t0080969 | from_roman | Convert MMLV from Roman numerals | {"result": "2055", "call": "roman mmlv"} [tool] (answer) | nopunct |
| t0020968 | convert | How many minutes are in 369 hours? | {"result": "22140 minutes", "call": "convert 369 hr min"} [tool] (answer) |  |
| t0118904 | words | Spell out the number 207241 in words. | {"result": "two hundred seven thousand two hundred forty-one", "call": "words 20 [tool] (answer) |  |
| t0155139 | convert | ok so convert 56 pounds into kilograms. | {"result": "25.4012 kilograms", "call": "convert 56 lb kg"} [tool] (answer) | filler,lower |
| t0013612 | convert | Convert 43 centimetres ino inches pls | {"result": "16.9291 inches", "call": "convert 43 cm in"} [tool] (answer) | typo,filler |

## real

| id | sub | question | expected | messy |
|---|---|---|---|---|
| t0183649 | freebaseqa | in wihch country are the angel falks, or kerepakupai ven? | venezuela (either) | typo |
| t0019082 | opentriviaqa | having played only one season in the majors with the 1959 phillies, this player, popularly known as sparky, later made his mark as a manager. | george anderson (either) |  |
| t0066671 | webquestions | what team did howie long? | villanova wildcats football / oakland raiders (either) | lower |
| t0161722 | freebaseqa | WHAT MODERN WITCHCRAFT RELIGION WAS INVENTED BY GERALD GARDNER? | wicca (either) | caps |
| t0173545 | mintaka | how many books are there in a discovery of witches series? | 3 (either) |  |
| t0139649 | freebaseqa | which peninsular on the south coast of glamorgan in wales was the first area of the united kingdom to be designated as an 'area of outstanding natural beauty'? | gower peninsula (either) |  |
| t0102812 | opentriviaqa | what was the name of the first husband of queen elizabeth i of england? | none of these (either) |  |
| t0151547 | opentriviaqa | SHE POSED HERSELF AS A PRINCESS FROM JAVA AND HER STAGE-NAME MEANT "SUN" OR "EYE OF THE DAWN" | mata hari (either) | nopunct,caps |
| t0190596 | opentriviaqa | in what language do ethiopian jews read torah? | gez (either) |  |
| t0147651 | freebaseqa | who preceded george w bush as president of da usa? | bill clinton (either) | slang,lower |
| t0118357 | opentriviaqa | IN 1943, GENERAL FRIEDRICH PAULUS WAS IN CHARGE OF THE GERMAN FORCES IN WHICH AREA? | caucasus (either) | caps |
| t0098524 | webquestions | where did apostle paul grow up? | tarsus, mersin (either) |  |
| t0081143 | opentriviaqa | hey so this play was written by shakespeare on the request of queen elizabeth i. | the merry wives of windsor (either) | filler |
| t0058224 | freebaseqa | in which us city do the 'yankees' play their baseball pls | new york (either) | filler,nopunct |
| t0079804 | mintaka | when was the fifth u.s. president born? | 1758-04-28 (either) |  |
| t0026014 | mintaka | was bad boys for life released the same year as birds of prey? | {"answer": "yes"} [yesno] (either) |  |
| t0186687 | opentriviaqa | what actor stars as retired jewel thief opposite grace kelly in alfred hitchcocks romantic thriller to catch a thief? | cary grant (either) |  |
| t0098665 | freebaseqa | who played the title role in the 2004 film the life and death of peter sellers? | geoffrey rush (either) |  |
| t0171255 | mintaka | how many olympic medals does michael phelps have that are not silver or bronze? | 23 (either) |  |
| t0161227 | webquestions | where did they find jenni rivera's body? | iturbide, nuevo leon (either) | lower |

## withheld

| id | sub | question | expected | messy |
|---|---|---|---|---|
| t0112809 | withheld:country | ADROGUE IS LOCATED IN WHICH COUNTRY? | argentina / argentine republic / republica argentina (fallback) | caps |
| t0146906 | withheld:birth_place | random question but birthplace of Corky Ballas? | houston, texas, u.s. / houston (fallback) | filler |
| t0094557 | unknowable:private | Where does John Worsfold live exactly, street address? | {} [none] (fallback) |  |
| t0199613 | withheld:birth_date | On what date was Jonas Mekas born? | 1922-12-24 (fallback) |  |
| t0024437 | withheld:birth_date | dave spitz was born on wich day? | 1958-2-22 (fallback) | typo,lower |
| t0039514 | withheld:birth_place | In what place was Antoine Blanc born? | sury-le-comtal, rhone-et-loire, france / sury-le-comtal (fallback) |  |
| t0168298 | withheld:party | what party did bob inglis represent? | republican (fallback) | lower |
| t0136622 | withheld:country | In which nation is Volta Redonda? | brazil / brasil / federative republic of brazil (fallback) |  |
| t0055400 | unknowable:news | What happened in the news today? | {} [none] (fallback) |  |
| t0112409 | withheld:publication_year | What year did The Battle for Skandia come out? | 2006 (fallback) |  |
| t0050815 | withheld:occupation | What line of work was Mehmet Akif Ersoy in? | poet (fallback) |  |
| t0160648 | withheld:birth_date | What year did Hal Sparks come into the world? | 1969 (fallback) |  |
| t0137713 | withheld:description | What exactly is Gbarnga? | capital city of bong county (fallback) |  |
| t0013025 | withheld:birth_place | What town was Adolphe Monticelli born in? | marseille, france / marseille (fallback) |  |
| t0025965 | withheld:birth_date | Date of birth for Jerry Reinsdorf? | 1936-2-25 (fallback) |  |
| t0182936 | withheld:population | Phola has how many residents? | 38,202 (fallback) |  |
| t0187668 | withheld:description | Who exactly is Lee Dixon lol | retired english professional footballer (fallback) | filler |
| t0102928 | unknowable:weather | is it raining in general santos today? | {} [none] (fallback) | lower |
| t0111737 | withheld:death_place | Robert Bloomfield died where? | shefford, bedfordshire / shefford (fallback) |  |
| t0115031 | withheld:description | whats Kaffrine | capital town of kaffrine region of senegal (fallback) | slang,nopunct |

## multiturn

| id | sub | question | expected | messy |
|---|---|---|---|---|
| t0192742 | tool_follow | What's 40% of 756? / What about 20% of it? | {"result": "151.2", "call": "pct_of 20 756"} [tool] (answer) |  |
| t0162017 | recall:color | My favourite colour is crimson. / What city serves as the capital of the country Mexico? / What colour did I say I like? | crimson (answer) |  |
| t0188111 | follow_entity:birth_date | What's the birthday of James Willard Hurst? / AND FOR HERB WASHINGTON ASAP | 1951-11-16 (answer) | filler,caps |
| t0148458 | follow_rel:death_date | Where did Karl Vennberg pass away? / And their date of death? | 1995-5-12 (answer) |  |
| t0022077 | tool_follow | What's 5% of 799? / Now do 40%. | {"result": "319.6", "call": "pct_of 40 799"} [tool] (answer) |  |
| t0029959 | follow_rel:death_date | What line of work was Paul Weston in? / When did they die? | 1996-9-20 (answer) |  |
| t0088866 | recall:pet | My cat is called Ziggy. / Which political party was Carl Sanders in? / How high above sea level is Hotel Transamerica Airport? / What's my pet's name? | ziggy (answer) |  |
| t0154600 | recall:city | I live over in Chiang Mai. / Dick van Patten's profession? / Where am I basdd? | chiang mai (answer) | typo |
| t0020856 | recall:city | I live over in Nairobi. / What year did Claire Dodd pass away? / Which city did I say I live in? | nairobi (answer) |  |
| t0019495 | follow_rel:population | Who is the country Spain's head of state right now? / And how many people live there | 47,900,000 (answer) | nopunct |
| t0101679 | follow_entity:publication_year | In what year was Proven Guilty published? / And what about Taking Chances? | 2012 (answer) |  |
| t0187415 | follow_entity:birth_date | What's the birthday of Henry Cianfrani? / quick question and what about James Warhola | 1955-3-16 (answer) | filler,nopunct |
| t0145341 | recall:pet | My cat is called Mochi. / What school did Charles Clarke graduate from? / What kind of music does Patrick Nuo make? / What's my pet's name? | mochi (answer) |  |
| t0093795 | follow_rel:birth_date | What party did Katharine Stewart-Murray, Duchess of Atholl represent? / And when were they born | 1874-11-6 (answer) | nopunct |
| t0125648 | recall:job | My job is chemist. / What year did Small Great Things come out? / What's my job again? | chemist (answer) |  |
| t0113295 | follow_entity:official_languages | Official language of Liechtenstein? / How about Qatar? | arabic (answer) |  |
| t0007307 | follow_rel:author | In what year was Never Go Back published? / who wrpte it? | lee child (answer) | typo,lower |
| t0150088 | tool_follow | What's 50% of 900? / What about 10% of it | {"result": "90", "call": "pct_of 10 900"} [tool] (answer) | nopunct |
| t0115906 | follow_rel:birth_place | Which political party was Adam Afriyie in? / And their birthplace? | wimbledon, london, england / wimbledon (answer) |  |
| t0054372 | follow_entity:population | How populated is Lu'an? / And what about Munderi? | 21,676 (answer) |  |

## ambiguous

| id | sub | question | expected | messy |
|---|---|---|---|---|
| t0039171 | underspecified | How old is he? | {} [none] (clarify) |  |
| t0165085 | ambiguous:country | in which nation is yuanyang? | candidates: ['city:1786016', 'city in china']; ['city:7517497', 'city in china'] (clarify_or_likeliest) | lower |
| t0019738 | ambiguous:population | Do you know da population figure for Kodoli? | candidates: ['city:13353683', 'city in india']; ['city:1266390', 'city in india'] (clarify_or_likeliest) | slang |
| t0072955 | ambiguous:country | in which nation is gaoliu | candidates: ['city:1810472', 'city in china']; ['city:1810473', 'city in china'] (clarify_or_likeliest) | nopunct,lower |
| t0096212 | ambiguous:country | What country would I be in at London? | candidates: ['city:2643743', 'city in united kingdom']; ['city:6058560', 'city in canada'] (clarify_or_likeliest) |  |
| t0043506 | ambiguous:author | To Say Nothing of the Dog was written by whom? | candidates: ['wk:To Say Nothing of the Dog', 'wiki']; ['book:5341', 'book by connie willis'] (clarify_or_likeliest) |  |
| t0083218 | ambiguous:population | Roughly how many people are in Cary? | candidates: ['city:4459467', 'city in north carolina']; ['city:4886738', 'city in illinois'] (clarify_or_likeliest) |  |
| t0134380 | ambiguous:country | In which nation is Oregon? | candidates: ['usstate:OR', 'u.s. state']; ['city:5165734', 'city in ohio'] (clarify_or_likeliest) |  |
| t0131928 | ambiguous:elevation | WHAT'S THE ELEVATION OF JOSE CELESTINO MUTIS AIRPORT ? | candidates: ['airport:BSC', 'airport in bahia solano']; ['airport:MQU', 'airport in ?'] (clarify_or_likeliest) | filler,caps |
| t0165990 | ambiguous:birth_place | Where's da Earl of Halifax's birthplace? | candidates: ['wb:140546', 'english poet and statesman']; ['wb:461484', 'person']; ['wb:461481', 'person'] (clarify_or_likeliest) | slang |
| t0026999 | ambiguous:population | ROUGHLY HOW MANY PEOPLE ARE IN SINOP THX | candidates: ['city:6318696', 'city']; ['city:739600', 'city in turkiye'] (clarify_or_likeliest) | filler,caps |
| t0055577 | ambiguous:country | Basi is located in which country? | candidates: ['city:1276765', 'city in india']; ['city:1276767', 'city in india']; ['city:1276764', 'city in india'] (clarify_or_likeliest) |  |
| t0150669 | ambiguous:country | Which country is Depok in? | candidates: ['city:1645524', 'city in west java province']; ['city:1645518', 'city in indonesia'] (clarify_or_likeliest) |  |
| t0135386 | underspecified | what's the capital? | {} [none] (clarify) | lower |
| t0183813 | ambiguous:author | The Handmaid's Tale was written by whom? | candidates: ['book:119', 'book by margaret atwood']; ["wk:The Handmaid's Tale", 'wiki'] (clarify_or_likeliest) |  |
| t0093159 | ambiguous:birth_date | What year did Jimmy Doyle come into the world? | candidates: ['wb:2709523', 'irish hurler']; ['wb:46318483', 'australian musician'] (clarify_or_likeliest) |  |
| t0046038 | underspecified | what's the population there | {} [none] (clarify) | nopunct,lower |
| t0144746 | ambiguous:birth_place | THE EARL OF SALISBURY WAS BORN WHERE | candidates: ['wb:70598', 'person']; ['wb:460835', 'person'] (clarify_or_likeliest) | nopunct,caps |
| t0184079 | underspecified | How old is he? | {} [none] (clarify) |  |
| t0093365 | ambiguous:country | IN WHICH NATION IS WASHINGTON? | candidates: ['usstate:WA', 'u.s. state']; ['city:4140963', 'city in district of columbia']; ['city:5549222', 'city in utah'] (clarify_or_likeliest) | caps |
