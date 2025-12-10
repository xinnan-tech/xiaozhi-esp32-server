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
from datetime import datetime, timedelta
import re
import openai
import time
import tiktoken
import os
import asyncio
import aiofiles
from tqdm.asyncio import tqdm_asyncio
from memory_chain import *
from openai import AsyncOpenAI
import yaml
import argparse
import torch
import time
from typing import List, Union, Dict
from concurrent.futures import ProcessPoolExecutor

try:
    with open('config.yaml', 'r') as file:
        args = yaml.safe_load(file)
except Exception as e:
    print(e)
    print('Error reading the config file')
client = AsyncOpenAI(base_url=args["model"]["openai_base_url"],api_key=args["model"]["openai_api_key"])


def get_timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

class ParallelSentenceTransformer:
    def __init__(self, model: SentenceTransformer):
        self.model = model
        # Enable DataParallel only in multi-GPU environment
        if torch.cuda.device_count() > 1:
            self.model = torch.nn.DataParallel(model)
            print(f"Using {torch.cuda.device_count()} GPUs!")
        else:
            print("Using single GPU or CPU")

    def encode(self, texts: Union[str, List[str]], 
               batch_size: int = 32,
               convert_to_tensor: bool = True,
               **kwargs) -> torch.Tensor:
        """
        Multi-GPU friendly encoding method with automatic batching and cross-device processing.
        Args:
            texts: Input text (single string or list)
            batch_size: Batch size per GPU
            convert_to_tensor: Whether to return tensor
        """
        # Normalize input format
        if isinstance(texts, str):
            texts = [texts]
        
        # Get current device (primary GPU)
        device = self.model.device_ids[0] if isinstance(self.model, torch.nn.DataParallel) \
                 else next(self.model.parameters()).device
        
        # Batch processing (avoid single GPU memory overflow)
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Tokenization (must be executed on primary GPU)
            features = self.model.module.tokenize(batch) if hasattr(self.model, 'module') \
                      else self.model.tokenize(batch)
            features = {k: v.to(device) for k, v in features.items()}
            
            # Multi-GPU forward propagation
            with torch.no_grad():
                outputs = self.model(features)
                embeddings = outputs['sentence_embedding']
                all_embeddings.append(embeddings if convert_to_tensor else embeddings.cpu().numpy())
        
        # Merge results
        return torch.cat(all_embeddings, dim=0) if convert_to_tensor \
               else np.concatenate(all_embeddings, axis=0)

