# TurboX 1M test: 20 random samples per category

Drawn from shards 00-03 with seed 7 after the freeze (results/test_freeze.json). Gold shown compactly.


## kb_fact

| id | sub | question | expected | messy |
|---|---|---|---|---|
| t0105954 | occupation | Job Cohen's profession? | politician (answer) |  |
| t0049330 | group | What group does the element Chlorine belong to on the periodic table | 17 (answer) | nopunct |
| t0129165 | death_date | What year did Sir Anthony Meyer, 3rd Baronet pass away? | 2004 (answer) |  |
| t0015867 | borders | The country Reunion bordes which countries? | none / no countries / no neighbo (answer) | typo |
| t0023897 | occupation | what does roy strong do for a living | art historian (answer) | nopunct,lower |
| t0175597 | nationality | What nationality was Friedrich Hecker? | german (answer) |  |
| t0030879 | nationality | Tim Macartney-Snape's nationality? | australian (answer) |  |
| t0119646 | region | Benin is in which subregion? | western africa (answer) |  |
| t0190908 | is_a | What category does a statuary belong to | collection / aggregation / accumulation (answer) | nopunct |
| t0019021 | birth_place | Where's Anne Marie Martinozzi's birthplace? | rome, italy / rome (answer) |  |
| t0166077 | death_place | Do you know where Norman Maclean died? | chicago, illinois, united states / chicago (answer) |  |
| t0069987 | state | Which US state is Yucaipa in? | california (answer) |  |
| t0012328 | region | What region of da world is the countty Thailand in? | south-eastern asia (answer) | typo,slang |
| t0028264 | elevation | How high above sea level is Paro Airport? | 7,332 feet (answer) |  |
| t0142077 | death_date | In which year did Ludwig Lachmann die? | 1990 (answer) |  |
| t0136994 | country | which country is hoorn in? | netherlands / holland / kingdom of the netherlands (answer) | lower |
| t0023022 | death_place | Where did Andrew Goodman pass away? | mississippi, u.s. / mississippi (answer) |  |
| t0078475 | director | Who was the director of The Patriot? | roland emmerich (answer) |  |
| t0029826 | founded_year | What year was Benet Academy established? | 1887 (answer) |  |
| t0180551 | position | Which position did Ray Lewis play? | middle linebacker (answer) |  |

## derived

| id | sub | question | expected | messy |
|---|---|---|---|---|
| t0093005 | compare_elevation | Which airport sits higher, Labo Airport or Danbury Municipal Airport just curious | danbury municipal airport (answer) | filler |
| t0012862 | age_at_death | At what age did Eugene Thomas Maleska die? | 77 (answer) |  |
| t0180942 | pop_of_largest_city | What's the population of the US state of New Hampshire's biggest city? | 568,996 (as of 2025) (answer) |  |
| t0124065 | birth_weekday | WHAT DAY OF DA WEEK WAS BEV DESJARLAIS BORN ON? | friday (answer) | slang,caps |
| t0026860 | pop_of_largest_city | What's the population of the US state of California's biggest city? | 3,820,914 (as of 2025) (answer) |  |
| t0048907 | capital_of_country_of_airport | Wick Airport is in a country whose capital is what? | london (answer) |  |
| t0138100 | compare_died | Which of them passed away earlier, James Buchanan Eads or Rochus Misch? | james buchanan eads (answer) |  |
| t0137354 | isa | Is a relaxation time a kind of time period? | no (answer) |  |
| t0127723 | convert_elev_m | What's Zahedan International Airport's elevation in meters? | 1391.1072 metres (answer) |  |
| t0013515 | author_birth_place | The writer of Dragonfly in Amber was born where? | arizona, u.s. / arizona (answer) |  |
| t0126545 | convert_diameter_mi | How many miles across is Saturn? | 72364.889 miles (answer) |  |
| t0128251 | compare_elevation | WHICH AIRPORT SITS HIGHER ESPERADINHA AIRPORT OR MOUNT VERNON AIRPORT | mount vernon airport (answer) | nopunct,caps |
| t0087022 | age_at_death | At what age did Roscoe Lee Browne die? | 84 (answer) |  |
| t0010822 | capital_of_country_of_city | What's the capital of the country that Tabuk in Saudi Arabia is in? | riyadh (answer) |  |
| t0048431 | count_languages | United States Minor Outlying Islands has how many official languages | 1 (answer) | nopunct |
| t0010138 | population_of_capital | What is the population of Bahamas's capital? | 227,940 (as of 2025) (answer) |  |
| t0121988 | isa | Would you call a cloth covering a type of artifact? | yes (answer) |  |
| t0188144 | isa | Would you call a grain a type of property? | yes (answer) |  |
| t0028933 | convert_elev_m | How high is Sasstown Airport in metres? | 1.8288 metres (answer) |  |
| t0063853 | population_of_capital | How many people live in the capital city of Lesotho? | 359,753 (as of 2025) (answer) |  |

