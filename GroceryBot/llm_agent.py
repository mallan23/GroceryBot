# uses a pre-trained language model to generate a weekly meal plan in JSON based on dietary tags


import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from models import WeeklyPlan
from agent import Agent
import re

class LLMMealPlanAgent(Agent):
    #iniitalizes the agent by loading a tokenizer and model from HuggingFace
    def __init__(self, model_name: str, device: str = "cpu"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype=torch.float16 if device!="cpu" else torch.float32
        ).to(device)
        self.device = device

    #retreives dietary tags from context, generates a prompt, and uses the model to generate a weekly meal plan
    def run(self, context):
        dietary = context.get("dietary_tags", "")
        #creats detailed prompt, ensures it matches the WeeklyPlan schema
        prompt = f"""
        Generate a 7-day meal plan in JSON.
        - Keys: "Monday"…"Sunday"
        - Each day has "breakfast", "lunch", "dinner"
        - Each meal: {{"name": string, "ingredients": [{{"name": string, "quantity": number, "unit": string}}]}}
        Dietary tags: {dietary}
        STRICT RULES:
        - Output ONLY valid JSON
        - Double quotes for all strings
        - No explanations, no extra text
        """
        #tokenizes the input prompt
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        # generates output, encrouages to be creative with sampling
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=1024,
            do_sample=True,
            temperature=0.7,
            top_p=0.9
        )
        #output decoded to text
        text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"Generated LLM text: {text} END OF LLM TEXT")
        # Extract the JSON blob
        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise RuntimeError(f"No JSON found in LLM output: {text}")
            json_str = match.group(0)
            # Parse the JSON string into a WeeklyPlan object
            plan = WeeklyPlan.parse_raw(json_str)
        except Exception as e:
            raise RuntimeError(f"Failed to parse LLM output: {e}\n{text}")
        context["weekly_plan"] = plan
        return context