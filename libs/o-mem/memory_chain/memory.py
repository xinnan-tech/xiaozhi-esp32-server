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
import os
import json
from .utils import *

from .prompts import *
from .memory_manager import *
from .persona_memory import *
from .working_memory import *
from .memory_manager import *
from .episodic_memory import *
from datetime import datetime
import string
from collections import defaultdict

# Heat threshold for triggering profile/knowledge update from mid-term memory
H_PROFILE_UPDATE_THRESHOLD = 5.0 
DEFAULT_ASSISTANT_ID = "default_assistant_profile"

def get_current_time():
    now = datetime.now()  
    local_time_str = now.strftime("%Y-%m-%d %H:%M:%S")  
    return local_time_str 

class MemoryChain:

    def __init__(self,memory_index,llm_model,llm_client,embedding_model,user_name,agent_name,args,cmd_args,memory_dir): 

            
        self.idx = memory_index
        self.args = args
        self.cmd_args = cmd_args
        self.client = llm_client
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.user_name = user_name
        self.agent_name = agent_name
        self.memory_dir = memory_dir
        current_time = get_current_time()

        self.user_topic_message_dict = {}
        self.agent_topic_message_dict = {}
        self.user_detail_dict = defaultdict(list)
        self.agent_detail_dict = defaultdict(list)


        print("The No."+str(self.idx)+" sample "+user_name+" and "+ agent_name+ "'s memory system has been established")
    
        user_working_memory_path = os.path.join(self.memory_dir, "user_working_memory_"+str(self.idx)+".json")        # User working memory
        agent_working_memory_path = os.path.join(self.memory_dir, "agent_working_memory_"+str(self.idx)+".json")      # Agent working memory             

        user_event_episodic_memory_path = os.path.join(self.memory_dir,  "user_event_episodic_memory_"+str(self.idx)+".json")        
        agent_event_episodic_memory_path = os.path.join(self.memory_dir, "agent_event_episodic_memory_"+str(self.idx)+".json")      

        user_fact_episodic_memory_path = os.path.join(self.memory_dir, "user_fact_episodic_memory_"+str(self.idx)+".json")        
        agent_fact_episodic_memory_path = os.path.join(self.memory_dir, "agent_fact_episodic_memory_"+str(self.idx)+".json") 

        user_attribute_episodic_memory_path = os.path.join(self.memory_dir, "user_attribute_episodic_memory_"+str(self.idx)+".json")        
        agent_attribute_episodic_memory_path = os.path.join(self.memory_dir, "agent_attribute_episodic_memory_"+str(self.idx)+".json") 
        
        user_topic_episodic_memory_path = os.path.join(self.memory_dir, "user_topic_episodic_memory_"+str(self.idx)+".json")  
        agent_topic_episodic_memory_path = os.path.join(self.memory_dir, "agent_topic_episodic_memory_"+str(self.idx)+".json")  

        user_episodic_memory_wm_cache_path = os.path.join(self.memory_dir, "user_wm_cache_episodic_memory_"+str(self.idx)+".json")  
        agent_episodic_memory_wm_cache_path = os.path.join(self.memory_dir, "agent_wm_cache_episodic_memory_"+str(self.idx)+".json")  
        
        user_persona_memory_preference_path = os.path.join(self.memory_dir, "user_persona_memory_preference_"+str(self.idx)+".json")    
        agent_persona_memory_preference_path = os.path.join(self.memory_dir, "agent_persona_memory_preference_"+str(self.idx)+".json")    

        user_persona_memory_fact_path = os.path.join(self.memory_dir, "user_persona_memory_fact_"+str(self.idx)+".json")                
        agent_persona_memory_fact_path = os.path.join(self.memory_dir, "agent_persona_memory_fact_"+str(self.idx)+".json")  

        user_persona_memory_attr_path = os.path.join(self.memory_dir, "user_persona_memory_attr_"+str(self.idx)+".json")                
        agent_persona_memory_attr_path = os.path.join(self.memory_dir, "agent_persona_memory_attr_"+str(self.idx)+".json")  

        self.user_memory_detail_path = os.path.join(self.memory_dir, "user_detail_"+str(self.idx)+".json")                
        self.agent_memory_detail_path = os.path.join(self.memory_dir, "agent_detail_"+str(self.idx)+".json")  

        ensure_directory_exists(user_working_memory_path)                                                                  
        ensure_directory_exists(agent_working_memory_path) 
        ensure_directory_exists(user_event_episodic_memory_path) 
        ensure_directory_exists(agent_event_episodic_memory_path)
        ensure_directory_exists(user_topic_episodic_memory_path)   
        ensure_directory_exists(agent_topic_episodic_memory_path)
        ensure_directory_exists(user_episodic_memory_wm_cache_path)   
        ensure_directory_exists(agent_episodic_memory_wm_cache_path )
        ensure_directory_exists(user_persona_memory_preference_path)   
        ensure_directory_exists(agent_persona_memory_preference_path)
        ensure_directory_exists(user_persona_memory_fact_path)   
        ensure_directory_exists(agent_persona_memory_fact_path)
        ensure_directory_exists(user_fact_episodic_memory_path)   
        ensure_directory_exists(user_attribute_episodic_memory_path)
        ensure_directory_exists(agent_fact_episodic_memory_path )   
        ensure_directory_exists(agent_attribute_episodic_memory_path)
        
        self.user_working_memory = Working_Memory(working_memory_path = user_working_memory_path, user_id = self.user_name, model=self.llm_model,              
        working_memory_max_size = cmd_args.working_memory_max_size, client=self.client,refresh_rate= cmd_args.episodic_memory_refresh_rate)

        self.agent_working_memory = Working_Memory(working_memory_path = agent_working_memory_path, user_id = self.agent_name, model=self.llm_model,              
        working_memory_max_size = cmd_args.working_memory_max_size, client=self.client,refresh_rate= cmd_args.episodic_memory_refresh_rate)

        self.user_episodic_memory = Episodic_Memory(event_episodic_memory_path = user_event_episodic_memory_path, topic_episodic_memory_path = user_topic_episodic_memory_path,
        ep_cache_list_path = user_episodic_memory_wm_cache_path, user_id = user_name, client = self.client, llm_model = self.llm_model, embedding_model = self.embedding_model,
        fact_episodic_memory_path = user_fact_episodic_memory_path,attribute_episodic_memory_path = user_attribute_episodic_memory_path,cmd_args = self.cmd_args, args = self.args) 
       
        self.agent_episodic_memory = Episodic_Memory(event_episodic_memory_path = agent_event_episodic_memory_path, topic_episodic_memory_path = agent_topic_episodic_memory_path,
        ep_cache_list_path = agent_episodic_memory_wm_cache_path, user_id = agent_name, client = self.client, llm_model = self.llm_model, embedding_model = self.embedding_model,
        fact_episodic_memory_path = agent_fact_episodic_memory_path,attribute_episodic_memory_path = agent_attribute_episodic_memory_path,cmd_args = self.cmd_args, args = self.args) 

        self.user_persona_memory = Persona_Memory(persona_memory_preference_path = user_persona_memory_preference_path, persona_memory_fact_path = user_persona_memory_fact_path, 
        user_id = self.user_name, llm_model=self.llm_model, client=self.client,init_persona_information="",embedding_model=self.embedding_model,
        persona_memory_attr_path = user_persona_memory_attr_path)

        self.agent_persona_memory = Persona_Memory(persona_memory_preference_path = agent_persona_memory_preference_path, persona_memory_fact_path = agent_persona_memory_fact_path,
        user_id = self.agent_name, llm_model=self.llm_model, client=self.client,init_persona_information="",embedding_model=self.embedding_model,
        persona_memory_attr_path = agent_persona_memory_attr_path)



     
        
        for message in list(self.user_working_memory.working_memory_queue.queue)+self.user_episodic_memory.episodic_memory_cache_list:
             self.user_topic_message_dict[message["topics"]] = [message["raw_message"],message["timestamp"]]
        
        for message in list(self.agent_working_memory.working_memory_queue.queue)+self.agent_episodic_memory.episodic_memory_cache_list:
             self.agent_topic_message_dict[message["topics"]] = [message["raw_message"],message["timestamp"]]   

    def generate_memory_detail_map(self):
        
        stop_words = {
        'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
        'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so', 'than',
        'such', 'both', 'through', 'about', 'for', 'is', 'of', 'while', 'during',
        'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under',
        'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where',
        'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most',
        'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
        'so', 'than', 'too', 'very', 'can', 'will', 'just', 'should', 'now',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
        'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their', 'mine',
        'yours', 'hers', 'ours', 'theirs', 'myself', 'yourself', 'himself',
        'herself', 'itself', 'ourselves', 'yourselves', 'themselves',self.user_name,self.agent_name}

        print("Generating Detail Map")
        user_full_memory_list = [(message["index"],message["raw_message"])  for message in list(self.user_working_memory.working_memory_queue.queue) + self.user_episodic_memory.episodic_memory_cache_list]
        agent_full_memory_list = [(message["index"],message["raw_message"])  for message in list(self.agent_working_memory.working_memory_queue.queue) + self.agent_episodic_memory.episodic_memory_cache_list]
        
        # round = 0
        for index,text in user_full_memory_list:
            text = text.translate(str.maketrans('', '', string.punctuation))
            word_list = text.split()
            for word in word_list:
                word = word.lower()
                if word not in stop_words:
                    self.user_detail_dict[word].append(index)
            
        for index,text in agent_full_memory_list:
            text = text.translate(str.maketrans('', '', string.punctuation))
            word_list = text.split()
            for word in word_list:
                word = word.lower()
                if word not in stop_words:
                    self.agent_detail_dict[word].append(index)
        
        with open(self.user_memory_detail_path, 'w', encoding='utf-8') as f:
            json.dump( self.user_detail_dict, f, ensure_ascii=False, indent=4)  
        
        with open(self.agent_memory_detail_path, 'w', encoding='utf-8') as f:
            json.dump( self.agent_detail_dict, f, ensure_ascii=False, indent=4)  

    def find_memory_file(self,directory, pattern):

        regex = re.compile(f"{pattern}$") 
        for filename in os.listdir(directory):
            if regex.search(filename):
                return os.path.join(directory,filename) 
        return None  
    async def read_cache_memory(self, cache_memory_dir):

        cache_user_working_memory_pattern =  f"user_working_memory_{self.idx}.json"
        cache_agent_working_memory_pattern = f"agent_working_memory_{self.idx}.json"

        cache_user_topic_episodic_memory_pattern =  f"user_topic_episodic_memory_{self.idx}.json"
        cache_agent_topic_episodic_memory_pattern = f"agent_topic_episodic_memory_{self.idx}.json"
        
        cache_user_event_episodic_memory_pattern =   f"user_event_episodic_memory_{self.idx}.json"
        cache_agent_event_episodic_memory_pattern =  f"agent_event_episodic_memory_{self.idx}.json"

        cache_user_fact_episodic_memory_pattern =  f"user_fact_episodic_memory_{self.idx}.json"
        cache_agent_fact_episodic_memory_pattern = f"agent_fact_episodic_memory_{self.idx}.json"
        
        cache_user_attr_episodic_memory_pattern =   f"user_attribute_episodic_memory_{self.idx}.json"
        cache_agent_attr_episodic_memory_pattern =  f"agent_attribute_episodic_memory_{self.idx}.json"

        cache_user_wm_cache_episodic_memory_pattern =   f"user_wm_cache_episodic_memory_{self.idx}.json"
        cache_agent_wm_cache_episodic_memory_pattern =  f"agent_wm_cache_episodic_memory_{self.idx}.json"

        cache_user_preferences_persona_memory_pattern =  f"user_persona_memory_preference_{self.idx}.json"
        cache_agent_preferences_persona_memory_pattern = f"agent_persona_memory_preference_{self.idx}.json"

        cache_user_attributes_persona_memory_pattern =  f"user_persona_memory_attr_{self.idx}.json"
        cache_agent_attributes_persona_memory_pattern = f"agent_persona_memory_attr_{self.idx}.json"


        # fact_episodic_path,attr_episodic_path

        self.user_working_memory.read_cache(self.find_memory_file(cache_memory_dir,cache_user_working_memory_pattern))
        self.agent_working_memory.read_cache(self.find_memory_file(cache_memory_dir,cache_agent_working_memory_pattern))

        self.user_episodic_memory.read_cache(self.find_memory_file(cache_memory_dir,cache_user_topic_episodic_memory_pattern),self.find_memory_file(cache_memory_dir,
        cache_user_event_episodic_memory_pattern),self.find_memory_file(cache_memory_dir,cache_user_wm_cache_episodic_memory_pattern),
        self.find_memory_file(cache_memory_dir,cache_user_fact_episodic_memory_pattern),
        self.find_memory_file(cache_memory_dir,cache_user_attr_episodic_memory_pattern))
        
        self.agent_episodic_memory.read_cache(self.find_memory_file(cache_memory_dir,cache_agent_topic_episodic_memory_pattern),self.find_memory_file(cache_memory_dir,
        cache_agent_event_episodic_memory_pattern),self.find_memory_file(cache_memory_dir,cache_agent_wm_cache_episodic_memory_pattern),
        self.find_memory_file(cache_memory_dir,cache_agent_fact_episodic_memory_pattern),
        self.find_memory_file(cache_memory_dir,cache_agent_attr_episodic_memory_pattern))

        self.user_persona_memory.read_cache(self.find_memory_file(cache_memory_dir,cache_user_preferences_persona_memory_pattern),
        self.find_memory_file(cache_memory_dir,cache_user_attributes_persona_memory_pattern))
        
        self.agent_persona_memory.read_cache(self.find_memory_file(cache_memory_dir,cache_agent_preferences_persona_memory_pattern),
        self.find_memory_file(cache_memory_dir,cache_agent_attributes_persona_memory_pattern))

        self.user_topic_message_dict = {}
        self.agent_topic_message_dict = {}

        for message in list(self.user_working_memory.working_memory_queue.queue)+self.user_episodic_memory.episodic_memory_cache_list:
             self.user_topic_message_dict[message["topics"]] = [message["raw_message"],message["timestamp"]]
        
        for message in list(self.agent_working_memory.working_memory_queue.queue)+self.agent_episodic_memory.episodic_memory_cache_list:
             self.agent_topic_message_dict[message["topics"]] = [message["raw_message"],message["timestamp"]]



    async def receive_user_message(self,message,round_index,client,timestamp):

        await self.user_memory_manager.understand_message(message,round_index,client)

    async def receive_agent_message(self,message,round_index,client,timestamp):
    
        await self.agent_memory_manager.understand_message(message,round_index,client)

    async def receive_user_message_v2(self,previous_query,user_message,round_index,client):

        await self.user_memory_manager.understand_message(message,round_index,client)

    async def receive_agent_message_v2(self,previous_query, user_message,round_index,client):
    
        await self.agent_memory_manager.understand_message(message,round_index,client)





    def get_response_base_on_profile_reorganization(self,query,all_options):

        """
        Generates a response to the user's query through reorganizing the latest profile.
        """        

        print(f"Generating response for query: '{query[:50]}...'")
        # raw_reorganized_user_profile_text, original_profile = self.personal_memory.reorganize_profile_base_on_query(query)
        raw_reorganized_user_profile_text, original_profile = self.personal_memory.reorganize_profile_base_on_query_and_option(query,all_options)
        reorganized_profile = f"【User Profile】\n{raw_reorganized_user_profile_text}"

        system_prompt_text = GENERATE_SYSTEM_RESPONSE_SYSTEM_PROMPT.format(background=reorganized_profile)
        user_prompt_text = GENERATE_SYSTEM_RESPONSE_USER_PROMPT.format(question= query,all_options=all_options)

        messages = [
            {"role": "system", "content": system_prompt_text},
            {"role": "user", "content": user_prompt_text}
        ]

        response_content = self.client.chat.completions.create(
            model=self.model, 
            messages=messages, 
            temperature=0.7, 
            max_tokens=1500 # As in original main
        )

        self.receive_message(query,self.user_id,"Question",self.client)
        
        return response_content.choices[0].message.content, reorganized_profile, original_profile



        







    def get_response_base_on_profile(self,query,all_options):

        """
        Generates a response to the user's query base on the latest profile.
        """

        print(f"Generating response for query: '{query[:50]}...'")

        raw_user_profile_text = self.personal_memory.get_user_profile_data()
        background_context = f"【User Profile】\n{raw_user_profile_text}"
        system_prompt_text = GENERATE_SYSTEM_RESPONSE_SYSTEM_PROMPT
        user_prompt_text = GENERATE_SYSTEM_RESPONSE_USER_PROMPT.format(
            background=background_context,
            question= query,
            all_options=all_options
        )
        
        messages = [
            {"role": "system", "content": system_prompt_text},
            {"role": "user", "content": user_prompt_text}
        ]

        response_content = self.client.chat.completions.create(
            model=self.model, 
            messages=messages, 
            temperature=0.7, 
            max_tokens=1500 # As in original main
        )

        self.receive_message(query,self.user_id,"Question",self.client)
        return response_content.choices[0].message.content, background_context 


    async def get_response_base_on_memx_profile(self,query,all_options):

        """
        Generates a response to the user's query base on the latest profile.
        """

        persona_profile = self.persona_memory.generate_preference_persona(self.episodic_memory.topic_episodic_memory_list)


        system_prompt_text = GENERATE_SYSTEM_RESPONSE_MEMX_SYSTEM_PROMPT
        user_prompt_text = GENERATE_SYSTEM_RESPONSE_MEMX_USER_PROMPT.format(
            profile = persona_profile,
            question= query,
            all_options=all_options
        )


        
        messages = [
            {"role": "system", "content": system_prompt_text},
            {"role": "user", "content": user_prompt_text}
        ]

        response_content = await self.client.chat.completions.create(
            model=self.model, 
            messages=messages, 
            temperature=0.7, 
            max_tokens=1500 # As in original main
        )

        return response_content.choices[0].message.content, persona_profile






    def get_response_base_on_profile(self,query,all_options):

        """
        Generates a response to the user's query base on the profile.
        """
        print(f"Generating response for query: '{query[:50]}...'")

        # 1. Retrieve context
        raw_user_profile_text = self.personal_memory.get_user_profile_data()

        


        background_context = f"【User Profile】\n{raw_user_profile_text}"

        system_prompt_text = GENERATE_SYSTEM_RESPONSE_SYSTEM_PROMPT
        user_prompt_text = GENERATE_SYSTEM_RESPONSE_USER_PROMPT.format(
            background=background_context,
            question= query,
            all_options=all_options
        )
        
        
        messages = [
            {"role": "system", "content": system_prompt_text},
            {"role": "user", "content": user_prompt_text}
        ]

        response_content = self.client.chat.completions.create(
            model=self.model, 
            messages=messages, 
            temperature=0.7, 
            max_tokens=1500 # As in original main 
        )


        self.receive_message(query,self.user_id,"Question",self.client)
        return response_content.choices[0].message.content, background_context 

    def get_response_base_on_profile_v2(self,query,all_options):

        """
        Generates a response to the user's query base on the profile.
        """
        print(f"Generating response for query: '{query[:50]}...'")

        # 1. Retrieve context

        self.personal_memory.merge_user_trace_profile_into_user_preference_profile()

        raw_user_profile_text = self.personal_memory.get_user_profile_data()
        background_context = f"【User Profile】\n{raw_user_profile_text}"
        
    #    system_prompt_text = GENERATE_SYSTEM_RESPONSE_SYSTEM_PROMPT
        user_prompt_text = GENERATE_SYSTEM_RESPONSE_USER_PROMPT.format(
                background=background_context,
                question= query,
                all_options=all_options)
    
        messages = [{"role": "user", "content": user_prompt_text}]

        # 2. Call LLM for response
        # print("Memoryos: Calling LLM for final response generation...")
        response_content = self.client.chat.completions.create(
            model=self.model, 
            messages=messages, 
            temperature=0, 
            max_tokens=16000
        )

        # 3. Add this interaction to memory
        self.receive_message(query,self.user_id,"Question",self.client)
        return response_content.choices[0].message.content, background_context

    async def get_response_base_on_recent_message(self,query,all_options,working_memory):

        """
        Generates a response to the user's query base on the profile.
        """
        print(f"Generating response for query: '{query[:50]}...'")

    #    system_prompt_text = GENERATE_SYSTEM_RESPONSE_SYSTEM_PROMPT
        
        system_prompt_text = GENERATE_SYSTEM_RESPONSE_ONLY_WM_SYSTEM_PROMPT
        user_prompt_text = GENERATE_SYSTEM_RESPONSE_ONLY_WM_USER_PROMPT.format(messages= working_memory,question= query,all_options=all_options)

        messages = [
            {"role": "system", "content": system_prompt_text},
            {"role": "user", "content": user_prompt_text}
        ]

        # 2. Call LLM for response
        # print("Memoryos: Calling LLM for final response generation...")
        response_content = await self.client.chat.completions.create(
            model=self.model, 
            messages=messages, 
            temperature=0, 
            max_tokens=16000
        )

        # 3. Add this interaction to memory
        return response_content.choices[0].message.content

    async def get_response_base_on_init_persona(self,query,all_options,init_persona):

        """
        Generates a response to the user's query base on the profile.
        """

        print(f"Generating response for query: '{query[:50]}...'")

    #    system_prompt_text = GENERATE_SYSTEM_RESPONSE_SYSTEM_PROMPT
        
        system_prompt_text = GENERATE_SYSTEM_RESPONSE_ONLY_WM_SYSTEM_PROMPT
        user_prompt_text = GENERATE_SYSTEM_RESPONSE_ONLY_INIT_PROFILE_PROMPT.format(persona= init_persona,question= query,all_options=all_options)

        messages = [
            {"role": "system", "content": system_prompt_text},
            {"role": "user", "content": user_prompt_text}
        ]

        # 2. Call LLM for response
        # print("Memoryos: Calling LLM for final response generation...")
        response_content = await self.client.chat.completions.create(
            model=self.model, 
            messages=messages, 
            temperature=0, 
            max_tokens=16000
        )

        # 3. Add this interaction to memory
        return response_content.choices[0].message.content


    def get_response_base_on_reorganized_profile(self,query,all_options,reorganzied_profile):

        """
        Generates a response to the user's query base on the profile.
        """
        print(f"Generating response for query: '{query[:50]}...'")

        # 1. Retrieve context

        raw_user_profile_text = str(reorganzied_profile)
        background_context = f"【User Profile】\n{raw_user_profile_text}"

        system_prompt_text = GENERATE_SYSTEM_RESPONSE_SYSTEM_PROMPT
        user_prompt_text = GENERATE_SYSTEM_RESPONSE_USER_PROMPT.format(
            background=background_context,
            question= query,
            all_options=all_options
        )
        
        messages = [
            {"role": "system", "content": system_prompt_text},
            {"role": "user", "content": user_prompt_text}
        ]

        # 2. Call LLM for response
        # print("Memoryos: Calling LLM for final response generation...")
        response_content = self.client.chat.completions.create(
            model=self.model, 
            messages=messages, 
            temperature=0.7, 
            max_tokens=1500 # As in original main 
        )

        # 3. Add this interaction to memory
        self.receive_message(query,self.user_id,"Question",self.client)
        return response_content.choices[0].message.content, self.personal_memory.get_user_profile_data()




    def reorganize_profile_base_on_message(self,message):

        """
        Only extract the sections of the profile which are important for current user message as well as provide the reasons behind it.
        """

        print(f"Reorganize the profile base on the user message: {message[:50]}...")

        profile = self.personal_memory.latest_profile
        system_prompt_text = Profile_Reorganization_SYSTEM_PROMPT
        user_prompt_text = Profile_Reorganization_USER_PROMPT.format(Message = message,Profile = profile)
        
        messages = [{"role": "system", "content": system_prompt_text},{"role": "user", "content": user_prompt_text}]
        reorganized_profile = ""
        
        while(reorganized_profile==""):
            response = self.client.chat.completions.create(
                model=self.model, 
                messages=messages, 
                temperature=0.7, 
                max_tokens=2000)    
            reorganized_profile = json.loads(response.choices[0].message.content)

        print(reorganized_profile)
        return reorganized_profile["relevant_profile"],reorganized_profile["summary"]


    async def get_response_base_on_episodic_memory_retrieval(self,query,all_options):

        """
        Generates a response to the user's query base on the latest profile.
        """

        # persona_profile = self.persona_memory.generate_preference_persona(self.episodic_memory.topic_episodic_memory_list)
        experience = str(self.memory_manager.retrieve_episodic_memory(query))
        system_prompt_text = GENERATE_SYSTEM_RESPONSE_EP_RAG_SYSTEM_PROMPT 
        user_prompt_text = GENERATE_SYSTEM_RESPONSE_EP_RAG_USER_PROMPT.format(experience = experience,question= query,all_options=all_options)
        messages = [{"role": "system", "content": system_prompt_text},{"role": "user", "content": user_prompt_text}]
        response_content = await self.client.chat.completions.create(model=self.model, messages=messages, temperature=0.7, max_tokens=1500)

        # self.receive_message(query,self.user_id,"Question",self.client)
        return response_content.choices[0].message.content, experience
