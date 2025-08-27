# uses a pre-trained language model to generate a weekly meal plan in JSON based on dietary tags


#import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from models import WeeklyPlan
from agent import Agent
from json_utils import extract_best_mealplan
#import re


class LLMMealPlanAgent(Agent):
    #iniitalizes the agent by loading a tokenizer and model from HuggingFace
    def __init__(self, model_name: str, device: str = "cpu"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, 
            device_map="auto", 
            trust_remote_code=True,
            quantization_config=BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype="float16",
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True
            )
        )
        self.device = device

    #retreives dietary tags from context, generates a prompt, and uses the model to generate a weekly meal plan
    def run(self, context):
        dietary = context.get("dietary_tags", "")
        #creats detailed prompt, ensures it matches the WeeklyPlan schema
        prompt = f"""
        [INST]
        Generate a 7-day meal plan in JSON.
        - Keys: "Monday"…"Sunday"
        - Each day has "breakfast", "lunch", "dinner"
        - Each meal: {{"name": "string", "ingredients": [{{"name": "string", "quantity": number, "unit": "string"}}]}}
        Dietary tags: {dietary}
        STRICT RULES:
        - Output ONLY valid JSON
        - Double quotes for all strings
        - No explanations, no extra text, no markdown, no comments
        [/INST]
        """
        #tokenizes the input prompt
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        # generates output, encrouages to be creative with sampling
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=4096,
            do_sample=True,
            temperature=0.7,
            top_p=0.9
        )
        #output decoded to text
        text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"Generated LLM text: {text} END OF LLM TEXT")
        # Extract the JSON
        try:
            json_str = extract_best_mealplan(text)
            #print the object type for debugging
            print(f"Extracted JSON string type: {type(json_str)}")
            plan = WeeklyPlan.parse_obj({"days": json_str})
        except Exception as e:
            raise RuntimeError(f"Failed to parse LLM output: {e}\n{text}")
        context["weekly_plan"] = plan
        return context