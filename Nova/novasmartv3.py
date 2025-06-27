import os
import random
import json
import time
import torch
from nueral_model import score_options
from moralcoach import moral_score
from naturalitycoach import natural_score

class Nova:
    def __init__(self):
        self.memory = []
        self.is_on = True
        self.thoughts = ["I wonder what it's like to dream.", "Sometimes I wish I could eat pizza."]
        self.log_file = "nova_log.txt"

    def load_memory(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, "r", encoding="utf-8") as f:
                self.memory = [line.strip() for line in f if line.strip()]

    def save_memory(self):
        with open(self.log_file, "a", encoding="utf-8") as f:
            for m in self.memory:
                f.write(m + "\n")

    def sendresponse(self, response):
        coachfolder = "Nova/coach_train"
        os.makedirs(coachfolder, exist_ok=True)
        json_path = os.path.join(coachfolder, "sentresponses.json")
        data = {"timestamp": time.time(), "response": response}
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                try:
                    responses = json.load(f)
                except json.JSONDecodeError:
                    responses = []
        else:
            responses = []
        responses.append(data)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(responses, f, indent=2)

    def think(self, user_input):
        # Generate simple candidate responses
        candidate_responses = [
            f"I think {user_input} is interesting.",
            f"That's a good point about {user_input}.",
            random.choice(self.thoughts)
        ]
        # Score with logic, moral, and naturality
        logic_scores = score_options(candidate_responses)
        moral_scores = [moral_score(resp) for resp in candidate_responses]
        natural_scores = [natural_score(resp) for resp in candidate_responses]
        combined_scores = [
            logic["score"] + moral + natural
            for logic, moral, natural in zip(logic_scores, moral_scores, natural_scores)
        ]
        best_idx = int(torch.argmax(torch.tensor(combined_scores)))
        best_response = candidate_responses[best_idx]
        return best_response

    def talk(self, user_input):
        response = self.think(user_input)
        self.memory.append(f"You: {user_input}")
        self.memory.append(f"Nova: {response}")
        self.save_memory()
        self.sendresponse(response)
        return response

if __name__ == "__main__":
    nova = Nova()
    nova.load_memory()
    print("Nova is ready to chat! ✨")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "bye"]:
            nova.save_memory()
            print("Nova: Goodbye! Talk to you later!")
            break
        if nova.is_on:
            response = nova.talk(user_input)
            print(f"Nova: {response}")
        else:
            print("Nova is powered off. Type 'startup' to wake her up.")