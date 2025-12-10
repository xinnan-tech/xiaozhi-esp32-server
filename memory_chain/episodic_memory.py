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
import json
import numpy as np
from collections import deque
from .utils import *
from .prompts import *
from FlagEmbedding import FlagAutoModel
from sentence_transformers import SentenceTransformer
from itertools import combinations
from collections import defaultdict
import re
from collections import defaultdict
import re
from collections import OrderedDict
import random
import logging
import time 

logging.basicConfig(level=logging.WARNING)  #
logging.getLogger("FlagEmbedding").setLevel(logging.CRITICAL + 1)
logging.getLogger("FlagEmbedding").propagate = False

class Episodic_Memory:

    def __init__(self,event_episodic_memory_path,topic_episodic_memory_path,ep_cache_list_path ,attribute_episodic_memory_path,fact_episodic_memory_path,
    user_id,client,llm_model, embedding_model,cmd_args, args):

        self.user_id = user_id
        self.client = client
        self.model = llm_model
        self.embedding_model = embedding_model
        self.cmd_args = cmd_args
        self.args = args

        self.episodic_memory_cache_list = []  # Episodic memory cache for storing working memory.                    
        self.event_episodic_memory_dict = {}  # Episodic memory dictionary concerning different events (e.g., A note-taking experience)
        self.topic_episodic_memory_list = []  # Episodic memory list concerning different event topics (e.g, multiple times of note-taking experience)
        self.attribute_episodic_memory_dict = {} # Episodic memory list concerning different attributes of the user 
        self.fact_episodic_memory_dict = {} #Episodic memory list concerning different facts of the user

        self.event_episodic_memory_path = event_episodic_memory_path    
        self.topic_episodic_memory_path = topic_episodic_memory_path
        self.episodic_memory_cache_list_path = ep_cache_list_path
        self.attribute_episodic_memory_path = attribute_episodic_memory_path
        self.fact_episodic_memory_path = fact_episodic_memory_path

        ensure_directory_exists(self.event_episodic_memory_path)
        ensure_directory_exists(self.topic_episodic_memory_path)
        ensure_directory_exists(self.episodic_memory_cache_list_path)
        ensure_directory_exists(self.attribute_episodic_memory_path)
        ensure_directory_exists(self.fact_episodic_memory_path)
        
    async def evolve_event_episodic_memory(self,message_understanding,action,target):

        self.episodic_memory_cache_list.append(message_understanding)
        self._save_wm_cache_episodic_memory()
        
        index = message_understanding["index"]

        if action.upper() == "UPDATE" or action.upper() == "IGNORE":
            self.event_episodic_memory_dict[target] += "The "+ str(index)+" round message: "+ message_understanding["emotions"]+"; "
        if action.upper() == "ADD":
            self.event_episodic_memory_dict[message_understanding["topics"]] = "The "+ str(index)+" round attitude: "+ message_understanding["emotions"]+"; "     

        self._save_event_episodic_memory()
    
    async def evolve_fact_episodic_memory(self,message_understanding,action,target):
        
        index = message_understanding["index"]

        if action.upper() == "UPDATE" or action.upper() == "IGNORE":
            self.fact_episodic_memory_dict[target] += "The "+ str(index)+" round fact: "+ message_understanding["fact"]+"; "
        if action.upper() == "ADD":
            self.fact_episodic_memory_dict[message_understanding["fact"]] = "The "+ str(index)+" round fact: "+ message_understanding["fact"]+"; "    

        self._save_fact_episodic_memory()

    async def evolve_attr_episodic_memory(self,message_attribute,action,target,message_index):
        
        index = message_index
    
        if action.upper() == "UPDATE" or action.upper() == "IGNORE":
            self.attribute_episodic_memory_dict[target] += "The "+ str(index)+" round attribute: "+ message_attribute +"; "
        if action.upper() == "ADD":
            self.attribute_episodic_memory_dict[message_attribute] = "The "+ str(index)+" round attribute: "+ message_attribute +"; "     

        self._save_attr_episodic_memory()

    async def evolve_topic_episodic_memory(self):

        self.topic_episodic_memory_list = []
        event_episodic_memory_dict_keys =  list(self.event_episodic_memory_dict.keys())  
        topic_clusters =  self.cluster_related_topics(self.find_top_similar_keys(event_episodic_memory_dict_keys, self.embedding_model))
        grouped_em_results = []    # Divide the episodic memory into groups.

        for cluster in topic_clusters:

            message = {}
            for event_name in cluster:
                message[event_name] = self.value_find_topic(self.episodic_memory_cache_list,event_name)   # How to deal with this part ?

            # print(message)
            episodic_memory_merge_message = [{"role": "system", "content": Preference_Merge_System_PROMPT},{"role": "user", "content": Preference_Merge_User_PROMPT.format(Topic_Groups=str(message))}]
            
            response = ""
            while response == "":
                try:
                    response =  await self.client.chat.completions.create(model=self.model, messages = episodic_memory_merge_message, temperature = 0.3)
                    current_results = json.loads(response.choices[0].message.content)
                    for group_name in current_results["Grouped Topics"].keys():
                        current_dict_result = {}
                        current_dict_result["group_name"] =  group_name
                        for event in current_results["Grouped Topics"][group_name]:
                            current_dict_result[event] = self.event_episodic_memory_dict[event]
                        pattern = r"The (\d+) round (?:attitude|message):.*?(Positive|Negative)"
                        result = {}
                        for key,value in current_dict_result.items():
                            matches = re.findall(pattern, str(value))
                            for round_num, attitude in matches:
                                result[int(round_num)] = attitude + " "+ self.value_find_index(self.episodic_memory_cache_list,str(round_num)) # 转为整数便于排序
                        sorted_result = OrderedDict(sorted(result.items()))
                        current_dict_result["Overall Attitude"]= sorted_result
                        self.topic_episodic_memory_list.append(current_dict_result)
                except Exception as e:
                    import traceback
                    traceback.print_exc() 
                    response == ""
                    print(f"Error generating profile: {str(e)}")
                    continue
        
        self._save_topic_episodic_memory()



    def _save_event_episodic_memory(self):

        with open(self.event_episodic_memory_path,'w') as f:
            json.dump(self.event_episodic_memory_dict, f, indent=4)
    
    def _save_fact_episodic_memory(self):

        with open(self.fact_episodic_memory_path,'w') as f:
            json.dump(self.fact_episodic_memory_dict, f, indent=4)
    
    def _save_attr_episodic_memory(self):

        with open(self.attribute_episodic_memory_path,'w') as f:
            json.dump(self.attribute_episodic_memory_dict, f, indent=4)




    def _save_topic_episodic_memory(self):

        with open(self.topic_episodic_memory_path,'w') as f:
            json.dump(self.topic_episodic_memory_list, f, indent=4)

    def _save_wm_cache_episodic_memory(self):

        with open(self.episodic_memory_cache_list_path,'w') as f:
            json.dump(self.episodic_memory_cache_list, f, indent=4)

    def find_top_similar_keys(self,all_keys, embedding_model):

        key_embeddings = embedding_model.encode(all_keys)
        key_pairs = list(combinations(range(len(all_keys)), 2))
        best_matches = {}
        
        for i, j in key_pairs:
            key1 = all_keys[i]
            key2 = all_keys[j]
            sim = float(key_embeddings[i] @ key_embeddings[j].T)
            if key1 not in best_matches or sim > best_matches[key1]['similarity']:
                best_matches[key1] = {'key1': key1, 'key2': key2, 'similarity': sim}
            if key2 not in best_matches or sim > best_matches[key2]['similarity']:
                best_matches[key2] = {'key1': key2, 'key2': key1, 'similarity': sim}

        results = list(best_matches.values())
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results

    def cluster_related_topics(self,data):

        parent = {}
        def find(node):
            if parent[node] != node:
                parent[node] = find(parent[node])
            return parent[node]
        def union(node1, node2):
            root1 = find(node1)
            root2 = find(node2)
            if root1 != root2:
                parent[root2] = root1

        for item in data:
            key1, key2 = item['key1'], item['key2']
            if key1 not in parent:
                parent[key1] = key1
            if key2 not in parent:
                parent[key2] = key2
        
        for item in data:
            key1, key2 = item['key1'], item['key2']
            union(key1, key2)

        clusters = defaultdict(list)
        for node in parent:
            clusters[find(node)].append(node)

        result = [cluster for cluster in clusters.values() if len(cluster) > 1]

        return result
    def value_find_topic(self,dict_list,target_value):
    
        for item in dict_list:
            if item["topics"] == target_value:
                return item["message"]
    def value_find_index(self,dict_list,target_value):
        
        for item in dict_list:
            if item["index"] == target_value:
                return item["message"]
        
        for item in dict_list:
            if item["index"] == int(target_value):
                return item["message"]


    def read_cache(self,topic_episodic_path,event_episodic_path,episodic_cache_path,fact_episodic_path,attr_episodic_path):

        print(topic_episodic_path)
        print(event_episodic_path)
        print(episodic_cache_path)
        print(fact_episodic_path)
        print(attr_episodic_path)

        with open(topic_episodic_path, 'r', encoding='utf-8') as f:
            self.topic_episodic_memory_list = json.load(f)
        
        with open(event_episodic_path,'r', encoding='utf-8') as f:
            self.event_episodic_memory_dict = json.load(f)

        with open(episodic_cache_path,'r', encoding='utf-8') as f:
            self.episodic_memory_cache_list = json.load(f)

        with open(fact_episodic_path,'r', encoding='utf-8') as f:
            self.fact_episodic_memory_dict = json.load(f)
        
        with open(attr_episodic_path,'r', encoding='utf-8') as f:
            self.attribute_episodic_memory_dict = json.load(f)

        self._save_event_episodic_memory()
        self._save_topic_episodic_memory()
        self._save_wm_cache_episodic_memory()
        self._save_attr_episodic_memory()
        self._save_fact_episodic_memory()



