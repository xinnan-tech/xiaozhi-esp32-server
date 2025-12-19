from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os


def get_device():
    """Auto-detect the best available device: CUDA > MPS > CPU"""
    if torch.cuda.is_available():
        os.environ["CUDA_VISIBLE_DEVICES"] = "0"
        return torch.device("cuda")
    elif torch.backends.mps.is_available():
        return torch.device("mps")
    else:
        return torch.device("cpu")


def get_dtype(device):
    """Get appropriate dtype for the device"""
    if device.type == "cuda":
        return torch.bfloat16
    elif device.type == "mps":
        return torch.float16  # MPS works better with float16
    else:
        return torch.float32  # CPU needs float32 for bfloat16 models


# Auto-detect device
DEVICE = get_device()
DTYPE = get_dtype(DEVICE)
print(f"Using device: {DEVICE}, dtype: {DTYPE}")

# Load model and tokenizer
model_id = 'TEN-framework/TEN_Turn_Detection'
model = AutoModelForCausalLM.from_pretrained(
    model_id, 
    trust_remote_code=True, 
    torch_dtype=DTYPE
)
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

# Move model to device
model = model.to(DEVICE)
model.eval()


def analyze_text(text, system_prompt=""):
    """Function for inference"""
    inf_messages = [{"role": "system", "content": system_prompt}] + [{"role": "user", "content": text}]
    input_ids = tokenizer.apply_chat_template(
        inf_messages, 
        add_generation_prompt=True, 
        return_tensors="pt"
    ).to(DEVICE)
    
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

