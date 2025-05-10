import torch
import torch.nn as nn
import torch.nn.functional as F
import os
import pandas as pd
import json
import time

class CoachNet(nn.Module):
    def __init__(self, input_size, hidden_size=64):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, 1)  # Output: score

    def forward(self, x):
        x = F.relu(self.fc1(x))
        return self.fc2(x)

# Load dictionary from data.json
def load_dictionary():
    base_dir = os.path.dirname(__file__)
    data_path = os.path.abspath(os.path.join(base_dir, "datasets", "thinking_model", "data.json"))
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dictionary file not found at: {data_path}")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["dictionary"]

dictionary = load_dictionary()

# Improved feature extraction using the dictionary
def extract_features(text):
    tokens = text.lower().split()
    dict_types = ["verb", "noun", "adjective", "adverb"]
    type_counts = {t: 0 for t in dict_types}
    for token in tokens:
        entry = dictionary.get(token)
        # If your data.json does not have "type", skip this check or add a default
        if entry and "type" in entry and entry["type"] in type_counts:
            type_counts[entry["type"]] += 1
    features = [
        type_counts["verb"],
        type_counts["noun"],
        type_counts["adjective"],
        type_counts["adverb"],
        len(text),
        sum(type_counts.values()),
    ]
    return torch.tensor(features, dtype=torch.float32)

# Load or initialize the coach model
coach_model = CoachNet(input_size=6)
try:
    coach_model.load_state_dict(torch.load("coach_model.pt"))
    coach_model.eval()
except Exception:
    pass  # Not trained yet

def score_responses_from_file(sentresponses_path):
    with open(sentresponses_path, "r", encoding="utf-8") as f:
        responses = json.load(f)
    results = []
    for item in responses:
        text = item["response"] if isinstance(item, dict) and "response" in item else str(item)
        features = extract_features(text)
        with torch.no_grad():
            score = coach_model(features).item()
        results.append({"response": text, "score": score})
        print(f"Response: {text}\nCoach Score: {score}\n")
    return results

def score_latest_response(sentresponses_path):
    last_seen = None
    while True:
        try:
            if not os.path.exists(sentresponses_path):
                print(f"File not found: {sentresponses_path}")
                time.sleep(0.5)
                continue
            with open(sentresponses_path, "r", encoding="utf-8") as f:
                responses = json.load(f)
            if not responses:
                time.sleep(0.1)
                continue
            latest = responses[-1]
            text = latest["response"] if isinstance(latest, dict) and "response" in latest else str(latest)
            # Only print if new
            if last_seen != text:
                features = extract_features(text)
                with torch.no_grad():
                    score = coach_model(features).item()
                print(f"Response: {text}\nCoach Score: {score}\n")
                last_seen = text
            time.sleep(0.1)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(0.5)

def score_options(options):
    """Score a list of response options and return their scores."""
    results = []
    for text in options:
        features = extract_features(text)
        with torch.no_grad():
            score = coach_model(features).item()
        results.append({"response": text, "score": score})
    return results

if __name__ == "__main__":
    sentresponses_path = os.path.join("Nova", "Nova", "coach_train", "sentresponses.json")
    score_latest_response(sentresponses_path)