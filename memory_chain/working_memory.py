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
from queue import Queue
import queue

class Working_Memory:

    def __init__(self,working_memory_path ,user_id,model,working_memory_max_size,client,refresh_rate):

        self.file_path = working_memory_path 
        self.user_id = user_id
        self.model = model
        self.working_memory_queue = Queue()
        self.working_memory_max_size = working_memory_max_size
        self.refresh_rate = refresh_rate
        self.client = client
        ensure_directory_exists(self.file_path)

    def add_message_to_working_memory(self,raw_message,message,topics,emotions,reason,index,timestamp,fact,attribute):

        self.working_memory_queue.put({"user_id":self.user_id,"raw_message":raw_message,"message":message,"topics":topics,"emotions":emotions,"reason":reason,"index":index,"timestamp":timestamp,"fact":fact,"attribue":attribute})

        if (self.working_memory_queue.qsize() == self.working_memory_max_size):
            is_full = True    
        else:
            is_full = False

        return is_full, self._save_working_memory()
    
    def pop_oldest_wm(self):

        return self.working_memory_queue.get()

    def pop_oldest_working_memory(self):
        
        popped_items = []

        for _ in range(self.refresh_rate):
            try:
                item = self.working_memory_queue.get_nowait() 
                popped_items.append(item)
            except queue.Empty:
                break  

        return popped_items

    
    def _save_working_memory(self):
        temp_queue = queue.Queue()
        temp_list = []

        while not self.working_memory_queue.empty():
            item = self.working_memory_queue.get()
            temp_list.append(item)
            temp_queue.put(item) 

        while not temp_queue.empty():
            self.working_memory_queue.put(temp_queue.get())

        with open(self.file_path, 'w') as f:
            json.dump(temp_list, f, indent=2, sort_keys=True) 
        
        message_summary_list = [item["message"] for item in temp_list]
        return message_summary_list
    def read_cache(self,file_path):

        print(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            message_understanding_caches = json.load(f)
        for message_understanding in  message_understanding_caches:
             self.working_memory_queue.put(message_understanding)
             
        self._save_working_memory()







        