## tool

| id | sub | question | expected | messy |
|---|---|---|---|---|
| t0091445 | lcm | Smallest number divisible by both 156 and 5? | 780 (answer) |  |
| t0031486 | words | How do u write 234922 in words | two hundred thirty-four thousand nine hundred twenty-two (answer) | slang,nopunct |
| t0117313 | gcd | What's the greatest common divisor of 137 and 50? | 1 (answer) |  |
| t0025764 | date | wht is today's date? | thursday, january 8, 2026 (answer) | typo,lower |
| t0124121 | time | What's the time right now? | 10:44 pm (answer) |  |
| t0066797 | calc_pow | What's 8 to the power of 5? | 32768 (answer) |  |
| t0121764 | world_time | What time is it in Manila at da moment | 10:47 pm, tuesday (answer) | slang,nopunct |
| t0177871 | count_letter | count the r's in dinosaur. | 1 (answer) | lower |
| t0148347 | tip | HOW MUCH SHOULD I TIP ON 241 DOLLARS AT 22 PERCENT? | tip 53.02, total 294.02 (answer) | caps |
| t0039174 | calc_add | 26263 plus 5704 equals what? | 31967 (answer) |  |
| t0022260 | calc_div | divide 5952 by 24 i forgot | 248 (answer) | filler,nopunct,lower |
| t0126588 | gcd | Highest common factor of 150 and 45? | 15 (answer) |  |
| t0124164 | count_letters | How many letters does the word volcano have? | 7 (answer) |  |
| t0139090 | convert | How many centimeters are in 307 inches? | 779.78 centimeters (answer) |  |
| t0040659 | calc_div | WHT IS 5760 DIVIDDE BY 36? | 160 (answer) | typo,caps |
| t0080969 | from_roman | Convert MMLV from Roman numerals | 2055 (answer) | nopunct |
| t0020968 | convert | How many minutes are in 369 hours? | 22140 minutes (answer) |  |
| t0118904 | words | Spell out the number 207241 in words. | two hundred seven thousand two hundred forty-one (answer) |  |
| t0155139 | convert | ok so convert 56 pounds into kilograms. | 25.4012 kilograms (answer) | filler,lower |
| t0013612 | convert | Convert 43 centimetres ino inches pls | 16.9291 inches (answer) | typo,filler |

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
| t0026014 | mintaka | was bad boys for life released the same year as birds of prey? | yes (either) |  |
| t0186687 | opentriviaqa | what actor stars as retired jewel thief opposite grace kelly in alfred hitchcocks romantic thriller to catch a thief? | cary grant (either) |  |
| t0098665 | freebaseqa | who played the title role in the 2004 film the life and death of peter sellers? | geoffrey rush (either) |  |
| t0171255 | mintaka | how many olympic medals does michael phelps have that are not silver or bronze? | 23 (either) |  |
| t0161227 | webquestions | where did they find jenni rivera's body? | iturbide, nuevo leon (either) | lower |

## withheld

