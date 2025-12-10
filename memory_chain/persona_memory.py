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
# import faiss
from collections import deque
from .utils import *
from .prompts import *
from FlagEmbedding import FlagAutoModel
from sentence_transformers import SentenceTransformer
from itertools import combinations
from collections import defaultdict
import json
from collections import defaultdict

class Persona_Memory:

    def __init__(self, persona_memory_preference_path, persona_memory_fact_path,persona_memory_attr_path,
    user_id,llm_model,client,init_persona_information,embedding_model):

        self.user_id = user_id
        self.client = client
        self.init_persona_information = init_persona_information
        self.llm_model =  llm_model
        self.persona_memory_preference_path = persona_memory_preference_path
        self.persona_memory_fact_path = persona_memory_fact_path
        self.persona_memory_attr_path = persona_memory_attr_path
        self.preference_persona = []
        self.fact_persona = []
        self.attr_persona = []
        self.aspect_attribute_dict = {}
        self.embedding_model = embedding_model

    async def update_preference_persona(self, episodic_topic_memory_list):

        episodic_memory_topic_list =  [topic["group_name"] for topic in episodic_topic_memory_list]
        topic_attitude_dict = {}
        
        for topic in episodic_topic_memory_list:
            topic_attitude_dict[topic["group_name"]] = topic["Overall Attitude"]
        
        topic_clusters =  self.cluster_related_topics(self.find_top_similar_keys(episodic_memory_topic_list, self.embedding_model))
        persona_preference_results = []    

        for cluster in topic_clusters:

            message = [{topic:topic_attitude_dict[topic]} for topic in cluster]
            preference_generate_message = [{"role": "system", "content": Preference_Generate_System_PROMPT},{"role": "user", "content": Preference_Generate_User_PROMPT.format(Topic_Groups=str(message))}]
            fact_generate_message = [{"role":"system"}]

            response = ""
            while response == "":
                try:
                    response =  await self.client.chat.completions.create(model=self.llm_model, messages = preference_generate_message, temperature = 0.3)
                    persona_preference = json.loads(response.choices[0].message.content)
                    persona_preference_results.append(persona_preference)
                except Exception as e:
                    import traceback

                    print("Error generating persona profile.")
                    print(f"Error generating profile: {str(e)}")
                    continue

            self.preference_persona = persona_preference_results
            self._save_preference_persona()
    
    async def update_attribute_persona(self, episodic_memory_attr_dict):
       
        memory_attr_list = list(episodic_memory_attr_dict.keys())
        attr_clusters =  self.cluster_related_topics(self.find_top_similar_keys(memory_attr_list, self.embedding_model))
        persona_attr_results = []    

        for cluster in attr_clusters:

            print(str(cluster))
            fact_generate_message = [{"role": "system", "content": Attribute_Merge_System_PROMPT_v2},{"role": "user", "content": Attribute_Merge_User_PROMPT.format(User_facts=str(cluster))}]
            response = ""
            while response == "":
                try:
                    response =  await self.client.chat.completions.create(model=self.llm_model, messages = fact_generate_message, temperature = 0.1)
                    persona_attr = json.loads(response.choices[0].message.content)
                    persona_attr["original attributes"] = cluster
                    persona_attr_results.append(persona_attr)
                except Exception as e:
                    import traceback
                    traceback.print_exc() 
                    response == ""
                    print(f"Error generating profile: {str(e)}")
                    continue

            self.attr_persona = persona_attr_results
            self._save_attr_persona()
        
    def _save_preference_persona(self):

        with open(self.persona_memory_preference_path, 'w', encoding='utf-8') as f:
            json.dump(self.preference_persona, f, ensure_ascii=False, indent=4)  

    def _save_fact_persona(self):

        with open(self.persona_memory_fact_path, 'w', encoding='utf-8') as f:
            json.dump(self.fact_persona_description, f, ensure_ascii=False, indent=4)  

    def _save_attr_persona(self):

        print("Generating aspect-attribute dictionary.")
        for attr_group in self.attr_persona:
            for key,value in attr_group["User Attributes"].items():
                    try:
                        if key in self.aspect_attribute_dict:
                            current = self.aspect_attribute_dict[key]
                            self.aspect_attribute_dict[key] = self.aspect_attribute_dict[key] + " " + value
                        else:
                            self.aspect_attribute_dict[key] = value
                    except:
                        print("Attribute Error")
                        print(key)
                        print(self.persona_memory_attr_path)
                        if key in self.aspect_attribute_dict:
                            current = self.aspect_attribute_dict[key]
                            self.aspect_attribute_dict[key] = str(self.aspect_attribute_dict[key]) + " " + str(value)
                        else:
                            self.aspect_attribute_dict[key] = value


        with open(self.persona_memory_attr_path, 'w', encoding='utf-8') as f:
            json.dump(self.attr_persona, f, ensure_ascii=False, indent=4)  


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
    
    def read_cache(self,preference_memory_path,attr_memory_path):

        with open(preference_memory_path,'r', encoding='utf-8') as f:
            self.preference_persona = json.load(f)
        
        with open(attr_memory_path,'r', encoding='utf-8') as f:
            self.attr_persona = json.load(f)

        self._save_preference_persona()
        self._save_attr_persona()
    


    






    


    







