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
from .working_memory import Working_Memory
from .prompts import * 
import random
import time
import re
from nltk.corpus import stopwords
# import nltk
# nltk.download('stopwords') 
from nltk.stem import PorterStemmer
import torch
from sentence_transformers import SentenceTransformer
import string
from collections import defaultdict
import math
import torch
import torch.cuda as cuda
import concurrent.futures
import math
import string
from typing import Tuple, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor

class MemoryManager:
    def __init__(self,memory_index,memory_system,user_name,agent_name,llm_model,llm_client,cmd_args,args,embedding_model,memory_dir):

        self.memory_system = memory_system
        self.user_name = user_name
        self.agent_name = agent_name
        self.llm_model = llm_model
        self.llm_client = llm_client
        self.cmd_args = cmd_args
        self.args = args
        self.idx = memory_index
        self.client = llm_client
        self.embedding_model = embedding_model
    
        print("The No."+str(self.idx)+" sample "+user_name+" and "+ agent_name+ "'s memory manager has been established")

    async def receive_message(self,message,index,client,timestamp,user_speak):

        understanding = ""

        while len(understanding)==0:
            try:
                response = await self.llm_client.chat.completions.create(model=self.llm_model,messages=[{"role": "user", "content": UNDERSTAND_USER_EXPERIENCE_PROMPT.format(message=message)}])

                understanding= json.loads(response.choices[0].message.content) 
                if len(understanding["tags"]["topic"])!=len(understanding["tags"]["attitude"]) or  len(understanding["tags"]["attitude"])!=len(understanding["tags"]["facts"]):
                    understanding_with_index = "["+str(index)+"]: "+ understanding["summary"]
                    topics = understanding["tags"]["topic"][0]
                    emotions = understanding["tags"]["attitude"][0]
                    reason = understanding["tags"]["reason"][0]
                    fact = understanding["tags"]["facts"][0]
                    attributes = understanding["tags"]["attributes"]
                    understanding == "" 
                else:
                    understanding_with_index = "["+str(index)+"]: "+ understanding["summary"]
                    topics = understanding["tags"]["topic"][0]
                    emotions = understanding["tags"]["attitude"][0]
                    reason = understanding["tags"]["reason"][0]
                    fact = understanding["tags"]["facts"][0]
                    attributes = understanding["tags"]["attributes"]
            except:
                import traceback
                traceback.print_exc()
                understanding = ""
                continue
        

        if user_speak:
            is_full,all_messages = self.memory_system.user_working_memory.add_message_to_working_memory(raw_message=message,message=understanding_with_index,topics=topics,
            emotions=emotions,reason=reason,index=index,timestamp=timestamp,fact=fact,attribute=attributes)
            if is_full:
                oldest_user_memory_list = self.memory_system.user_working_memory.pop_oldest_working_memory()
                await self.update_user_episodic_memory(oldest_user_memory_list)
                await self.memory_system.user_episodic_memory.evolve_topic_episodic_memory()


        else:
            is_full,all_messages = self.memory_system.agent_working_memory.add_message_to_working_memory(raw_message=message,message=understanding_with_index,topics=topics,emotions=emotions,reason=reason,index=index,timestamp=timestamp,fact=fact,attribute=attributes)
            if is_full:
                oldest_agent_memory_list = self.memory_system.agent_working_memory.pop_oldest_working_memory()
                await self.update_agent_episodic_memory(oldest_agent_memory_list)
                await self.memory_system.agent_episodic_memory.evolve_topic_episodic_memory()


    
    async def understand_dialogue(self,message,index,client):

        understanding = ""

        while len(understanding)==0:
            try:
                # print("calling GPT")
                response = await client.chat.completions.create(model=self.model,messages=[{"role": "user", "content": UNDERSTAND_USER_EXPERIENCE_PROMPT_v4.format(message=message)}])
                understanding= json.loads(response.choices[0].message.content) 
                # print(understanding)
                if len(understanding["tags"]["topic"])!=len(understanding["tags"]["attitude"]):
                    understanding == ""
            except:
                import traceback
                traceback.print_exc()
                continue
        
        understanding_with_index = "["+str(index)+"]: "+ understanding["summary"]
        topics = understanding["tags"]["topic"][0]
        emotions = understanding["tags"]["attitude"][0]
        reason = understanding["tags"]["reason"][0]
        
        is_full,all_messages = self.working_memory.add_message_to_working_memory(raw_message=message,message=understanding_with_index,topics=topics,emotions=emotions,reason=reason,index=index)


    async def update_user_episodic_memory(self,user_message_understandings_list):

        for message_understanding in user_message_understandings_list:

            print("add one message understanding to user episodic memory concernng preference")
            current_user_event_episodic_memory = self.memory_system.user_episodic_memory.event_episodic_memory_dict
            action,target  = await self.wm_to_em_router(message_understanding,current_user_event_episodic_memory,self.client)
            fail_times = 0
            if action.upper()=="UPDATE" or action.upper()=="IGNORE":
                while target not in current_user_event_episodic_memory:
                    action,target  = await self.wm_to_em_router(message_understanding,current_user_event_episodic_memory,self.client)
                    fail_times += 1
                    if fail_times>=3:
                        break
            if fail_times>=3:
                continue
            await self.memory_system.user_episodic_memory.evolve_event_episodic_memory(message_understanding=message_understanding,action=action,target=target)
            print("Event episodic memory update finish.")

            message_understanding_fact =  message_understanding["fact"]
            current_user_fact_episodic_memory =  self.memory_system.user_episodic_memory.fact_episodic_memory_dict
            action,target  = await self.wm_to_em_router_fact(message_understanding_fact,current_user_fact_episodic_memory,self.client)
            
            fail_times = 0
            if action.upper()=="UPDATE" or action.upper()=="IGNORE":
                while target not in current_user_fact_episodic_memory:

                    action,target  = await self.wm_to_em_router_fact(message_understanding_fact,current_user_fact_episodic_memory,self.client)
                    fail_times += 1
                    if fail_times>=3:
                        break
            if fail_times>=3:
                continue
            await self.memory_system.user_episodic_memory.evolve_fact_episodic_memory(message_understanding=message_understanding,action=action,target=target)
            print("Fact episodic memory update finish.")
        
            message_understanding_attribute_list =  message_understanding["attribue"]

            for message_understanding_attribute in message_understanding_attribute_list:

                current_user_attr_episodic_memory =  self.memory_system.user_episodic_memory.attribute_episodic_memory_dict 
                action,target  = await self.wm_to_em_router_attr(message_understanding_attribute,list(current_user_attr_episodic_memory.keys()),self.client)
                fail_times = 0
                if action.upper()=="UPDATE" or action.upper()=="IGNORE":
                    while target not in current_user_attr_episodic_memory:

                        action,target  = await self.wm_to_em_router_attr(message_understanding_attribute,list(current_user_attr_episodic_memory.keys()),self.client)
                        fail_times += 1
                        if fail_times>=3:
                            break
                if fail_times>=3:
                    continue
                await self.memory_system.user_episodic_memory.evolve_attr_episodic_memory(message_attribute=message_understanding_attribute, 
                message_index = message_understanding["index"],action=action,target=target)

    async def update_agent_episodic_memory(self,agent_message_understandings_list):

        for message_understanding in agent_message_understandings_list:
            print("add one message understanding to agent episodic memory")
            current_agent_event_episodic_memory = self.memory_system.agent_episodic_memory.event_episodic_memory_dict
            action,target  = await self.wm_to_em_router(message_understanding,current_agent_event_episodic_memory,self.client)
            fail_times = 0
            if action.upper()=="UPDATE" or action.upper()=="IGNORE":
                while target not in current_agent_event_episodic_memory:

                    action,target  = await self.wm_to_em_router(message_understanding,current_agent_event_episodic_memory,self.client)
                    fail_times += 1
                    if fail_times>=3:
                        break
            if fail_times>=3:
                continue
            await self.memory_system.agent_episodic_memory.evolve_event_episodic_memory(message_understanding=message_understanding,action=action,target=target)
            print("Event episodic memory update finish.")

            message_understanding_fact =  message_understanding["fact"]
            current_agent_fact_episodic_memory =  self.memory_system.agent_episodic_memory.fact_episodic_memory_dict
            action,target  = await self.wm_to_em_router_fact(message_understanding_fact,list(current_agent_fact_episodic_memory.keys()),self.client)
            
            fail_times = 0
            if action.upper()=="UPDATE" or action.upper()=="IGNORE":
                while target not in current_agent_fact_episodic_memory:

                    action,target  = await self.wm_to_em_router_fact(message_understanding_fact,list(current_agent_fact_episodic_memory.keys()),self.client)
                    fail_times += 1
                    if fail_times>=3:
                        break
            if fail_times>=3:
                continue
            await self.memory_system.agent_episodic_memory.evolve_fact_episodic_memory(message_understanding=message_understanding,action=action,target=target)
            print("Fact episodic memory update finish.")

            message_understanding_attribute_list =  message_understanding["attribue"]
            for message_understanding_attribute in message_understanding_attribute_list:
                current_agent_attr_episodic_memory =  self.memory_system.agent_episodic_memory.attribute_episodic_memory_dict 
                action,target  = await self.wm_to_em_router_attr(message_understanding_attribute,list(current_agent_attr_episodic_memory.keys()),self.client)
                fail_times = 0
                if action.upper()=="UPDATE" or action.upper()=="IGNORE":
                    while target not in current_agent_attr_episodic_memory:

                        action,target  = await self.wm_to_em_router_attr(message_understanding_attribute,list(current_agent_attr_episodic_memory.keys()),self.client)
                        fail_times += 1
                        if fail_times>=3:
                            break
                if fail_times>=3:
                    continue
                await self.memory_system.agent_episodic_memory.evolve_attr_episodic_memory(message_attribute=message_understanding_attribute, 
                message_index = message_understanding["index"],action=action,target=target)
            print("Attribute episodic memory update finish.")
        
    async def update_user_episodic_memory_using_cache_message_understanding(self,user_message_understanding_cache_path):

        print(user_message_understanding_cache_path)
        with open(user_message_understanding_cache_path, 'r', encoding='utf-8') as f:
            user_message_understandings_list = json.load(f)
        for message_understanding in user_message_understandings_list:
            print("add one message understanding to episodic memory")
            current_user_event_episodic_memory = self.memory_system.user_episodic_memory.event_episodic_memory_dict
            action,target  = await self.wm_to_em_router(message_understanding,current_user_event_episodic_memory,self.client)
            if action.upper()=="UPDATE" or action.upper()=="IGNORE":
                while target not in current_user_event_episodic_memory:
                    action,target  = await self.wm_to_em_router(message_understanding,current_user_event_episodic_memory,self.client)
            await self.memory_system.user_episodic_memory.evolve_em(message_understanding=message_understanding,action=action,target=target)

    async def update_agent_episodic_memory_using_cache_message_understanding(self,agent_message_understanding_cache_path):

        print(agent_message_understanding_cache_path)
        with open(agent_message_understanding_cache_path, 'r', encoding='utf-8') as f:
            agent_message_understandings_list = json.load(f)
        for message_understanding in agent_message_understandings_list:
            print("add one message understanding to episodic memory")
            current_agent_event_episodic_memory = self.memory_system.agent_episodic_memory.event_episodic_memory_dict
            action,target  = await self.wm_to_em_router(message_understanding,current_agent_event_episodic_memory,self.client)
            if action.upper()=="UPDATE" or action.upper()=="IGNORE":
                while target not in current_agent_event_episodic_memory:
                    action,target  = await self.wm_to_em_router(message_understanding,current_agent_event_episodic_memory,self.client)
            await self.memory_system.user_episodic_memory.evolve_em(message_understanding=message_understanding,action=action,target=target)
    
    def add_message(self,user_id,message):  
    
        pass

    async def _trigger_episodic_memory_update(self,message_understanding,index):

        current_event_episodic_memory = self.episodic_memory.event_episodic_memory_dict
        action,target  = await self.wm_to_em_router(message_understanding,current_event_episodic_memory,self.client)
        
        if action.upper()=="UPDATE" or action.upper()=="IGNORE":
            while target not in current_event_episodic_memory:
                action,target  = await self.wm_to_em_router(message_understanding,current_event_episodic_memory,self.client)

        await self.episodic_memory.evolve_em(message_understanding=message_understanding,action=action,target=target)

    def create_messages_for_update_episodic_event_memory_concerning_new_message(self,episodic_event_memory,message):
        
        return [{"role": "system", "content": Message_ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": Message_ROUTER_USER_PROMPT.format(Message = message,Profile = episodic_event_memory)}]
    
    def create_messages_for_update_episodic_fact_memory_concerning_new_message(self,episodic_fact_memory,message):
        
        return [{"role": "system", "content": Message_Fact_ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": Message_ROUTER_USER_PROMPT.format(Message = message,Profile = episodic_fact_memory)}]

    def create_messages_for_update_episodic_attr_memory_concerning_new_message(self,episodic_attr_memory,message):
        
        return [{"role": "system", "content": Message_Attr_ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": Message_Attr_ROUTER_USER_PROMPT.format(Message = message,Profile = episodic_attr_memory)}]

    async def wm_to_em_router(self,message_with_understanding,episodic_event_memory_profile,client):

        '''
        The task is to determine whether to update, merge, or ignore the new message.  
        '''

        router_decision = ""

        while len(router_decision)==0:
            try:
                response = await client.chat.completions.create(model=self.llm_model,messages=self.create_messages_for_update_episodic_event_memory_concerning_new_message(episodic_event_memory=episodic_event_memory_profile,
                message=message_with_understanding))
                router_decision = json.loads(response.choices[0].message.content) 
            except:
                import traceback
                traceback.print_exc() 
                continue

        action = router_decision["Action"]
        target = router_decision["Target"]
        print("Action: "+action+" happen concerning "+target)
        return action,target 


    async def wm_to_em_router_fact(self,message_with_understanding,episodic_fact_memory_profile,client):

        '''
        The task is to determine whether to update, merge, or ignore the new message concerning the facts of the user.  
        '''

        router_decision = ""

        while len(router_decision)==0:
            try:
                response = await client.chat.completions.create(model=self.llm_model,messages=self.create_messages_for_update_episodic_fact_memory_concerning_new_message(episodic_fact_memory=episodic_fact_memory_profile,
                message=message_with_understanding))
                router_decision = json.loads(response.choices[0].message.content) 
            except:
                import traceback
                traceback.print_exc() 
                continue

        action = router_decision["Action"]
        target = router_decision["Target"]
        print("Action: "+action+" happen concerning "+target)
        return action,target
    

    async def wm_to_em_router_attr(self,message_with_understanding,episodic_attr_memory_profile,client):

        '''
        The task is to determine whether to update, merge, or ignore the new message concerning the attribute of the user.  
        '''

        router_decision = ""

        while len(router_decision)==0:
            try:
                response = await client.chat.completions.create(model=self.llm_model,messages=self.create_messages_for_update_episodic_attr_memory_concerning_new_message(episodic_attr_memory=episodic_attr_memory_profile,
                message=message_with_understanding))
                router_decision = json.loads(response.choices[0].message.content) 
                action = router_decision["Action"]
                target = router_decision["Target"]
                print("Action: "+action+" happen concerning "+target)
            except:
                import traceback
                traceback.print_exc() 
                router_decision = ""
                continue

        return action,target



    async def generate_persona_preference(self):

        self.persona_memory.generate_preference_persona(self.episodic_memory.topic_episodic_memory_list)



    # def has_word_overlap(self,sentence1, sentence2, ignore_stopwords=True):

    #     words1 = re.findall(r'\b\w+\b', sentence1.lower())
    #     words2 = re.findall(r'\b\w+\b', sentence2.lower())
        
    #     stemmer = PorterStemmer()


    #     if ignore_stopwords:
    #         stop_words = set(stopwords.words('english'))  
    #         words1 = [w for w in words1 if w not in stop_words]
    #         words2 = [w for w in words2 if w not in stop_words]
    #         words1 = [stemmer.stem(w) for w in words1]
    #         words2 = [stemmer.stem(w) for w in words2]


    #     return len(set(words1) & set(words2)) > 0

    def event_topic_mapping(self,overall_topic_dict_list,event_list,target_topics_list):
        
        event_topic_mapping_results = {}

        for event in event_list:
            for topic_info in overall_topic_dict_list:
                if event in topic_info:
                    if topic_info["group_name"] in target_topics_list:
                        event_topic_mapping_results[event]=topic_info["group_name"]
                        break
        return event_topic_mapping_results


    def message_fact_event_mapping(self,target_fact_list,overall_message_understandings,event_message_dict,target_event_list):
        
        message_event_mapping_results = {}
        round_number = None
        event_name = None

        for fact in target_fact_list:

            for message in overall_message_understandings:
                if message["fact"]==fact:
                    round_number = message["index"]
                    break
                
            for key, value in event_message_dict.items():
                if "The "+str(round_number)+" round" in value:
                    event_name = key
                    if event_name in target_event_list:
                        message_event_mapping_results[fact] = event_name
                    break
            
            # message_event_mapping_results[fact] = event_name
        return message_event_mapping_results


    def retrieve_episodic_memory(self,question):

        '''
        Retrieve message from the episodic memory concerning the question
        '''
        current_episodic_memory_list = self.episodic_memory.topic_episodic_memory_list 
        episodic_memory_string_list = [str(current_episodic_memory) for current_episodic_memory in current_episodic_memory_list]

        doc_embeddings = self.embedding_model.encode(episodic_memory_string_list)
        query_embedding = self.embedding_model.encode(question)
        similarities = np.dot(doc_embeddings, query_embedding.T)
                
        top_indices = np.argsort(similarities)[-10:][::-1]
        related_messages= [episodic_memory_string_list[i] for i in top_indices]

        return related_messages

    # def has_word_overlap(self,sentence1, sentence2, ignore_stopwords=True):

    #     words1 = re.findall(r'\b\w+\b', sentence1.lower())
    #     words2 = re.findall(r'\b\w+\b', sentence2.lower())
        
    #     stemmer = PorterStemmer()


    #     if ignore_stopwords:
    #         stop_words = set(stopwords.words('english'))
    #         words1 = [w for w in words1 if w not in stop_words]
    #         words2 = [w for w in words2 if w not in stop_words]
    #         words1 = [stemmer.stem(w) for w in words1]
    #         words2 = [stemmer.stem(w) for w in words2]


    #     return len(set(words1) & set(words2)) > 0

    
    def retrive_from_data(self,texts_being_retrieved,target_text,embedding_model,top_k):

        torch.cuda.empty_cache()                    
        initial_memory = cuda.memory_allocated()    
        cuda.reset_peak_memory_stats()              

        target_embedding = embedding_model.encode([target_text])
        retrieved_embeddings = embedding_model.encode(texts_being_retrieved)
        

        target_embedding = torch.nn.functional.normalize(target_embedding, p=2, dim=1)
        retrieved_embeddings = torch.nn.functional.normalize(retrieved_embeddings, p=2, dim=1)
        similarities = torch.mm(target_embedding, retrieved_embeddings.T)[0]  # (1, n_texts) -> (n_texts,)
        peak_memory = cuda.max_memory_allocated()  

        peak_memory_number = peak_memory / 1024**2
        peak_memory_number_increase = (peak_memory - initial_memory) / 1024**2

        peak_memory = cuda.max_memory_allocated() 
        net_peak_memory = peak_memory - initial_memory  

        top_scores, top_indices = torch.topk(similarities, k=top_k)
        # top_results = [ (texts_being_retrieved[idx], score.item()) for score, idx in zip(top_scores, top_indices)]
        top_results = [ texts_being_retrieved[idx] for score, idx in zip(top_scores, top_indices)]
        return top_results, top_scores,peak_memory_number,peak_memory_number_increase



    def link_fact_to_cache_message_number(self,episodic_memory,fact):

        all_fact_related_round_info = episodic_memory.fact_episodic_memory_dict[fact]
        round_numbers = re.findall(r"The (\d+) round fact:", all_fact_related_round_info)
        return round_numbers

    

    def locate_fact_context_details(self,episodic_memory,round_number_list):
        
        results = []
        for round_number in round_number_list:
            for message in episodic_memory.episodic_memory_cache_list:
                if  str(message["index"])==str(round_number):
                    results.append([message["raw_message"],message["timestamp"]])

        return results

    def locate_cache_episodic_message(self,episodic_memory,round_number_list):
        
        results = []
        for round_number in round_number_list:
            for message in episodic_memory.episodic_memory_cache_list:
                if  str(message["index"])==str(round_number):
                    results.append(message["timestamp"])
        return results

    def locate_cache_episodic_message_fact_raw_message_timestamp(self,episodic_memory,round_number_list):
        
        results = []
        for round_number in round_number_list:
            for message in episodic_memory.episodic_memory_cache_list:
                if  str(message["index"])==str(round_number):
                    results.append([message["fact"],message["raw_message"],message["timestamp"]])
        return results



    def activate_fact_memory_match(self,fact_scores,drop_threshold):
        
        '''
        修复断层点前的记忆集群
        '''
        
        # 处理空列表的情况
        if not fact_scores or len(fact_scores) == 0:
            return None

         # 计算标准化下降比例（相对于最大值）
        max_score = max(fact_scores)
        if max_score == 0:
            return None
            
        breaks = []
        drop_threshold = drop_threshold  # 10%阈值
        
        for i in range(1, len(fact_scores)):
            drop = (fact_scores[i-1] - fact_scores[i]) / max_score
            if drop > drop_threshold:
                return i

        return None


    @staticmethod
    def retrive_from_data(texts_being_retrieved,target_text,embedding_model,top_k):

        # torch.cuda.empty_cache()
        # cuda.reset_peak_memory_stats()  # 重置峰值统计
        torch.cuda.empty_cache()                    # 清空缓存，确保测量准确
        initial_memory = cuda.memory_allocated()    # 获取初始显存占用（基准线）
        cuda.reset_peak_memory_stats()              # 重置峰值统计

        target_embedding = embedding_model.encode([target_text])
        retrieved_embeddings = embedding_model.encode(texts_being_retrieved)
        
        # GPU-optimized cosine similarity (避免数据转移到CPU)
        target_embedding = torch.nn.functional.normalize(target_embedding, p=2, dim=1)
        retrieved_embeddings = torch.nn.functional.normalize(retrieved_embeddings, p=2, dim=1)
        similarities = torch.mm(target_embedding, retrieved_embeddings.T)[0]  # (1, n_texts) -> (n_texts,)
        peak_memory = cuda.max_memory_allocated()  # 返回字节数
        # 获取Top-K结果（全程GPU）
        # top_scores, top_indices = torch.topk(similarities, k=top_k)
        # # 立即获取峰值显存占用
        # print(f"峰值显存占用: {peak_memory / 1024**2:.2f} MB")
        # print(f"峰值净增显存: {(peak_memory - initial_memory) / 1024**2:.2f} MB")
        peak_memory_number = peak_memory / 1024**2
        peak_memory_number_increase = (peak_memory - initial_memory) / 1024**2
        # top_scores, top_indices = torch.topk(similarities, k=top_k)
        # 立即获取峰值显存占用
        peak_memory = cuda.max_memory_allocated()  # 返回字节数
        net_peak_memory = peak_memory - initial_memory  # 计算净增峰值
        print(f"峰值显存占用: {peak_memory / 1024**2:.2f} MB")
        print(f"峰值净增显存: {net_peak_memory / 1024**2:.2f} MB")  # 这是最关键的指标！
        # print(f"峰值显存占用: {peak_memory / 1024**2:.2f} MB")
        top_scores, top_indices = torch.topk(similarities, k=top_k)
        # top_results = [ (texts_being_retrieved[idx], score.item()) for score, idx in zip(top_scores, top_indices)]
        top_results = [ texts_being_retrieved[idx] for score, idx in zip(top_scores, top_indices)]
        return top_results, top_scores,peak_memory_number,peak_memory_number_increase





    def retrive_from_data_attr_fact(self, texts_list_1, texts_list_2, target_text, embedding_model, top_k):

        """
        同时处理两个文本列表的检索，使用批量编码
        """

        torch.cuda.empty_cache()
        initial_memory = torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        
        # 编码目标文本（单独编码，因为需要特殊处理）
        target_embedding = embedding_model.encode([target_text])
        target_embedding = torch.tensor(target_embedding)
        
        # 批量编码：将两个列表合并进行一次编码
        all_texts = texts_list_1 + texts_list_2  # 这会创建一个新列表，包含两个列表的所有元素
        all_embeddings = embedding_model.encode(all_texts, batch_size=32)
        all_embeddings = torch.tensor(all_embeddings)
        
        # 正确分割嵌入结果
        n1 = len(texts_list_1)
        n2 = len(texts_list_2)
        
        # 分割点：第一个列表的结束位置
        retrieved_embeddings_1 = all_embeddings[:n1]          # 前n1个是第一个列表
        retrieved_embeddings_2 = all_embeddings[n1:n1 + n2]   # 接下来的n2个是第二个列表
        
        # 验证分割是否正确
        assert len(retrieved_embeddings_1) == n1, f"分割错误: expected {n1}, got {len(retrieved_embeddings_1)}"
        assert len(retrieved_embeddings_2) == n2, f"分割错误: expected {n2}, got {len(retrieved_embeddings_2)}"
        
        # 归一化
        target_embedding = torch.nn.functional.normalize(target_embedding, p=2, dim=1)
        retrieved_embeddings_1 = torch.nn.functional.normalize(retrieved_embeddings_1, p=2, dim=1)
        retrieved_embeddings_2 = torch.nn.functional.normalize(retrieved_embeddings_2, p=2, dim=1)
        
        # 合并的矩阵乘法
        all_retrieved_embeddings = torch.cat([retrieved_embeddings_1, retrieved_embeddings_2], dim=0)
        all_similarities = torch.mm(target_embedding, all_retrieved_embeddings.T)[0]
        
        # 分割相似度结果
        similarities_1 = all_similarities[:n1]
        similarities_2 = all_similarities[n1:n1 + n2]
        
        # 获取峰值内存
        if torch.cuda.is_available():
            peak_memory = torch.cuda.max_memory_allocated()
            peak_memory_number = peak_memory / 1024**2
            peak_memory_number_increase = (peak_memory - initial_memory) / 1024**2
        else:
            peak_memory_number = 0
            peak_memory_number_increase = 0
        
        # 获取Top-K结果
        top_scores_1, top_indices_1 = torch.topk(similarities_1, k=min(top_k, len(similarities_1)))
        top_scores_2, top_indices_2 = torch.topk(similarities_2, k=min(top_k, len(similarities_2)))
        
        top_results_1 = [texts_list_1[idx] for idx in top_indices_1]
        top_results_2 = [texts_list_2[idx] for idx in top_indices_2]
        
        return (
            top_results_1, top_scores_1.tolist(),
            top_results_2, top_scores_2.tolist(),
            peak_memory_number, peak_memory_number_increase)
    

    def retrive_from_data_attr_fact_topic(self, texts_list_1, texts_list_2, texts_list_3, target_text, embedding_model, top_k):

        torch.cuda.empty_cache()
        initial_memory = torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        
        # 编码目标文本
        target_embedding = embedding_model.encode([target_text])
        target_embedding = torch.tensor(target_embedding)
        
        # 批量编码：将三个列表合并进行一次编码
        all_texts = texts_list_1 + texts_list_2 + texts_list_3
        all_embeddings = embedding_model.encode(all_texts,batch_size=64)
        all_embeddings = torch.tensor(all_embeddings)
        
        # 正确分割嵌入结果
        n1 = len(texts_list_1)
        n2 = len(texts_list_2)
        n3 = len(texts_list_3)
        
        # 分割点
        retrieved_embeddings_1 = all_embeddings[:n1]                     # 前n1个是第一个列表
        retrieved_embeddings_2 = all_embeddings[n1:n1 + n2]             # 接下来的n2个是第二个列表
        retrieved_embeddings_3 = all_embeddings[n1 + n2:n1 + n2 + n3]   # 最后的n3个是第三个列表
        
        # 验证分割是否正确
        assert len(retrieved_embeddings_1) == n1, f"分割错误: expected {n1}, got {len(retrieved_embeddings_1)}"
        assert len(retrieved_embeddings_2) == n2, f"分割错误: expected {n2}, got {len(retrieved_embeddings_2)}"
        assert len(retrieved_embeddings_3) == n3, f"分割错误: expected {n3}, got {len(retrieved_embeddings_3)}"
        
        # 归一化
        target_embedding = torch.nn.functional.normalize(target_embedding, p=2, dim=1)
        retrieved_embeddings_1 = torch.nn.functional.normalize(retrieved_embeddings_1, p=2, dim=1)
        retrieved_embeddings_2 = torch.nn.functional.normalize(retrieved_embeddings_2, p=2, dim=1)
        retrieved_embeddings_3 = torch.nn.functional.normalize(retrieved_embeddings_3, p=2, dim=1)
        
        # 合并的矩阵乘法
        all_retrieved_embeddings = torch.cat([
            retrieved_embeddings_1, 
            retrieved_embeddings_2, 
            retrieved_embeddings_3
        ], dim=0)
        
        all_similarities = torch.mm(target_embedding, all_retrieved_embeddings.T)[0]
        
        # 分割相似度结果
        similarities_1 = all_similarities[:n1]
        similarities_2 = all_similarities[n1:n1 + n2]
        similarities_3 = all_similarities[n1 + n2:n1 + n2 + n3]
        
        # 获取峰值内存
        if torch.cuda.is_available():
            peak_memory = torch.cuda.max_memory_allocated()
            peak_memory_number = peak_memory / 1024**2
            peak_memory_number_increase = (peak_memory - initial_memory) / 1024**2
        else:
            peak_memory_number = 0
            peak_memory_number_increase = 0
        
        # # 获取Top-K结果
        # 49.48 1656
        # top_scores_1, top_indices_1 = torch.topk(similarities_1, k=min(top_k+8, len(similarities_1)))
        # top_scores_2, top_indices_2 = torch.topk(similarities_2, k=min(top_k+8, len(similarities_2)))
        # top_scores_3, top_indices_3 = torch.topk(similarities_3, k=min(top_k-3, len(similarities_3)))

        # 获取Top-K结果 50.33 1593
        # top_scores_1, top_indices_1 = torch.topk(similarities_1, k=min(top_k, len(similarities_1)))
        # top_scores_2, top_indices_2 = torch.topk(similarities_2, k=min(top_k+12, len(similarities_2)))
        # top_scores_3, top_indices_3 = torch.topk(similarities_3, k=min(top_k-5, len(similarities_3)))

        # 51.57
        # top_scores_1, top_indices_1 = torch.topk(similarities_1, k=min(top_k-7, len(similarities_1)))
        # top_scores_2, top_indices_2 = torch.topk(similarities_2, k=min(top_k-2, len(similarities_2)))
        # top_scores_3, top_indices_3 = torch.topk(similarities_3, k=min(top_k+7, len(similarities_3)))

        # 51.43        
        # top_scores_1, top_indices_1 = torch.topk(similarities_1, k=min(top_k-7, len(similarities_1)))
        # top_scores_2, top_indices_2 = torch.topk(similarities_2, k=min(top_k-3, len(similarities_2)))
        # top_scores_3, top_indices_3 = torch.topk(similarities_3, k=min(top_k+8, len(similarities_3)))
        
        # 51.56 1615        
        # top_scores_1, top_indices_1 = torch.topk(similarities_1, k=min(top_k-8, len(similarities_1)))
        # top_scores_2, top_indices_2 = torch.topk(similarities_2, k=min(top_k-2, len(similarities_2)))
        # top_scores_3, top_indices_3 = torch.topk(similarities_3, k=min(top_k+9, len(similarities_3)))

        top_scores_1, top_indices_1 = torch.topk(similarities_1, k=min(top_k-9, len(similarities_1)))
        top_scores_2, top_indices_2 = torch.topk(similarities_2, k=min(top_k-1, len(similarities_2)))
        top_scores_3, top_indices_3 = torch.topk(similarities_3, k=min(top_k+8, len(similarities_3)))
        



        top_results_1 = [texts_list_1[idx] for idx in top_indices_1]
        top_results_2 = [texts_list_2[idx] for idx in top_indices_2]
        top_results_3 = [texts_list_3[idx] for idx in top_indices_3]
        
        return (
            top_results_1, top_scores_1.tolist(),
            top_results_2, top_scores_2.tolist(),
            top_results_3, top_scores_3.tolist(),
            peak_memory_number, peak_memory_number_increase
        )






    def retrieve_from_memory_soft_segmentation(self,question,topn,drop_threshold):

        '''
        启发式记忆检索 We need to retrieve from memory heuristically.
        '''

        print("version v5 retrieval")

        if self.user_name in question:
            user_name = self.user_name 
            agent_name = self.agent_name 
            retrieved_memory_word_details = self.memory_system.user_detail_dict 
            retrieved_topic_memory_dict = self.memory_system.user_topic_message_dict
            retrieved_working_memory =  self.memory_system.user_working_memory
            retrieved_episodic_memory = self.memory_system.user_episodic_memory
            retrieved_persona_memory = self.memory_system.user_persona_memory
        else:
            user_name = self.agent_name 
            agent_name = self.user_name 
            retrieved_memory_word_details = self.memory_system.agent_detail_dict 
            retrieved_topic_memory_dict = self.memory_system.agent_topic_message_dict
            retrieved_working_memory = self.memory_system.agent_working_memory 
            retrieved_episodic_memory = self.memory_system.agent_episodic_memory
            retrieved_persona_memory = self.memory_system.agent_persona_memory

        persona_attributes = [attribute_aspect.replace("self.user_name","") for attribute_group in retrieved_persona_memory.attr_persona for attribute_aspect in list(attribute_group["User Attributes"].keys())]
        print("There are "+str(len(persona_attributes)) + " pieces of persona memory attributes for "+retrieved_persona_memory.user_id)
        persona_facts = list(retrieved_episodic_memory.fact_episodic_memory_dict.keys())
        print("There are "+str(len(persona_facts) )+ " pieces of persona memory facts for "+retrieved_persona_memory.user_id)
        
        # retrieved_persona_aspects, aspect_scores,peak_memory_number_1,peak_memory_number_increase_1  = self.retrive_from_data(list(set(persona_attributes)),question,self.embedding_model,int(topn))
        # selected_retrieved_persona_facts,fact_scores,peak_memory_number_2,peak_memory_number_increase_2 = self.retrive_from_data(persona_facts,question,self.embedding_model,topn)
        all_context_messages_list = retrieved_episodic_memory.episodic_memory_cache_list + list(retrieved_working_memory.working_memory_queue.queue)
        print("There are "+str(len(all_context_messages_list) )+ " pieces of working memory messages for "+retrieved_persona_memory.user_id)
        all_context_messages_list = [context_message["topics"] for context_message in all_context_messages_list]        
        retrieved_persona_aspects, aspect_scores, selected_retrieved_persona_facts,fact_scores, retrieved_context_topics,topic_scores,peak_memory_number_1, peak_memory_number_increase_1 = self.retrive_from_data_attr_fact_topic(persona_attributes,persona_facts,all_context_messages_list,question,self.embedding_model,int(topn))
        # result1, scores1, result2, scores2, result3, scores3, peak_mem, peak_mem_inc = \
        # retrieve_from_three_lists(list1, list2, list3, target_text, model, top_k=5)
        print(question)
        print(aspect_scores)
        print(np.mean(aspect_scores))
        print(fact_scores)
        print(np.mean(fact_scores))
        print(topic_scores)
        print(np.mean(topic_scores))

        # # 获取结果
        # retrieved_persona_aspects, aspect_scores, peak_memory_number_1, peak_memory_number_increase_1 = future1.result()
        # selected_retrieved_persona_facts, fact_scores, peak_memory_number_2, peak_memory_number_increase_2 = future2.result()

        print(retrieved_persona_aspects)
        retrieved_persona_attributes = [retrieved_persona_memory.aspect_attribute_dict[aspect] for aspect in retrieved_persona_aspects]
        print(retrieved_persona_attributes)
        retrieved_persona_facts = [(fact,self.locate_cache_episodic_message(retrieved_episodic_memory,self.link_fact_to_cache_message_number(retrieved_episodic_memory,fact))) for fact in selected_retrieved_persona_facts] 
        all_retrieved_persona_facts = [item[0] for item in retrieved_persona_facts]
        print("Overall facts: "+str(retrieved_persona_facts))

        # persona_facts = list(retrieved_episodic_memory.fact_episodic_memory_dict.keys())
        # print("There are "+str(len(persona_facts) )+ " pieces of persona memory facts for "+retrieved_persona_memory.user_id)
        # selected_retrieved_persona_facts,fact_scores,peak_memory_number_2,peak_memory_number_increase_2 = self.retrive_from_data(persona_facts,question,self.embedding_model,topn)
        # retrieved_persona_facts = [(fact,self.locate_cache_episodic_message(retrieved_episodic_memory,self.link_fact_to_cache_message_number(retrieved_episodic_memory,fact))) for fact in selected_retrieved_persona_facts] 
        # all_retrieved_persona_facts = [item[0] for item in retrieved_persona_facts]
        # print("Overall facts: "+str(retrieved_persona_facts))

        # Fact Detail Recovery
        activated_facts_place = self.activate_fact_memory_match(fact_scores,drop_threshold)
        activated_fact_context_messages = []
        flattened_activated_fact_context_messages = []
        flattened_reserved_fact_context_messages = []
        flattened_reserved_fact_index = []

        if activated_facts_place!=None:
            for i in range(activated_facts_place):
                activated_fact_context_messages.append(self.locate_fact_context_details(retrieved_episodic_memory,self.link_fact_to_cache_message_number(retrieved_episodic_memory,retrieved_persona_facts[i][0])))
                flattened_activated_fact_context_messages += self.locate_fact_context_details(retrieved_episodic_memory,self.link_fact_to_cache_message_number(retrieved_episodic_memory,retrieved_persona_facts[i][0]))
            retrieved_persona_facts = retrieved_persona_facts[len(activated_fact_context_messages):]
        else:
            activated_facts_place = 0
            activated_fact_context_messages = []

        for i in range(len(retrieved_persona_facts)):
            # activated_fact_context_messages.append(self.locate_fact_context_details(retrieved_episodic_memory,self.link_fact_to_cache_message_number(retrieved_episodic_memory,retrieved_persona_facts[i][0])))
            flattened_reserved_fact_context_messages += self.locate_fact_context_details(retrieved_episodic_memory,self.link_fact_to_cache_message_number(retrieved_episodic_memory,retrieved_persona_facts[i][0]))
            # flattened_reserved_fact_context_messages = [message[0] for message in flattened_reserved_fact_context_messages]
            flattened_reserved_fact_index.append(i)

        flattened_reserved_fact_context_messages_only_message_content = [message[0] for message in flattened_reserved_fact_context_messages]

        potential_keyword = None
        ignored_details_facts = []
        question_word_list_distribute_dict = {}
        question_word_list = list(set(question.translate(str.maketrans('', '', string.punctuation)).split()))
        for word in  question_word_list:
            if word.lower() != user_name.lower():
                question_word_list_distribute_dict[word.lower()] = retrieved_memory_word_details[word.lower()]
        print(question_word_list_distribute_dict)

        # all_context_messages_list = retrieved_episodic_memory.episodic_memory_cache_list + list(retrieved_working_memory.working_memory_queue.queue)
        # print("There are "+str(len(all_context_messages_list) )+ " pieces of working memory messages for "+retrieved_persona_memory.user_id)
        # all_context_messages_list = [context_message["topics"] for context_message in all_context_messages_list]
        # retrieved_context_topics,topic_socres,peak_memory_number_3,peak_memory_number_increase_3 = self.retrive_from_data(all_context_messages_list,question,self.embedding_model,topn-len(activated_fact_context_messages))
        
        retrieved_context_messages = [retrieved_topic_memory_dict[retrieved_context_topic] for retrieved_context_topic in retrieved_context_topics] 
        original_context_messages = retrieved_context_messages
        raw_original_fact_message = [message[0] for message in [retrieved_topic_memory_dict[retrieved_context_topic] for retrieved_context_topic in retrieved_context_topics]] 

        for message in flattened_activated_fact_context_messages :
            if message[0] not in raw_original_fact_message:
                retrieved_context_messages = [[message[0],message[1]]] + retrieved_context_messages 
        
        retrieval_context_raw_messages = [message[0] for message in retrieved_context_messages]
        print(retrieval_context_raw_messages)
        TF_IDF_record_dict = {}

        for word in question_word_list_distribute_dict.keys():
            if len(question_word_list_distribute_dict[word])>0:
                TF_IDF_record_dict[word]= 1*math.log(1/(len(question_word_list_distribute_dict[word])+1))

        keyword_message=[]

        if  len(TF_IDF_record_dict.keys())>0:
            potential_keyword = sorted(TF_IDF_record_dict.items(), key=lambda x: x[1], reverse=True)[0][0]
            potential_docs = question_word_list_distribute_dict[potential_keyword]
            detail_results = self.locate_cache_episodic_message_fact_raw_message_timestamp(retrieved_episodic_memory,potential_docs)
            for detail_result in detail_results:
                if detail_result[1] not in set(retrieval_context_raw_messages):
                    retrieved_context_messages.append([detail_result[1],detail_result[2]])
                    keyword_message.append((detail_result[1],detail_result[2]))

        retrieved_context_messages_only_message_content = [message[0] for message in retrieved_context_messages]

        # print(len(retrieved_persona_facts))
        # print(len(flattened_reserved_fact_context_messages_only_message_content))

        for i in range(len(flattened_reserved_fact_context_messages_only_message_content)):
            if flattened_reserved_fact_context_messages_only_message_content[i] in retrieved_context_messages_only_message_content:
                try:
                    print(flattened_reserved_fact_context_messages_only_message_content[i],retrieved_context_messages_only_message_content)
                    print("index")
                    print(i)
                    retrieved_persona_facts[i]=[]
                except:
                    continue
                
        # max_memory = max(peak_memory_number_1,peak_memory_number_2,peak_memory_number_3)
        # max_increase_memory = max(peak_memory_number_increase_1,peak_memory_number_increase_2,peak_memory_number_increase_3)

        max_memory = max(peak_memory_number_1,peak_memory_number_1)
        max_increase_memory = max(peak_memory_number_increase_1,peak_memory_number_increase_1)
        # retrieved_persona_attributes = None
        # retrieved_persona_facts = None

        return {"keyword message":keyword_message,"keyword distribution dict":question_word_list_distribute_dict,"ignored_details_keywords":potential_keyword ,"ignored_facts":ignored_details_facts,"persona attributes":retrieved_persona_attributes,"persona facts":retrieved_persona_facts,"fact scores":fact_scores,"retrieved context messages":retrieved_context_messages, "recover facts num":len(activated_fact_context_messages),"original context message":original_context_messages},user_name, agent_name,max_memory,max_increase_memory


    def _prepare_persona_attributes(self, retrieved_persona_memory):
        """准备persona attributes数据"""
        return [attribute_aspect.replace("self.user_name", "") 
                for attribute_group in retrieved_persona_memory.attr_persona 
                for attribute_aspect in list(attribute_group["User Attributes"].keys())]

    def _prepare_persona_facts(self, retrieved_episodic_memory):
        """准备persona facts数据"""
        return list(retrieved_episodic_memory.fact_episodic_memory_dict.keys())

    def _prepare_context_data(self, question, user_name, retrieved_memory_word_details, 
                            retrieved_episodic_memory, retrieved_working_memory):
        """准备context数据和TF-IDF数据"""
        # 处理question words
        question_word_list = list(set(question.translate(str.maketrans('', '', string.punctuation)).split()))
        question_word_list_distribute_dict = {}
        
        for word in question_word_list:
            if word.lower() != user_name.lower():
                question_word_list_distribute_dict[word.lower()] = retrieved_memory_word_details[word.lower()]
        
        # 准备context messages
        all_context_messages_list = (retrieved_episodic_memory.episodic_memory_cache_list + 
                                list(retrieved_working_memory.working_memory_queue.queue))
        all_context_messages_list = [context_message["topics"] for context_message in all_context_messages_list]
        
        return {
            "question_word_list_distribute_dict": question_word_list_distribute_dict,
            "all_context_messages_list": all_context_messages_list
        }

    def _process_single_fact(self, retrieved_episodic_memory, fact):
        """处理单个fact的定位"""
        cache_message = self.locate_cache_episodic_message(
            retrieved_episodic_memory,
            self.link_fact_to_cache_message_number(retrieved_episodic_memory, fact)
        )
        return (fact, cache_message)

    def _process_activated_fact(self, retrieved_episodic_memory, fact):
        """处理activated fact的上下文"""
        activated_context = self.locate_fact_context_details(
            retrieved_episodic_memory,
            self.link_fact_to_cache_message_number(retrieved_episodic_memory, fact)
        )
        flattened_context = self.locate_fact_context_details(
            retrieved_episodic_memory,
            self.link_fact_to_cache_message_number(retrieved_episodic_memory, fact)
        )
        return activated_context, flattened_context




    async def generate_system_response(self,query,restrieval_result,client,speaker_a,speaker_b,llm_model):

        retrieval_attributes = f"【Persona Attributes】 \n" + str(restrieval_result["persona attributes"])
        # retrieval_facts = f"【Persona Facts】 \n" + str(restrieval_result["persona facts"]) + str(restrieval_result["working memory facts"])
        retrieval_facts = f"【Persona Facts】 \n" + str(restrieval_result["persona facts"])
        retrieval_context_messages = restrieval_result["retrieved context messages"]
        retrieval_preferences = ""  # We will add this section later.
       
        system_prompt = (
            f"You are role-playing as {speaker_b} in a conversation with the user is playing is {speaker_a}. "
            f"Your task is to answer questions about {speaker_a} or {speaker_b} in an extremely concise manner base on the provided information context concenring {speaker_a}.\n"
            f"Any content referring to 'User' in the context refers to {speaker_a}'s content."
            f"The provided information include:\n"
            f"i). The fact of {speaker_a} and the timestamp when the {speaker_a} share the fact to you. You need to infer the timing of the fact happening from the fact message and timestamps.\n"
            f"ii). The attributes of {speaker_a}\n"
            f"iii). The context messages from {speaker_a} as well as  the timestamp when the {speaker_a} send the message to you.\n"
            f"For example, when the fact is (\"I play basktetball last year.\", 8 May, 2023). You need to infer that the user play basketball play basketball in the pervisous year of 2023, which is 2022." 
            f"When the question is: \"What did the charity race raise awareness for?\", you should not answer in the form of: \"The charity race raised awareness for mental health.\" Instead, it should be: \"mental health\", as this is more concise."
            f"Remember, you must try your best to deduce clear answers from facts and attributes rather than give vague answers."
        )
        
        user_prompt = (
            f"<CONTEXT>\n"
            f"<User Attributes>\n"
            f"Attributes concerning {speaker_a}\n"
            f"{retrieval_attributes}\n"
            f"<The context messages from {speaker_a} as well as  the timestamp when the {speaker_a} send the message to you>\n"
            f"{retrieval_context_messages}\n"
            f"<Other User Fact Message and the timestamp when the user sharing the fact>\n"
            f"Facts of {speaker_a}:\n"
            f"{retrieval_facts}\n"
            f"the question is: {query}\n"
            f"Your task is to answer questions about {speaker_a} or {speaker_b} in an extremely concise manner.\n"
            f"Please only provide the content of the answer, without including 'answer:'\n"
            f"For questions that require answering a date or time, strictly follow the format \"15 July 2023\" and provide a specific date whenever possible. For example, if you need to answer \"last year,\" give the specific year of last year rather than just saying \"last year.\" Only provide one year, date, or time, without any extra responses.\n"
            f"If the question is about the duration, answer in the form of several years, months, or days.\n"
            f"Generate answers primarily composed of concrete entities, such as Mentoring program, school speech, etc"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}]
        

        response = ""
        while (response==""):
            try:
                response = await client.chat.completions.create(model=llm_model, messages=messages, temperature=0.7, max_tokens=2000)
                answer = response.choices[0].message.content
                token_consumption = response
            except:
                continue

        return answer,response.usage.total_tokens
        # return response






    



        


        
