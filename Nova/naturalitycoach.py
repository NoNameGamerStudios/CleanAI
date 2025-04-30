import torch
import torch.nn as nn
import torch.nn.functional as F
import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class NaturalCoach(nn.Module):
    def __init__(self, input_size, hidden_size=64):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        return self.fc2(x)

def load_coach_dataset():
    import re
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, "datasets", "natural_real", "NATURALdata.txt")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}")

    lines = []
    usernames = []
    current_user = None

    with open(data_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Detect username lines (e.g., "KingKarma, Yesterday 7:22 PM")
            if line and "," in line and not any(x in line for x in ["AM", "PM", "min", "Now", "Edited"]) and not line.startswith("//"):
                # Extract username before the first comma
                current_user = line.split(",")[0].strip()
                continue
            # If it's a message line and we have a user, keep it
            if line and current_user:
                usernames.append(current_user)
                lines.append(line)

    import pandas as pd
    df = pd.DataFrame({"user": usernames, "text": lines})
    return df

# Load dataset and fit TF-IDF vectorizer once
df = load_coach_dataset()
real_responses = df['text'].astype(str).tolist()
vectorizer = TfidfVectorizer().fit(real_responses)

def natural_score(candidate):
    # Compute similarity to real responses
    candidate_vec = vectorizer.transform([candidate])
    real_vecs = vectorizer.transform(real_responses)
    similarities = cosine_similarity(candidate_vec, real_vecs)
    # Score is the max similarity to any real response (higher = more natural)
    return float(similarities.max())

