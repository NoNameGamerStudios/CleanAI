import torch
import torch.nn as nn
import torch.nn.functional as F
import os
import pandas as pd

class CoachNet(nn.Module):
    def __init__(self, input_size, hidden_size=64):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, 1)  # Output: score

    def forward(self, x):
        x = F.relu(self.fc1(x))
        return self.fc2(x)

# Example: Feature extraction (very basic, you can expand)
def extract_features(text):
    features = [
        text.count("help"),
        text.count("feel"),
        text.count("why"),
        text.count("?"),
        text.count("!"),
        len(text),
    ]
    return torch.tensor(features, dtype=torch.float32)

# Load or initialize the coach model
coach_model = CoachNet(input_size=6)
try:
    coach_model.load_state_dict(torch.load("coach_model.pt"))
    coach_model.eval()
except Exception:
    pass  # Not trained yet

def score_options(context, options):
    # Dummy logic: score by length for demo, replace with your model
    scores = [len(opt) for opt in options]
    best_idx = int(torch.argmax(torch.tensor(scores)))
    return options[best_idx], scores

def suggest_reasoning(context, options):
    """Suggest a reasoning step based on context and options."""
    # Example: If the context is negative, suggest empathy
    if any(word in context.lower() for word in ["sad", "angry", "upset", "bad"]):
        return "Try to show empathy or offer support."
    # If the context is a question, suggest curiosity
    if "?" in context:
        return "Respond with curiosity or ask a follow-up question."
    # Otherwise, suggest being helpful
    return "Offer helpful information or ask for more details."

def load_coach_dataset():
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, "..", "datasets", "reason", "reasoning_data.txt")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}")
    df = pd.read_csv(data_path)
    return df