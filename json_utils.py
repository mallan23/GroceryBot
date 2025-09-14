import json5
import re

def clean_json(json_str: str) -> str:
    # Remove comments (// or #)
    json_str = re.sub(r'//.*|#.*', '', json_str)
    # Replace single quotes with double quotes
    json_str = re.sub(r"'", r'"', json_str)
    # Remove trailing commas
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    # Convert fractions like 1/4 to 0.25 does this by finding patterns of digits/digits and replacing with float division
    json_str = re.sub(r'(\d+)\s*/\s*(\d+)', lambda m: str(float(m.group(1))/float(m.group(2))), json_str)
    return json_str

def extract_json_blocks(text: str) -> list[str]:
    """
    scans a string and extracts all balanced JSON objects (text blocks in matching {})
    Scans character-by-character so it won't break on nested braces inside strings.
    """
    blocks = [] #collected JSON blocks
    stack = [] #stack to track opening braces
    start = None #start index of current JSON block
    in_string = False #are we inside a string?
    escape = False #was the last char a backslash?

    for i, char in enumerate(text):
        # toggles in_string state on unescaped quotes
        if char == '"' and not escape:
            in_string = not in_string
        elif char == "\\" and not escape:
            escape = True
            continue
        escape = False

        #when not in a string, track braces by pushong onto stack, then pop once a closing brace is found
        if not in_string:
            if char == "{":
                if not stack:
                    start = i
                stack.append(char)
            elif char == "}" and stack:
                stack.pop()
                if not stack and start is not None:
                    blocks.append(text[start:i+1])
                    start = None
    return blocks

def score_and_parse_mealplan(json_str: str) -> tuple[int, dict]:
    """
    Hueristically evaluate whether a json block is a complete meal plan, first my cleaning then loading
    higher score = more likely to be a full weekly meal plan.
    - +2 for each weekday key
    - +1 for each meal slot (breakfast/lunch/dinner)
    Also checks for "days" wrapper object.
    returns (score, parsed_object) or (0, None) if invalid
    """    
    try:
        cleaned = clean_json(json_str)
        obj = json5.loads(cleaned) # parses JSON into a dict, fails if invalid giving 0 score
    except Exception as e:
        print("\n[JSON Parse Error]")
        print("Error:", e)
        print("Block:\n", json_str[:500])  # Print first 500 chars for context
        return 0, None

    weekdays = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    score = 0
    for day in weekdays:
        if day in obj:
            score += 2
            for meal in ["breakfast","lunch","dinner"]:
                if meal in obj[day]:
                    score += 1
    # Also check for "days" wrapper, meaing if the structure is { "days": { "Monday": {...}, ... } }
    if "days" in obj and isinstance(obj["days"], dict):
        for day in weekdays:
            if day in obj["days"]:
                score += 2
                for meal in ["breakfast","lunch","dinner"]:
                    if meal in obj["days"][day]:
                        score += 1
    # Wrap in "days" if not present for WeeklyPlan parsing to work 
    if "days" not in obj:
        obj = {"days": obj}
    
    return score, obj

def extract_best_mealplan(text: str) -> dict:
    """
    Extracts all JSON blocks, scores them, and returns the best one.
    Raises ValueError if no valid JSON found.
    Also prints the score for each block.
    """
    print("Extracting best mealplan from text")
    blocks = extract_json_blocks(text)
    if not blocks:
        raise ValueError("No JSON blocks found in text")

    best_score = -1
    best_obj = None
    for block in blocks:
        score, obj = score_and_parse_mealplan(block)
        print(f"Block Score = {score}, Best Score = {best_score}")
        if score > best_score:
            best_score = score
            best_obj = obj

    if best_score <= 0 or best_obj is None:
        raise ValueError("No valid meal plan JSON found")

    return best_obj        
'''    
    scores = []
    for i, block in enumerate(blocks):
        score = score_mealplan(block)
        print(f"Block {i+1}: Score = {score}")
        scores.append(score)

    best_idx = max(range(len(blocks)), key=lambda i: scores[i], default=None)
    if best_idx is None or scores[best_idx] == 0:
        raise ValueError("No valid meal plan JSON found")

    return blocks[best_idx]
'''
'''
def extract_best_mealplan(text: str) -> str:
    """
    Extracts all JSON blocks, scores them, and returns the best one.
    Raises ValueError if no valid JSON found.
    """
    print("Extracting best mealplan from text")
    blocks = extract_json_blocks(text)
    if not blocks:
        raise ValueError("No JSON blocks found in text")

    best = max(blocks, key=score_mealplan, default=None)
    if not best or score_mealplan(best) == 0:
        raise ValueError("No valid meal plan JSON found")

    return best
'''

'''
def score_mealplan(json_str: str) -> int:
    """
    Hueristically evaluate whether a json block is a complete meal plan
    higher score = more likely to be a full weekly meal plan.
    - +2 for each weekday key
    - +1 for each meal slot (breakfast/lunch/dinner)
    """
    try:
        obj = json.loads(json_str) # parses JSON into a dict, fails if invalid giving 0 score
    except Exception:
        return 0

    #for each found weekday, add 2 points, and 1 point for each meal slot
    #expects the object to be a dict with keys for each day of the week and day caontian another dict with meal keys
    weekdays = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    score = 0
    for day in weekdays:
        if day in obj:
            score += 2
            for meal in ["breakfast","lunch","dinner"]:
                if meal in obj[day]:
                    score += 1
    return score
'''