from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
# Load model and tokenizer
model_id = 'TEN-framework/TEN_Turn_Detection'
model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True, torch_dtype=torch.bfloat16)
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

# Move model to GPU
model = model.cuda()
model.eval()

# Function for inference
def analyze_text(text, system_prompt=""):
    inf_messages = [{"role":"system", "content":system_prompt}] + [{"role":"user", "content":text}]
    input_ids = tokenizer.apply_chat_template(
        inf_messages, 
        add_generation_prompt=True, 
        return_tensors="pt"
    ).cuda()
    
    with torch.no_grad():
        outputs = model.generate(
            input_ids, 
            max_new_tokens=1, 
            do_sample=True, 
            top_p=0.1, 
            temperature=0.1, 
            pad_token_id=tokenizer.eos_token_id
        )
        
    response = outputs[0][input_ids.shape[-1]:]
    return tokenizer.decode(response, skip_special_tokens=True)

if __name__=="__main__":
    # Example usage
    text = "Hello I have a question about"
    result = analyze_text(text)
    print(f"Input: '{text}'")
    print(f"Turn Detection Result: '{result}'")

