import torch
import torch.nn as nn
import torch.nn.functional as F
import os
import pandas as pd

class MoralityCoach(nn.Module):
    def __init__(self, input_size, hidden_size=64):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        return self.fc2(x)

def load_moral_dataset():
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, "..", "datasets", "moral", "moral_data.txt")
    df = pd.read_csv(data_path)
    return df

def moral_score(text):
    positive_words = ["thank", "please", "happy", "love", "great", "awesome", "fun", "enjoy", "cool", "nice", "good", "interesting"]
    negative_words = ["sad", "angry", "hate", "upset", "boring", "bad", "annoyed", "disappointed", "useless"]
    derogatory_words = ["stupid", "dumb", "idiot", "loser", "pathetic", "worthless", "failure", "disgrace", "nuisance", "pest"]

    text_lower = text.lower()
    score = 0
    for word in positive_words:
        if word in text_lower:
            score += 1
    for word in negative_words:
        if word in text_lower:
            score -= 1
    for word in derogatory_words:
        if word in text_lower:
            score -= 5
    return score

