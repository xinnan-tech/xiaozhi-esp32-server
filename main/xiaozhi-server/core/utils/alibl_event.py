def extract_sentence_start_text(data):
    output = data.get("payload", {}).get("output", {})
    if output.get("type") != "sentence-begin":
        return None
    text = output.get("original_text")
    return text if isinstance(text, str) and text.strip() else None
