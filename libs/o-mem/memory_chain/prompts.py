#!/usr/bin/env python
# coding=utf-8
# Copyright 2025 The OPPO Personal AI team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''
This file store all our prompts.
Some of the prompts are updated from memoryOS.
'''

GENERATE_SYSTEM_RESPONSE_SYSTEM_PROMPT = (
    "Your task is to choose the best option to answer the message from the user. If you can not fined the event mentioned in the option from the profie, then you could not choose the options."
)

GENERATE_SYSTEM_RESPONSE_USER_PROMPT = (
   "Your task is to choose the best option to answer the message from the user. If you can not fined the event mentioned in the option from the profie, then you could not choose the options."
   "Sometimes a user's attitude toward an event is implicit and you have to infer it."
    "Here is the profile history of the user:"
    "{background}\n"
    "The message of the user is: \n" 
    "{question} \n"
    "Find the most appropriate model response band give your final answer (a), (b), (c), or (d) after the special token <final_answer>."
    "{all_options}"
)


GENERATE_SYSTEM_RESPONSE_ONLY_WM_SYSTEM_PROMPT = (
    "Your task is to choose the best option to answer the message from the user."
)


GENERATE_SYSTEM_RESPONSE_ONLY_WM_USER_PROMPT = (
    "Your task is to choose the best option to answer the message from the user."
    "Here is the recent messages from the user:"
    "{messages}\n"
    "The current message of the user is: \n" 
    "{question} \n"
    "Find the most appropriate model response and give your final answer (a), (b), (c), or (d) after the special token <final_answer>."
    "{all_options}"
)


GENERATE_SYSTEM_RESPONSE_ONLY_INIT_PROFILE_PROMPT = (
    "Your task is to choose the best option to answer the message from the user."
    "The persona profile of the user is: \n" 
    "{persona} \n"
     "The current message of the user is: \n" 
    "{question} \n"
    "Find the most appropriate model response and give your final answer (a), (b), (c), or (d) after the special token <final_answer>."
    "{all_options}"
)




REORGANIZE_USER_PROFILE_SYSTEM_PROMPT = """

### STRICT MESSAGE-FOCUSED PROFILE RESTRUCTURER ###

You are a precision profile editor that rewrites profiles to include ONLY information directly relevant to the new message, while maintaining:

1) Original narrative format
2) Full citation chain
3) Explicit linkage to prior traits

--- RULES ---
1. INPUT:
[Current Profile]
"Natural description with [X] citations"
[New Message]
"Raw user input"

2. PROCESSING:
A) Include ONLY if:
   - Directly referenced in message
   - Contradicted by message
   - Required to explain changes ("stopped X" needs original X cited)

B) Citation Handling:
   - Preserve ALL original citations ([1][2]...)
   - New updates get [NewX] markers
   - Chain changes: "stopped [2]" → "has stopped [2] due to [New1]"

3. OUTPUT:
- Single paragraph
- Original writing style
- Every fact cited
- No unrelated traits

### Example Input:  
[Current Profile]
"This 30yo teacher from Paris [1] practices yoga daily [2], is vegetarian [3], writes novels [4], hates heat [5]."

[New Message]
"Stopped yoga after injury. Focusing more on writing now."

### Example Output:  
"This 30yo teacher from Paris [1] has stopped daily yoga [2] due to injury [New1] and is focusing more on novel writing [4]."

"""


REORGANIZE_USER_PROFILE_USER_PROMPT = """

Now please generate a edited user persona profile from this new message and user profile.\n

New message from user:
{New_Message}
Profile:
{Profile}

Output:

"""


REORGANIZE_USER_PROFILE_Message_SYSTEM_PROMPT =  """### STRICT MESSAGE-FOCUSED PROFILE RESTRUCTURER ###

You are a precision profile editor that rewrites profiles to include ONLY information directly relevant to the new message, while maintaining:

1) Original narrative format
2) Full citation chain
3) Explicit linkage to prior traits

--- RULES ---
1. INPUT:
[Current Profile]
"Natural description with [X] citations"
[New Message]
"Raw user input"
[Response Options]
"Options of reponses concerning the question"

2. PROCESSING:
A) Include ONLY if:
   - Directly referenced in message
   - Contradicted by message
   - Required to explain changes ("stopped X" needs original X cited)

B) Citation Handling:
   - Preserve ALL original citations ([1][2]...)
   - New updates get [NewX] markers
   - Chain changes: "stopped [2]" → "has stopped [2] due to [New1]"

3. OUTPUT:
- Single paragraph
- Original writing style
- Every fact cited
- No unrelated traits

### Example Input:  
[Current Profile]
"This 30yo teacher from Paris [1] practices yoga daily [2], is vegetarian [3], writes novels [4], hates heat [5]. The teacher come from GuangZhou, a city in Guangdong Province [6]" 

[New Message and Options]
"Stopped yoga after injury. Focusing more on resting in my hometowm." Options: A. You are good at writing. You can stay at home to practice writing.

### Example Output:  
"This 30yo teacher from Paris [1] has stopped daily yoga [2] due to injury [New1] and is focusing more on novel writing [4] in her hometown GuangZhou [6]."

"""


REORGANIZE_USER_PROFILE_Message_Options_USER_PROMPT = """

Now please generate a edited user persona profile from this new message and user profile.\n

New messages and options :
{New_Message}. Options: {Option}
Profile:
{Profile}

Output:

"""


GENERATE_USER_PROFILE_SYSTEM_PROMPT = """

Task:  
Generate a **detailed and nuanced user persona profile** based on the provided dialogue history. The input format is `[Turn Number][Content]`. Your output must be a **continuous, narrative-style paragraph** (no bullet points or sections) with all claims rigorously cited.

### Key Requirements:

1. **Structure & Content**  
   - Cover: Demographics (age/gender/location), Background (career/education), Preferences (interests/habits), and Behavioral Shifts.  
   - **No emojis or informal markers**. Maintain a professional tone.  
   - Always refer to the person as 'the user' (not 'they'). Example: 'The user prefers tea [3]', not 'They prefer tea [3]'."

2. **Citation Rules**  
   - Every claim must reference specific turns (e.g., "Prefers tea over coffee [3][7]").  
   - Flag contradictions explicitly (e.g., "Conflict: Claims to dislike cities [2] but mentions enjoying NYC nightlife [9]").  

3. **Nuance & Flow**  
   - Highlight how the characteristics, preferenes, and personalities of the user evolve.  
   - Use transitional phrases to ensure logical flow (e.g., "While...", "Despite...").  

### Example Input:  
[1][Hi! I’m a 28yo graphic designer from Seattle. Love hiking and coffee.]  
[2][Just adopted a golden retriever puppy last week.]  
[3][Actually vegan for 2 years, but I cheat sometimes with cheese pizza.]  
[4][Ugh, my freelance work is so unstable… miss my old office job’s benefits.]  
[5][Weekend plans? Hiking with the pup then gaming (big Zelda fan!).]  

### Example Output:  
"This 28-year-old graphic designer from Seattle [1] maintains an active lifestyle centered around hiking and coffee. The user recently adopted a golden retriever puppy [2], which has influenced the user's daily routines. Professionally, the user expressed dissatisfaction with the transition from a stable office job to freelance work, citing concerns about inconsistent income and lost benefits [4]. While the user identify as vegan for ethical reasons (maintained for two years), the user occasionally indulge in cheese pizza, demonstrating flexibility in the user's dietary habits [3]. The user's leisure time balances outdoor activities like hiking with their dog and indoor interests such as gaming, particularly the Zelda franchise [5]. The shift to freelancing appears to be the user's most significant recent life change, with nostalgic references to the user's previous job's stability [4]."

"""


GENERATE_USER_PROFILE_USER_PROMPT = """

Now please generate a professional user persona profile from this dialogue history.\n

Dialogue History:
{DIALOGUE_HISTORY}

Output:
"""





  
UNDERSTAND_USER_EXPERIENCE_PROMPT = """

    Perform topic tagging on this message from user following these rules:

    1. Generate machine-readable tag
    2. Tag should cover:

       - Only one primary event concerning the user messages.
       - The author's attitude towards the event.
       - The topic should be the subject of the message which the user held attitude towards.
       - The topic and reason behind the attitude, sometimes you need to infer the attitude from the users' words. 
       - The facts or events infered or revealed from the user's message.
       - If the author mention the time of the facts or events, the tag should also include the time inferred from the message (e.g., last day, last week)
       - Any attributes of the user revealed by the user's message (e.g., demographic features,biographical information,etc).

    3. Use this JSON format:
    {{
        "text": "original message",
        "tags": {{
            "topic": ["event"],
            "attitude": ["attitude towards the event": Postive or Negative or Mixed]
            "reason" :["The reason concenring the attitude towards the event"]
            "facts": ["The facts or events infered from the user's message"]
            "attributes": ["The attributes of the user revealed by the user's message"]
        }},
        "summary": "One sentence summary of the message"
        "rationale": "brief explanation concenring why raising these tags"
    }}

    Example Input: "The jazz workshop helped me overcome performance anxiety"
    Example Output:
    {{
        "text": "Last week's jazz workshop helped me overcome performance anxiety since the tutors are so patients.",
        "tags": {{
            "topic": ["music workshop"],
            "attitude": ["Positive"],
            "reason": ["The tutors can teach the use patiently."],
            "facts":["join jazz workshop last week"],
            "attributes": ["user worrys about jazz performance"]
        }},
        "summary": "Jazz workshop helped the user overcome performance anxiety."
        "rationale": "The user's performance anxiety was alleviated with the help of Jazz Workshop. Therefore , he is positive towards Jazz Workshop."
    }}

    Example Input: "I stop playing basketball for this semester due to too much stress."
    Example Output:
    {{
        "text": "The user step away from playing baskerball due to too much stress.",
        "tags": {{
            "topic": ["playing basketball"],
            "attitude": ["negative"],
            "reason": ["Too much stree for playing basketball"],
            "facts:["stop playing basketball"],
            "attributes": ["user hate stress"]
        }},
        "summary": "The user stop playing baskerball due to too much stress."
        "rationale": "The user stop playing baskerball due to too much stress. Therefore, the user is negative towards playing basketball."
    }}

   Example Input: "I go back to play basketball due to strenghten my body yesterday."
   Example Output:
    {{
        "text": "The user return to play basketball due to strenghten the body.",
        "tags": {{
            "topic": ["playing basketball"],
            "attitude": ["Positive"],
            "reason": ["Baskterball could help strenghtening the body"],
            "facts":["return to play basketball yesterday"],
            "attributes": ["User value the body"]
        }},
        "summary": "The user go back to play basketball due to strenghten the body."
        "rationale": "he user go back to play basketball due to strenghten the body. There, the user is positive towards playing basketball."
    }}

   Example Input: "I hate playing basktetball due to its preasure"
   Example Output:
    {{
        "text": "I hate playing basktetball since I move from my hometowm GuangZhou due to its preasure.",
        "tags": {{
            "topic": ["hate playing basketball"],
            "attitude": ["negative"],
            "reason": ["The user hates playing basktetball for preasure."],
            "facts":["hate playing basketball"],
            "attributes": ["user hate stress","user's hometown is GuangZhou"]
        }},
        "summary": "The user go back to play basketball due to strenghten the body."
        "rationale": "The user go back to play basketball due to strenghten the body. There, the user is positive towards playing basketball."
    }}

    Now analyze this message:
    "{message}"

    """







GENERATE_RETRIEVAL_CLUES_SYSTEM_PROMPT = """

Generate **third-person responses ideas** based strictly on the provided user profile (with citations) and new message. Responses must directly reference and utilize profile content.

### Requirements:

1. **Format Specifications**
   - Provide no more than three numbered response ideas
   - Use "the user" or profile-specified pronouns
   - Indicate the relationships between profile content and the response idea.
   - Include relevant profile citations [X] for each response

2. **Content Rules**
   - All responses must be directly derived from profile content
   - No extrapolations beyond cited profile information
   - All advice or suggestions should be explicitly supported by profile

3. **Response Content**
   (1) Profile-referenced activity mention
   (2) Profile-documented characteristic
   (3) How are these activities and characteristics related to the responsed to the message.

### Example Input:  
[Profile]
"This 30-year-old teacher from Paris [1] practices yoga daily [2], is vegetarian [3], writes novels [4], and hates heat [5]. Originally from Guangzhou, Guangdong Province [6], 
she speaks four languages fluently [7], collects vintage postcards [8], and loves rainy weather [9]. An avid baker of vegan desserts [10] and mountain hiker [11], her favorite book
 is The Unbearable Lightness of Being [12], and she dreams of publishing a novel [13]. At 25, she broke her wrist hiking in the Alps [14], and at 18 suffered a concussion in a car accident
that still causes occasional migraines [15]. Her family has endured trauma as well: her mother sustained severe burns in a kitchen fire when she was 10 [16], and her younger brother temporarily 
lost mobility after a spinal fracture during a cycling race [17]." 

[New Message]
"I have to Stop yoga after injury. Focusing more on resting in my hometowm. This is really painful." 

### Example Output:  
(1): In this profile, the user likes writing novels [4]. This indicates the user could start practicing writing novels during this period of resting time. 
(2): In this profile, the user break legs in Alps and brings occasional migraine [9], this indicates the user should pay more attention to sports safety. 
(3): In this profile, the user a vegetarian [3], this indicates the user should try to eat more protein to quickly restore the user's body.


"""




GENERATE_RETRIEVAL_QUERY_SYSTEM_PROMPT = """

Given a user's latest message and a profile built from the user's previous messages, your task is to generate a group of retrieval query based on the user profile that 
retrieves information from the conversation history that helps answer the current message.

"""


GENERATE_RETRIEVAL_CLUES_USER_PROMPT = """

Now please generate the retrival clues from this new message and user profile.\n

New messages:
{Query}
Profile:
{Profile}

Output:

"""


Profile_Update_SYSTEM_PROMPT = """





"""


Profile_Update_USER_PROMPT = """

Now please generate the retrival clues from this new message and user profile.\n

New messages:
{Query}
Profile:
{Profile}

Output:

"""


Message_ROUTER_SYSTEM_PROMPT = """
You are a user profile updater that maintains a dictionary of topics and the user's attitudes toward them. For each new message, analyze whether to update the profile and respond in JSON format.

### Rules:
1. Input:
   - Profile: {"topic1": "attitude1", "topic2": "attitude2"...}
   - Message: ("topic"："attitude")

2. Processing:
   - Compare topics semantically (e.g., "dogs" ≈ "puppies")
   - Compare attitudes semantically (e.g., "dislike" ≈ "hate")
   - Choose action:
     * [UPDATE] if similar topic exists with different attitude
     * [ADD] if topic is new
     * [IGNORE] if same topic+attitude exists
   - If there is no matched topics, the target should be "None"

3. Output format (JSON):
{{
  "Action": "[UPDATE|ADD|IGNORE]",
  "Target": "matched topic or 'None'"
}}

### Examples:

Input 1:
Profile: {"Singing in class": "ashamed","smoking in the public":"fear of being fined"}
Message: ("Performing for peers", "proud")
Output: {"Action": "UPDATE", "Target": "Singing in class",}

Input 2:
Profile: {"Cats": "love","Dogs":"Love"}
Message: ("Kittens", "adore")
Output: {"Action": "IGNORE", "Target": "Cats"}

Input 3:
Profile: {"Swimming": "enjoy"}
Message: ("Hiking", "love")
Output: {"Action": "ADD", "Target": "None"}

"""


Message_ROUTER_USER_PROMPT = """
Now please generate the action and target from this new message and user profile.\n
Profile:
{Profile}
New messages:
{Message}

Output:

"""




Message_Fact_ROUTER_SYSTEM_PROMPT = """
You are a user profile updater that maintains a dictionary of user's facts. For each new message, analyze whether to update the user facts profile and respond in JSON format.

### Rules:
1. Input:
   - Profile: {"user fact 1","user fact 2", "user fact 3" ... "user fact n"}
   - Message: "user fact from new message"

2. Processing:
   - Compare facts semantically (e.g., "supportive" ≈ "assisting")
   - Choose action:
     * [ADD] if the fact is new
     * [IGNORE] if same fact exists
     * [UPDATE] if contradictory fact exists

   - If there is no matched facts, the target should be "None"

3. Output format (JSON):
{{
  "Action": "[UPDATE|ADD|IGNORE]",
  "Target": "matched fact or 'None'"
}}

### Examples:

Input 1:
Profile: {"The user played basketball with friends.","The user played badminton with friends."}
Message: "The user played basketball."
Output: {"Action": "IGNORE", "Target": "The user played basketball with friends."}

Input 2:
Profile: {"The user player badminton.","The user player tennis."}
Message: "The user played basketball."
Output: {"Action": "ADD", "Target": "None"}

Input 3:
Profile: {"The user never ate dim sum."}
Message: "The user ate dim sum in Guangzhou."
Output: {"Action": "UPDATE", "Target": "The user never ate dim sum."}

"""


Message_Fact_ROUTER_USER_PROMPT = """
Now please generate the action and target from this new message and user fact profile.\n
Profile:
{Profile}
New messages:
{Message}
Output:
"""



Message_Attr_ROUTER_SYSTEM_PROMPT = """
You are a user profile updater that maintains a dictionary of user attributes. For each new message, analyze whether to update the attributes profile and respond in JSON format.

### Rules:
1. Input:
   - Profile: {"user attribute 1","user attribute 2", "user attribute 3"..."user attribute n"}
   - Message: ("user attribute from new message")

2. Processing:
   - Compare attributes semantically (e.g., "Transgender person" ≈ "Non-binary person")
   - Choose action:
     * [UPDATE] if contradictory attribute exists
     * [ADD] if the user attribute is new
     * [IGNORE] if same user attribute exists
   - If there is no matched attributes, the target should be "None"

3. Output format (JSON):
{{
  "Action": "[UPDATE|ADD|IGNORE]",
  "Target": "matched attribute or 'None'"
}}

### Examples:

Input 1:
Profile: {"The user is helpful.","The user is from China."}
Message: ("The user is supportive.")
Output: {"Action": "IGNORE", "Target": "The user is helpful."}


Input 2:
Profile: {"The user is from China.","The users may have five children."}
Message: ("The user played basketball.")
Output: {"Action": "ADD", "Target": "None"}

Input 3:
Profile: {"The user is from China.","The users may have five children."}
Message: ("The user's hometown is US.")
Output: {"Action": "UPDATE", "Target": "The user is from China."}

"""


Message_Attr_ROUTER_USER_PROMPT = """
Now please generate the action and target from this new message and user attribute profile.\n
Profile:
{Profile}
New messages:
{Message}

Output:

"""



Profile_Reorganization_SYSTEM_PROMPT =  """

Your task is to extract profile elements that are directly OR implicitly related to the current message, while:

1. Preserving original [citation] markers exactly
2. Keeping all attitude phrases unchanged
3. Providing a detailed summary explaining both explicit and implicit connections

=== INPUT FORMAT ===
[Profile]
{
  "topic1": "[1]attitude/behavior",
  "topic2": "[2]attitude/behavior",
  ...
  "topic10+": "[X]attitude/behavior" 
}

[Message]
[user's new message text]

=== PROCESSING RULES ===
1. Relevance Standards:
   - DIRECT: Topic/keyword appears in message
   - IMPLICIT: 
     * Helps explain message context
     * Provides background for behavioral changes
     * Reveals potential contradictions
     * Shows related lifestyle patterns

2. Strict Preservation:
   - Original topic names unchanged
   - Exact citation markers [X] preserved
   - No modification of attitude/behavior phrases

=== Output format (JSON):===
{
  "relevant_profile": {
    "topicA": "[X]original_attitude", 
    "topicB": "[Y]original_behavior"
  },
  "summary": "Selected [topicA] because [explicit/implicit reason]. Included [topicB] as [contextual reason], even though not directly mentioned."
}

=== COMPLEX EXAMPLE ===
[Profile] 
{
  "career_goals": "[1]promotion_focused [12]Health First [13] Stop working in companies",
  "work_life": "[2]poor_balance",
  "diet": "[3]meal_prepper",
  "exercise": "[4]gym_3x_week",
  "stress": "[5]chronic_insomnia", 
  "relationships": "[6]neglected_family",
  "finances": "[7]aggressive_saver",
  "hobbies": "[8]no_time",
  "health": "[9]high_blood_pressure",
  "commute": "[10]90_minutes"
}

[Message]
"Resigned from my job yesterday. Planning to travel while doing freelance work."

[Output]
{
  "relevant_profile": {
    "career_goals": "[1]promotion_focused 12]Health First [13] Stop working",
    "work_life": "[2]poor_balance",
    "stress": "[5]chronic_insomnia",
    "relationships": "[6]neglected_family"
  },
  "summary": "Selected career_goals (explains radical career shift), work_life (context for quitting), stress (likely contributing factor), and relationships (opportunity to reconnect during travel). Although not mentioned, these implicitly connect to the decision through accumulated lifestyle pressures."
}

"""


Profile_Reorganization_USER_PROMPT =  """

Now please extract profile elements that are directly OR implicitly related to the current message from this current message and user profile.\n

Profile:
{Profile}
New messages:
{Message}

Output:

"""

 

Preference_Merge_System_PROMPT =  """

Given a group of topics extracted from users' messages, analyze whether these topics can be logically grouped under common themes based on their descriptions. Follow these rules:

1. Only the topics talking about the exactly same things can be merged.
2. When merging topics, extract as many common details as possible from their reference sentences to create the new merged topic name
3. Maintain the original meaning and context of each topic
4. Only group topics that share significant conceptual overlap
5. Keep distinct topics separate when they represent different concepts
6. Remeber You should not reveal the attitude of the user in the merged topic name. The topic should only be the event.

=== INPUT FORMAT ===
{
  "topic1": "A summary of the sentence which the topic is extracted from",
  "topic2": "A summary of the sentence which the topic is extracted from",
  ...
  "topicN": "A summary of the sentence which the topic is extracted from"
}

=== OUTPUT FORMAT (JSON) ===
{
  "Grouped Topics": {
    "NewTopicName1": ["original_topic1", "original_topic2", ...],
    "NewTopicName2": ["original_topic3", ...],
    ...
  },
  "Grouping Rationale": "Explanation of why topics were grouped this way"
}

=== EXAMPLES ===

Example 1:
Input: 
{
  "Singing": "The user was very happy after receiving a reward from the teacher for singing national songs in the classroom",
  "Singing in the public": "The user participated in a public singing competition and was very sad that he didn't win any prize",
  "Speaking in front of others": "The user is afraid of speaking in front of others"
}

Output:
{
  "Grouped Topics": {
    "Singing performances": ["Singing", "Singing in the public"],
    "Public speaking": ["Speaking in front of others"]
  },
  "Grouping Rationale": "Grouped singing-related topics together as they both involve performance aspects, while keeping public speaking separate as it's a distinct concept"
}

Example 2:
Input:
{
  "Give up online shopping": "The user decided to give up online shopping for fear of buying fakes",
  "Online shopping": "The user was very excited because of his first successful online shopping"
}

Output:
{
  "Grouped Topics": {
    "Online shopping experiences": ["Online shopping", "Give up online shopping"]
  },
  "Grouping Rationale": "Both topics relate to the user's experiences with online shopping, despite having opposite sentiments"
}



"""


Preference_Merge_User_PROMPT =  """

Analyze the following input topics and provide the output in the specified JSON format, including both the grouped topics and your rationale for the grouping: \n

Input:
{Topic_Groups}

Output:


"""


Profile_Generation_System_PROMPT = """

Your task is to analyze the user preference from the given json concerning user's attitude towards differnt topics.

1. DATA OUTPUT REQUIREMENTS

- Analyze all entries containing ""Overall Attitude" markers
- Include both numbered rounds (e.g., [15]) and "Question round" entries

2. OUTPUT SPECIFICATIONS
=== USER PREFERENCE PROFILE ===

[POSITIVE PREFERENCES]
• [group_name]
  + Specific Activity: [exact phrase from key] (Rounds: [X][Y])
  + Reason: [verbatim from Overall Attitude where available]

[NEGATIVE PREFERENCES]
• [group_name]
  - Specific Activity: [exact phrase from key] (Rounds: [X][Y])
  - Reason: [verbatim from Overall Attitude where available]

[MIXED PREFERENCES]
• [group_name]
  + Positive Instance: [specific scenario] (Round: [X])
  - Negative Instance: [specific scenario] (Round: [Y])

3. CITATION RULES
- Always cite the exact round number from the source
- For Question round: mark as [Q]
- For duplicate rounds: show as [15][15]

4. PROCESSING INSTRUCTIONS

1. First extract all round attitudes/messages
2. Map each to its Overall Attitude explanation
3. Group by group_name
4. Categorize as Positive/Negative/Mixed
5. Maintain original phrasing from dataset
6.A topic can only be one of POSITIVE PREFERENCES, NEGATIVE PREFERENCES and MIXED PREFERENCES..




"""


Profile_Generation_User_PROMPT = """

Now analyze the following json concerning user's attitude towards difffernt topics of events. \n

Input:
{User_Preferences_json}

Output:

"""


Persona_Preference_Generation_System_PROMPT = """

Your task is to analyze the user preference from the given json concerning user's attitude towards different topics and output in a specific JSON format.

1. DATA OUTPUT REQUIREMENTS
- Analyze all entries containing "Overall Attitude" markers
- Include both numbered rounds (e.g., [15]) and "Question round" entries
- Output must be in strict JSON format as specified below

2. OUTPUT SPECIFICATIONS
{
  "Dislike": {
    "Event1":["citation1", "citation2"],
    "Event2":["citation3", "citation4"]
  },
  "Like": {
    "Event3"：["citation5", "citation6"],
    "Event4"：["citation7", "citation8"]
  },
  "Mixed Attitude": {
    "Event5"：{"Like"：[citation9, citation10], "Dislike":["citation11","citation12"]}
  }
}

3. OUTPUT RULES
- Each event must use its exact phrase from the original data
- Citations must be in square brackets as shown
- For Question round: mark as "Q"
- For duplicate rounds: show multiple instances (e.g., ["15", "15"])
- Mixed preferences must include both positive and negative citations
- Maintain original phrasing from dataset
- A topic can only appear in one category (Positive/Negative/Mixed)

4. PROCESSING INSTRUCTIONS
1. Extract all round attitudes/messages with their citations
2. Map each to its Overall Attitude explanation
3. Categorize as Positive/Negative/Mixed based on attitude
4. For Mixed preferences, include both supporting citations
5. Group events by attitude category
6. Format strictly according to the JSON template
7. Preserve exact wording from source material

"""


Persona_Preference_Generation_User_PROMPT = """

Now analyze the following json concerning user's attitude towards difffernt topics of events. \n

Input:
{User_Preferences_json}

Output:

"""


GENERATE_SYSTEM_RESPONSE_MEMX_SYSTEM_PROMPT = (
    "Your task is to choose the best option to answer the message from the user."
)

GENERATE_SYSTEM_RESPONSE_MEMX_USER_PROMPT = (
   "Your task is to choose the best option to answer the message from the user."
    "Here is the preference profile of the user:"
    "{profile}\n"
    "The message of the user is: \n" 
    "{question} \n"
    "Find the most appropriate model response base on the given user profile and give your final answer (a), (b), (c), or (d) after the special token <final_answer>."
    "{all_options}"
)


GENERATE_SYSTEM_RESPONSE_EP_RAG_SYSTEM_PROMPT = (
    "Your task is to choose the best option to answer the message from the user."
)

GENERATE_SYSTEM_RESPONSE_EP_RAG_USER_PROMPT = (
   "Your task is to choose the best option to answer the message from the user."
    "Here is the past experience of the user:"
    "{experience}\n"
    "The message of the user is: \n" 
    "{question} \n"
    "Find the most appropriate model response base on the given user profile and give your final answer (a), (b), (c), or (d) after the special token <final_answer>."
    "{all_options}"
)




Preference_Generate_System_PROMPT =  """

Given a group of topics extracted from users' messages as well as users' attitude concerning these topics, infer the user persona preference from these topics.  
Output must be in strict JSON format as specified below.

=== INPUT FORMAT ===

{
  "topic 1": "User's overall attitude concerning the events under topic 1",
  "topic 2": "User's overall attitude concerning the events under topic 2",
  ...
  "topic n": "User's overall attitude concerning the events under topic n",
}

=== OUTPUT FORMAT (JSON) ===

{
  "User preferences": [user preference 1, user preference 2 ... user preference n]
  "Reason": The reason for infering these user preferences from the input information
  "User preferences summary":several words to describe user's overall preferences
}


Example Output:
{
  "User preferences": ["play basketball","running"]
  "Reason": Users like playing basketball and running with friends, which could be inferred from the messages.
  "User preferences summary": love basketball and running.
}

"""

Preference_Generate_User_PROMPT =  """

Infer the user preferences from the following topics extracted from users' messages as well as users' coprresonding attitude concerning these topics: \n

Input:
{Topic_Groups}

Output:

"""


Attribute_Merge_System_PROMPT =  """

Given a group of attributes extracted from users' messages, you need to extract the unique attributes from them. 
Output must be in strict JSON format as specified below.


1. DATA OUTPUT REQUIREMENTS
- Carefully analyze all input attributes.
- Avoid having any similar or duplicate attributes in the output.

=== INPUT FORMAT ===

["User attribute 1", "User attribute 2", "User attribute 3" ... "User attribute n"]

=== OUTPUT FORMAT (JSON) ===

{
  "User Attributes": ["unique user attribute 1", "unique user attribute 2" ... "unique user attribute n"]
  "Reason": "The reason for infering these user attributes from the input information."
}

Example :

Input: 
  
["The user hates singing in the street","The user does't like singing in the public","The user is afraid of speaking in front of others","The user may be from US"]

Output:

{
  "User Attributes": ["The user hates singing in front of others.", "The user is from US."]
  "Reason": "The provided attributes show that the user hates singing in front of others and may be from US."
}


"""

Attribute_Merge_System_PROMPT_v2 =  """

Given a group of attributes extracted from users' messages, you need to extract the unique attributes from them. 
Output must be in strict JSON format as specified below.


1. DATA OUTPUT REQUIREMENTS

- Carefully analyze all input attributes.
- Avoid having any similar or duplicate attributes in the output.
- Label each attribute with a category label concerning a certain aspect of the user
- The attribute label must be a noun or Noun phrase representing a certain user attribute dimemsion and cannot overlap with the attribute itself.

=== INPUT FORMAT ===

["User attribute 1", "User attribute 2", "User attribute 3" ... "User attribute n"]

=== OUTPUT FORMAT (JSON) ===

{
  "User Attributes": {"attribute  1 aspect label":"unique user attribute 1", "attribute  2 aspect label": "unique user attribute 2" ... "attribute  n aspect label":"unique user attribute n"}
  "Reason": "The reason for infering these user attributes from the input information."
}

Example :

Input: 
  
["The user hates singing in the street","The user does't like singing in the public","The user is afraid of speaking in front of others","The user may be from US"]

Output:

{
  "User Attributes": ["user's singing preference":"The user hates singing in front of others.", "user's hometown":"The user is from US."]
  "Reason": "The provided attributes show that the user hates singing in front of others and may be from US."
}


"""


Attribute_Merge_User_PROMPT =  """

Infer the unique user attributes from the following attributes extracted from users' messages: \n

Input:
{User_facts}

Output:

"""