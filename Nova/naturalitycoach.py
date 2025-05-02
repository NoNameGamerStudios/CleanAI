import torch
import torch.nn as nn
import torch.nn.functional as F
import os
import pandas as pd
import json
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class NaturalCoach(nn.Module):
    
    data_path = "coachtrain/sentresponses.json"
    
    def __init__(self, input_size, hidden_size=64):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        return self.fc2(x)
    
    def importdata(self, data_path):
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Dataset not found at {data_path}")
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.data = pd.DataFrame(data)
        

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

def process_nova_response(nova_response):
    if not isinstance(nova_response, str):
        print("Invalid response type. Expected a string.")
        return None
    if not nova_response.strip():
        print("Empty response received.")
        return None
    try:
        
        print(f"Nova's Response: {nova_response}")
        score = natural_score(nova_response)
        print(f"Naturality Score: {score}")
        return score
    except Exception as e:
        print(f"Error processing Nova's response: {e}")
        return None
    
def log_scoring(score):
    log_dir = "Nova/coach_train/natural_feedback"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, "natural_score_log.txt")
    with open(log_file, 'a') as f:
        f.write(f"Score: {score}\n")

#final logging loop
if __name__ == "__main__":
    coach = NaturalCoach(input_size=10)
    coach.importdata("Nova/coach_train/sentresponses.json")
    while True:
        if 'response' in coach.data.columns:
            coach.data['naturality_score'] = coach.data['response'].apply(natural_score)
            for idx, row in coach.data.iterrows():
                print(f"Response: {row['response']}\nNaturality Score: {row['naturality_score']}\n")
        else:
            print("No 'response' column found in sentresponses.json.")
        time.sleep(0.1)  # Wait 5 seconds before checking again
        # Optionally, reload the data to catch new responses:
        coach.importdata("Nova/coach_train/sentresponses.json")


    