print("Loading embedding model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
embedding_model = ParallelSentenceTransformer(SentenceTransformer("all-MiniLM-L6-v2").to(device))
# path = 'your model'
# embedding_model = ParallelSentenceTransformer(SentenceTransformer(path).to(device))
async def update_user_profile_from_top_segment(mid_mem, long_mem, sample_id, client):
    
    print("update the profiles of the users.")

async def generate_system_response_with_memx(query, short_mem, long_mem, retrieval_queue, long_konwledge, client, sample_id, speaker_a, speaker_b, meta_data,no_mtm,no_ltm,no_wm):
    
    """
    These codes are referenced from memory os.
    """

    if no_wm == True:
         history_text = ""
    else:
        history = short_mem.get_all()
        history_text_list = [
            f"{speaker_a}: {qa.get('user_input', '')}\n{speaker_b}: {qa.get('agent_response', '')}\nTime: ({qa.get('timestamp', '')})" 
            for qa in history]
    
    if no_mtm == True:
        retrieval_text = ""
    else:
        retrieval_text = "\n".join([
            f"【Historical Memory】 {speaker_a}: {page.get('user_input', '')}\n{speaker_b}: {page.get('agent_response', '')}\nTime:({page.get('timestamp', '')})\nConversation chain overview:({page.get('meta_info', '')})\n" 
            for page in retrieval_queue])
    
    if no_ltm == True:
        user_profile_text = ""
    else:
        profile_obj = long_mem.get_user_profile(sample_id)
        user_profile_text = str(profile_obj.get("data", "None")) if profile_obj else "None"
    
    background = f"【User Profile】\n{user_profile_text}\n\n"
    for kn in long_konwledge:
        background += f"{kn['knowledge']}\n"
    background = re.sub(r'(?i)\buser\b', speaker_a, background)
    background= re.sub(r'(?i)\bassistant\b', speaker_b, background)
    assistant_knowledge = long_mem.get_assistant_knowledge()
    assistant_knowledge_text = "【Assistant Knowledge】\n"
    for ak in assistant_knowledge:
        assistant_knowledge_text += f"- {ak['knowledge']} ({ak['timestamp']})\n"

    assistant_knowledge_text = re.sub(r'\bI\b', speaker_b, assistant_knowledge_text)
    
    system_prompt = (
        f"You are role-playing as {speaker_b} in a conversation with the user is playing is  {speaker_a}. "
        f"Here are some of your character traits and knowledge:\n{assistant_knowledge_text}\n"
        f"Any content referring to 'User' in the prompt refers to {speaker_a}'s content, and any content referring to 'AI'or 'assiant' refers to {speaker_b}'s content."
        f"Your task is to answer questions about {speaker_a} or {speaker_b} in an extremely concise manner.\n"
        f"When the question is: \"What did the charity race raise awareness for?\", you should not answer in the form of: \"The charity race raised awareness for mental health.\" Instead, it should be: \"mental health\", as this is more concise."
    )
    
    user_prompt = (
        f"<CONTEXT>\n"
        f"Recent conversation between {speaker_a} and {speaker_b}:\n"
        f"{history_text}\n\n"
        f"<MEMORY>\n"
        f"Relevant past conversations:\n"
        f"{retrieval_text}\n\n"
        f"<CHARACTER TRAITS>\n"
        f"Characteristics of {speaker_a}:\n"
        f"{background}\n\n"
        f"the question is: {query}\n"
        f"Your task is to answer questions about {speaker_a} or {speaker_b} in an extremely concise manner.\n"
        f"Please only provide the content of the answer, without including 'answer:'\n"
        f"For questions that require answering a date or time, strictly follow the format \"15 July 2023\" and provide a specific date whenever possible. For example, if you need to answer \"last year,\" give the specific year of last year rather than just saying \"last year.\" Only provide one year, date, or time, without any extra responses.\n"
        f"If the question is about the duration, answer in the form of several years, months, or days.\n"
        f"Generate answers primarily composed of concrete entities, such as Mentoring program, school speech, etc"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    response = await client.chat_completion(model="gpt-4o-mini", messages=messages, temperature=0.7, max_tokens=2000)
    return response, system_prompt, user_prompt

def process_conversation(conversation_data):
    
    """
    These codes are referenced from memory os.
    Process conversation data from locomo10 format into memory system format.
    Handles both text-only and image-containing messages.
    """

    processed = []
    speaker_a = conversation_data["speaker_a"]
    speaker_b = conversation_data["speaker_b"]

    session_keys = [key for key in conversation_data.keys() if key.startswith("session_") and not key.endswith("_date_time")]
    
    for session_key in session_keys:

        timestamp_key = f"{session_key}_date_time"
        timestamp = conversation_data.get(timestamp_key, "")
        
        for dialog in conversation_data[session_key]:

            speaker = dialog["speaker"]
            text = dialog["text"]

            if "blip_caption" in dialog and dialog["blip_caption"]:
                text = f"{text} (image description: {dialog['blip_caption']})"

            if speaker == speaker_a:
                processed.append({speaker_a: text,"timestamp": timestamp})
            else:
                processed.append({speaker_b: text, "timestamp": timestamp})
    
    return processed


import os
import re

def find_agent_memory_file(directory, idx):

    pattern = re.compile(rf'^.*_agent_working_memory_{idx}\.json$')
    for filename in os.listdir(directory):
        if pattern.match(filename):
            return os.path.join(directory,filename) 
    return None  

def find_user_memory_file(directory, idx):

    pattern = re.compile(rf'^.*_user_working_memory_{idx}\.json$')
    for filename in os.listdir(directory):
        if pattern.match(filename):
            return os.path.join(directory,filename) 
    return None  

async def run_locomo_experiment(idx,args,cmd_args,client):

    os.makedirs("mem_tmp_loco_final", exist_ok=True)
    try:
        with open("locomo10.json", "r", encoding="utf-8") as f:
            dataset = json.load(f)
    except FileNotFoundError:
        print("Error: locomo10.json file not found, please ensure it is in the current directory")
        return
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return

    output_file = cmd_args.response_output_dir+"/HippoIndex_results_"+str(idx)+".json"
    results = []
    total_samples = len(dataset)
    sample = dataset[idx]

    print(f"Processing sample {idx + 1}/{total_samples}: {sample.get('sample_id', 'unknown')}")
    
    sample_id = sample.get("sample_id", "unknown_sample")
    conversation_data = sample["conversation"]
    qa_pairs = sample["qa"]
    qa_count = len(qa_pairs)
    processed_dialogs = process_conversation(conversation_data)
    
    print(f"This sample has {len(processed_dialogs)} dialog turns")
    print(f"This sample has {len(qa_pairs)} questions")

    if not processed_dialogs:
        print(f"Sample {sample_id} has no valid conversation data, skipping")
        return 
        
    speaker_a = conversation_data["speaker_a"]
    speaker_b = conversation_data["speaker_b"]

    memory_dir = cmd_args.output_dir
    
    memory_system = MemoryChain(memory_index=idx, llm_model=args["model"]["llm_model"],llm_client = client,embedding_model = embedding_model,
    user_name= speaker_a, agent_name = speaker_b, cmd_args=cmd_args, args=args, memory_dir = memory_dir)

    memory_manager = MemoryManager(memory_index=idx, memory_system=memory_system,llm_model=args["model"]["llm_model"],llm_client = client,
    embedding_model = embedding_model,user_name= speaker_a, agent_name = speaker_b, cmd_args=cmd_args, args=args, memory_dir = memory_dir)

    if cmd_args.use_all_memory_cache:
        await memory_system.read_cache_memory(cmd_args.memory_cache_path)
        memory_system.generate_memory_detail_map()
        print("Memory system load cache  memory finish")
        # qa_count = len(qa_pairs)
    else:
        print("Stage 1: We indexing the memory base.")
        for index,dialog in  enumerate(processed_dialogs):
            timestamp =  get_timestamp()
            if speaker_a in dialog:
                user_speak = True
                start_time = time.time()
                await memory_manager.receive_message(message = dialog[speaker_a], client=client,index=index,timestamp=dialog["timestamp"], user_speak=user_speak)
                end_time = time.time()  # Record end time
                elapsed = end_time - start_time  # Calculate elapsed time (seconds)
                print(f"Receive one new message took: {elapsed:.4f} seconds") 
            else:
                user_speak = False
                start_time = time.time()
                await memory_manager.receive_message(message = dialog[speaker_b],client=client,index=index,timestamp=dialog["timestamp"],user_speak = user_speak)
                end_time = time.time()  # Record end time
                elapsed = end_time - start_time  # Calculate elapsed time (seconds)
                print(f"Receive one new message took: {elapsed:.4f} seconds") 

        await memory_system.agent_persona_memory.update_preference_persona(memory_system.agent_episodic_memory.topic_episodic_memory_list)
        await memory_system.agent_persona_memory.update_attribute_persona(memory_system.agent_episodic_memory.attribute_episodic_memory_dict)
        await memory_system.user_persona_memory.update_preference_persona(memory_system.user_episodic_memory.topic_episodic_memory_list)
        await memory_system.user_persona_memory.update_attribute_persona(memory_system.user_episodic_memory.attribute_episodic_memory_dict)
        return 

    for qa_idx, qa in enumerate(qa_pairs):

        start_time =  time.time()
        print(f"Processing QA {qa_idx + 1}/{qa_count}")

        question = qa["question"]
        original_answer = qa.get("answer", "")
        category = qa["category"]
        evidence = qa.get("evidence", "")

        if(original_answer == ""):
            # continue
            original_answer = qa.get("adversarial_answer", "")

        # retrieval_result, user_name, agent_name = memory_manager.retrieve_from_memory_soft_segmentation_v5(question,cmd_args.number_of_retrieval_pieces,cmd_args.drop_threshold)
        retrieval_result, user_name, agent_name,peak_memory_number,peak_memory_number_increase = memory_manager.retrieve_from_memory_soft_segmentation(question,cmd_args.number_of_retrieval_pieces,cmd_args.drop_threshold)
        # retrieval_result, user_name, agent_name,peak_memory_number,peak_memory_number_increase = memory_manager.retrieve_from_memory_soft_segmentation_v9_ablation_study(question,cmd_args.number_of_retrieval_pieces,cmd_args.drop_threshold)
        answer,tokens_consumption = await memory_manager.generate_system_response(question,retrieval_result,client,user_name,agent_name,args["model"]["llm_model"])
        end_time =  time.time()
        elapsed_time = end_time - start_time


        results.append({"time":elapsed_time,"sample_id": sample_id,"user": user_name,"agent": agent_name,"question": question,"answer":answer,"reference_answer": original_answer,"category": category,
        "evidence": evidence,"persona attributes":retrieval_result["persona attributes"],"fact scores":retrieval_result["fact scores"],"persona facts": retrieval_result["persona facts"],
        "retrieved context messages":retrieval_result["retrieved context messages"],"fact recovery num":retrieval_result["recover facts num"],"ignored details keywords": retrieval_result["ignored_details_keywords"],
        "ignored facts":retrieval_result["ignored_facts"],"keyword distribution dict":retrieval_result["keyword distribution dict"],"keyword message":retrieval_result["keyword message"],"original retrievals":retrieval_result["original context message"],"token consumption":tokens_consumption,
        "peak memory":peak_memory_number,"peak_memory_number_increase":peak_memory_number_increase})

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"Sample {idx + 1} processing complete, results saved to {output_file}")
        except Exception as e:
            print(f"Error saving results: {e}")
            import traceback
            traceback.print_exc() 
            print(f"Final error saving results: {e}")
async def run_one(idx,args,cmd_args,client):

    async with semaphore:       
        result = await run_locomo_experiment(idx=idx,args=args,cmd_args=cmd_args,client=client)
        return result

semaphore = asyncio.Semaphore(10)

async def main():

    parser = argparse.ArgumentParser(description='Command line arguments')
    parser.add_argument('--working_memory_max_size',type=int, default=20, help = 'the maximum size of the working memory')
    parser.add_argument('--episodic_memory_refresh_rate',type=int, default=5, help = 'the rate ti refresh episodic memory')
    parser.add_argument('--output_dir',type=str, default="./test_locomo")  # 1. Memory generation directory
    parser.add_argument('--response_output_dir',type=str, default="./responses_locomo") # 2. Results output
    parser.add_argument('--use_all_memory_cache',type=bool, default=False)     # 1.False(start generate mem) 2. True (start retireval)
    parser.add_argument('--memory_cache_path',type=str, default="./test_locomo")  
    parser.add_argument('--message_understanding_cache',type=bool, default=False) # This is to save money and keep efficiency
    parser.add_argument('--message_understanding_cache_path',type=str, default="./memory_cache")
    parser.add_argument('--number_of_retrieval_pieces',type=int, default=10)
    parser.add_argument('--drop_threshold',type=float, default=0.1)
    cmd_args = parser.parse_args()
    tasks = [run_one(idx=p_id, args = args, cmd_args=cmd_args, client=client) for p_id in range(10)]

    import shutil
    dir_path = cmd_args.output_dir


    try:
        shutil.rmtree(cmd_args.response_output_dir)
    except:
        print("No target output folder.")
    os.mkdir(cmd_args.response_output_dir) 
    
    results = await tqdm_asyncio.gather(*tasks, total=len(tasks))

if __name__ == "__main__":

    asyncio.run(main())  