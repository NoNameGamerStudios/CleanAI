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
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, "..", "datasets", "natural_real", "NATURALdata.txt")
    if not os.path.exists(data_path):
        f
    df = pd.read_csv(data_path)
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