| id | sub | question | expected | messy |
|---|---|---|---|---|
| t0112809 | withheld:population | POPULATION OF CROULEBARBE? | 20,062 (as of 2025) (fallback) | caps |
| t0146906 | withheld:birth_date | In which year was Viktor Chernomyrdin born? | 1938 (fallback) |  |
| t0094557 | unknowable:private | Where does John Worsfold live exactly, street address? | none (fallback) |  |
| t0199613 | withheld:description | Who is Bob Mcnab? | ~ english former footballer (fallback) |  |
| t0024437 | withheld:birth_date | georg von kuchler was born on wich day? | 1881-5-30 (fallback) | typo,lower |
| t0039514 | withheld:occupation | What kind of work did Skeet Ulrich do? | actor (fallback) |  |
| t0168298 | withheld:description | Can you tell me pls who Valerie Mahfood is? | ~ female boxer (fallback) | slang |
| t0136622 | withheld:death_place | Place of death of Emil Hacha? | prague, czechoslovakia / prague (fallback) |  |
| t0055400 | unknowable:news | What happened in the news today? | none (fallback) |  |
| t0112409 | withheld:country | Which country is Wuchuan in? | china / people's republic of china / zhongguo (fallback) |  |
| t0050815 | withheld:death_date | Lucretiu Patrascanu died in which year? | 1954 (fallback) |  |
| t0160648 | withheld:death_date | What year did Vittorio Pozzo pass away? | 1968 (fallback) |  |
| t0137713 | withheld:definition | Can you explain what 'price freeze' means? | ~ a freeze of prices at a given level (fallback) |  |
| t0013025 | withheld:author | Author of Succubus Dreams | richelle mead (fallback) | nopunct |
| t0025965 | withheld:country | Which country is Bhanga in? | bangladesh / gonoprojatontri bangladesh / people's republic of bangladesh (fallback) |  |
| t0182936 | withheld:author | Author of Book of a Thousand Days? | shannon hale (fallback) |  |
| t0187668 | withheld:death_place | Do u know where Eugenio Coseriu died lol | tubingen, germany / tubingen (fallback) | slang,filler |
| t0102928 | unknowable:weather | is it raining in general santos today? | none (fallback) | lower |
| t0111737 | withheld:death_date | Edoardo Chiossone died in which year? | 1898 (fallback) |  |
| t0115031 | withheld:description | Who is Kamil Zayatte | ~ guinean footballer (fallback) | nopunct |

## multiturn

| id | sub | question | expected | messy |
|---|---|---|---|---|
| t0192742 | tool_follow | What's 40% of 756? ⏎ What about 20% of it? | 151.2 (answer) |  |
| t0162017 | recall:color | My favourite colour is crimson. ⏎ What city serves as the capital of the country Mexico? ⏎ What colour did I say I like? | crimson (answer) |  |
| t0188111 | follow_entity:birth_date | What's the birthday of Rivers Turnbull? ⏎ AND FOR ADOLF ZIEGLER ASAP | 1892-10-16 (answer) | filler,caps |
| t0148458 | follow_rel:birth_place | Which political party was Brad Ellsworth in? ⏎ hey so and their birthplace? | jasper, indiana / jasper (answer) | filler |
| t0022077 | tool_follow | What's 5% of 799? ⏎ Now do 40%. | 319.6 (answer) |  |
| t0029959 | follow_rel:currency | International dialing code of Indonesia? ⏎ What currency do they use there? | indonesian rupiah (answer) |  |
| t0088866 | recall:pet | My cat is called Ziggy. ⏎ Which political party was Luis Alberto Lacalle in? ⏎ How high above sea level is Ponta Pora Airport? ⏎ What's my pet's name? | ziggy (answer) |  |
| t0154600 | recall:city | I live over in Chiang Mai. ⏎ Carlos Saura's profession? ⏎ Where am I basdd? | chiang mai (answer) | typo |
| t0020856 | recall:city | I live over in Nairobi. ⏎ Dix Hills is in what state? ⏎ Where am I based? | nairobi (answer) |  |
| t0019495 | follow_rel:population | Kihei is in what state? ⏎ And how many people live there? | 20,881 (as of 2025) (answer) |  |
| t0101679 | follow_entity:publication_year | In what year was The Indian in the Cupboard published? ⏎ And what about Taking Chances? | 2012 (answer) |  |
| t0187415 | follow_entity:birth_date | Eoin Quigley: year of birth? ⏎ And for Jordan Carstens? | 1981 (answer) |  |
| t0145341 | recall:pet | My cat is called Mochi. ⏎ What school did Marvin Harris graduate from? ⏎ What kind of music does Anika Moa make? ⏎ What's my pet's name? | mochi (answer) |  |
| t0093795 | follow_rel:birth_date | What kind of music does Ronald D. Moore make? ⏎ And when were they born? | 1964-7-5 (answer) |  |
| t0125648 | recall:job | My job is chemist. ⏎ What year did The Black Swan: the Impact of the Highly Improbable come out? ⏎ What's my job again? | chemist (answer) |  |
| t0113295 | follow_entity:official_languages | Official language of Liechtenstein? ⏎ How about Qatar? | arabic (answer) |  |
| t0007307 | follow_rel:birth_date | Which university did Tony Sertich attend? ⏎ And when were they born? | 1976-1-2 (answer) |  |
| t0150088 | tool_follow | What's 50% of 900? ⏎ What about 10% of it | 90 (answer) | nopunct |
| t0115906 | follow_rel:death_date | On what date was John R. Brinkley born? ⏎ and theeir date of death? | 1942-5-26 (answer) | typo,lower |
| t0054372 | follow_entity:atomic_number | Atomic number of Seaborgium? ⏎ SAME QUESTION FOR OXYGEEN | 8 (answer) | typo,nopunct,caps |

## ambiguous

| id | sub | question | expected | messy |
|---|---|---|---|---|
| t0039171 | underspecified | How old is he? | none (clarify) |  |
| t0165085 | ambiguous:country | in which nation is york? | clarify, or likeliest: city in united kingdom (united kingdom / great britain / united kin (clarify_or_likeliest) | lower |
| t0019738 | ambiguous:population | Do you know da population figure for Kirov? | clarify, or likeliest: city in russia (507,155 (as of 2025)) (clarify_or_likeliest) | slang |
| t0072955 | ambiguous:country | in which nation is gantang | clarify, or likeliest: city in china (china / people's republic of china / zhongguo) (clarify_or_likeliest) | nopunct,lower |
| t0096212 | ambiguous:country | What country would I be in at Livingston? | clarify, or likeliest: city in united kingdom (united kingdom / great britain / united kin (clarify_or_likeliest) |  |
| t0043506 | ambiguous:publication_year | What year did Tithe: a Modern Faerie Tale come out? | clarify, or likeliest: book by holly black (2002) (clarify_or_likeliest) |  |
| t0083218 | ambiguous:population | Roughly how many people are in Cartagena? | clarify, or likeliest: city in colombia (914,552 (as of 2025)) (clarify_or_likeliest) |  |
| t0134380 | ambiguous:population | Olney has how many residents? | clarify, or likeliest: city in pennsylvania (39,154 (as of 2025)) (clarify_or_likeliest) |  |
| t0131928 | ambiguous:birth_place | WHERE'S JOHN WILLIAMSON'S BIRTHPLACE ? | clarify, or likeliest: english former professional footballer (derby, england / derby) (clarify_or_likeliest) | filler,caps |
| t0165990 | ambiguous:birth_place | Where's da Earl of Gowrie's birthplace? | clarify, or likeliest: person (windsor, berkshire / windsor) (clarify_or_likeliest) | slang |
| t0026999 | ambiguous:elevation | Simon Bolivar International Airport elevation? | clarify, or likeliest: airport in guayaquil (19 feet) (clarify_or_likeliest) |  |
| t0055577 | ambiguous:country | Bartlett is located in which country? | clarify, or likeliest: city in tennessee (united states / united states of america) (clarify_or_likeliest) |  |
| t0150669 | ambiguous:country | Which country is Denton in? | clarify, or likeliest: city in texas (united states / united states of america) (clarify_or_likeliest) |  |
| t0135386 | underspecified | what's the capital? | none (clarify) | lower |
| t0183813 | ambiguous:author | The Guardian was written by whom? | clarify, or likeliest: book by nicholas sparks (nicholas sparks) (clarify_or_likeliest) |  |
| t0093159 | ambiguous:country | What country would I be in at Jiangzhuang? | clarify, or likeliest: city in china (china / people's republic of china / zhongguo) (clarify_or_likeliest) |  |
| t0046038 | underspecified | what's the population there | none (clarify) | nopunct,lower |
| t0144746 | ambiguous:death_date | In which year did The Earl of Rosslyn die? | clarify, or likeliest: person (1805) (clarify_or_likeliest) |  |
| t0184079 | underspecified | How old is he? | none (clarify) |  |
| t0093365 | ambiguous:country | IN WHICH NATION IS WASCO? | clarify, or likeliest: city in california (united states / united states of america) (clarify_or_likeliest) | caps |
