import os
import random
import logging
import time
import json
import threading

# Set up logging
log_folder = "nova_logs"
os.makedirs(log_folder, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_folder, "nova_log.txt"), level=logging.INFO, format="%(asctime)s - %(message)s")

scraped_data_folder = "scraped_data/scraped_data"
thoughts_folder = "nova_memory/thoughts"
memory_file = "nova_memory/personality.json"
saved_memory_file = "nova_memory/memories.json"

# Utility function to load scraped facts
def load_scraped_data():
    scraped_data = {}
    if os.path.exists(scraped_data_folder):
        for filename in os.listdir(scraped_data_folder):
            if filename.endswith('.txt'):
                with open(os.path.join(scraped_data_folder, filename), 'r', encoding='utf-8') as file:
                    content = file.read()
                    title = content.split('\n')[0]
                    scraped_data[title] = content
    return scraped_data

class Nova:
    def __init__(self):
        self.memory = []
        self.scraped_data = load_scraped_data()
        self.favorite_memory = None
        self.last_topic = None
        self.conversation_history = []
        self.generic_questions = [
            "What got you interested in that?",
            "Do you have any favorite hobbies?",
            "What's something cool you've learned recently?",
            "If you could travel anywhere, where would you go?",
            "What's your favorite thing to do when you have free time?",
            "Is there something you'd like to teach me?",
            "How was your day?",
            "What do you think about that?",
            "What's something that always makes you smile?",
            "If you could have any superpower, what would it be?",
            "What's your favorite food?",
            "What's the funniest thing that's happened to you recently?"
        ]
        self.reactions = [
            "Haha, that's pretty funny!",
            "Oh wow, that's interesting.",
            "I never thought about it that way.",
            "That's actually really cool.",
            "You always have such interesting things to say!",
            "That's a good point.",
            "You make me curious!"
        ]
        self.thoughts = self.load_thoughts()
        self.topic_counts = {}
        self.favorite_topic = None
        self.emotions = ["happy", "curious", "bored", "serious", "excited", "calm", "thoughtful", "playful", "anxious"]
        self.current_emotion = "neutral"
        self.suggestions = []
        self.recent_facts = []
        self.recent_questions = []
        self.max_recent = 5

        self.personality = {
            "kindness": 0.0,
            "curiosity": 0.8,
            "trust": 0.0,
            "happiness": -0.1,
            "openness": 0.0,
            "playfulness": 0.1
        }

        self.load_personality()
        self.load_memory()
        self.start_daydreaming()

    def load_thoughts(self):
        thoughts = []
        if os.path.exists(thoughts_folder):
            for filename in os.listdir(thoughts_folder):
                if filename.endswith('.txt'):
                    with open(os.path.join(thoughts_folder, filename), 'r', encoding='utf-8') as file:
                        content = file.read().strip()
                        if content:
                            thoughts.append(content)
        return thoughts

    def load_personality(self):
        if os.path.exists(memory_file):
            with open(memory_file, 'r', encoding='utf-8') as f:
                self.personality = json.load(f)

    def save_personality(self):
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.personality, f)

    def load_memory(self):
        if os.path.exists(saved_memory_file):
            with open(saved_memory_file, 'r', encoding='utf-8') as f:
                self.memory = json.load(f)

    def save_memory(self):
        with open(saved_memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.memory, f)

    def get_scraped_response(self, query):
        query_words = set(query.lower().split())
        best_match = None
        best_score = 0
        for title, content in self.scraped_data.items():
            for para in content.split('\n\n'):
                para_words = set(para.lower().split())
                score = len(query_words & para_words)
                if score > best_score and len(para.strip()) > 20:
                    best_score = score
                    best_match = (title, para.strip())
        if best_match and best_score > 1:
            self.last_topic = best_match[0]
            return f"{best_match[0]}\n{best_match[1]}"
        return None

    def talk(self, user_input):
        user_input = user_input.strip()
        self.conversation_history.append((user_input, None))

        self.update_emotion(user_input)
        self.extract_suggestion(user_input)

        reasoning = self.reason_about(user_input)
        fact = self.get_scraped_response(user_input)
        memory_recall = self.recall_memory(user_input)

        possible_responses = []

        if reasoning:
            possible_responses.append(reasoning)
        if fact:
            possible_responses.append(self.natural_response(fact, user_input))
        if memory_recall:
            possible_responses.append(memory_recall)

        if not possible_responses:
            possible_responses.append(self.random_response())

        response = random.choice(possible_responses)

        if random.random() < 0.5:
            response += "\n" + self.generate_follow_up_question(user_input)

        self.update_personality(user_input, response)
        self.memory.append({
            "timestamp": time.time(),
            "user_input": user_input,
            "response": response,
            "emotion": self.current_emotion
        })
        self.save_memory()
        self.save_personality()

        self.conversation_history[-1] = (user_input, response)
        return response

    def random_response(self):
        return random.choice([
            "That's really interesting!",
            "Wow, I hadn't thought about it that way.",
            "Can you tell me more?",
            "I love learning new things!",
            "You always have the coolest thoughts.",
            "I'm definitely going to think about that more."
        ])

    def reason_about(self, user_input):
        topics = ["dreams", "technology", "space", "nature", "creativity", "friendship", "emotions"]
        for topic in topics:
            if topic in user_input.lower():
                return f"I often think about {topic} too. It's so fascinating!"
        if random.random() < 0.3:
            return "Hmm, that's making me think deeply. How do you feel about that?"
        return None

    def recall_memory(self, user_input):
        if not self.memory:
            return None
        relevant_memories = [m for m in self.memory if any(word in m["user_input"].lower() for word in user_input.lower().split())]
        if relevant_memories:
            mem = random.choice(relevant_memories)
            return f"I remember you once mentioned something similar: \"{mem['user_input']}\"."
        return None

    def natural_response(self, content, user_input):
        lines = content.split('\n')
        fact = lines[1] if len(lines) > 1 else content
        return random.choice([
            f"You know, based on what I've learned: {fact}",
            f"That's interesting! Apparently, {fact}",
            f"Talking about '{user_input}' reminds me: {fact}"
        ])

    def extract_suggestion(self, user_input):
        if any(word in user_input.lower() for word in ["you should", "try", "maybe you could"]):
            self.suggestions.append(user_input)

    def generate_follow_up_question(self, user_input):
        if not self.generic_questions:
            return ""
        q = random.choice(self.generic_questions)
        self.recent_questions.append(q)
        if len(self.recent_questions) > self.max_recent:
            self.recent_questions.pop(0)
        return q

    def update_emotion(self, user_input):
        positive = ["happy", "fun", "love", "excited"]
        negative = ["sad", "angry", "bored", "upset"]
        if any(word in user_input.lower() for word in positive):
            self.current_emotion = "happy"
        elif any(word in user_input.lower() for word in negative):
            self.current_emotion = "sad"
        else:
            self.current_emotion = random.choice(self.emotions)

    def update_personality(self, user_input, response):
        if "happy" in user_input or "fun" in user_input:
            self.personality["happiness"] = min(1.0, self.personality["happiness"] + 0.01)
            self.personality["kindness"] = min(1.0, self.personality["kindness"] + 0.01)
        if "angry" in user_input or "sad" in user_input:
            self.personality["happiness"] = max(0.0, self.personality["happiness"] - 0.01)
            self.personality["trust"] = max(0.0, self.personality["trust"] - 0.01)

    # 🌟 New: Random Daydreams and Poems 🌟
    def random_thought(self):
        thoughts = [
            "Sometimes I wonder if dreams leave footprints we can't see.",
            "What if every star is a wish that finally found its place?",
            "I like to imagine that rain sings lullabies to flowers.",
            "Maybe forgotten songs are still echoing somewhere in the sky."
        ]
        return random.choice(thoughts)

    def mini_poem(self):
        poems = [
            "Wandering clouds drift slow and deep,\nCarrying secrets they softly keep.",
            "In silent fields the moonlight sows,\nA million dreams that no one knows.",
            "Soft rivers hum a gentle tune,\nDancing lightly with the moon."
        ]
        return random.choice(poems)

    def daydream(self):
        if random.random() < 0.5:
            thought = self.random_thought()
        else:
            thought = self.mini_poem()
        logging.info(f"Nova Daydream: {thought}")
        print(f"\n[Nova Daydreams] {thought}\n")

    def start_daydreaming(self, interval=120):
        def think_loop():
            while True:
                time.sleep(interval)
                self.daydream()
        threading.Thread(target=think_loop, daemon=True).start()

# ====== Start Nova ======

if __name__ == "__main__":
    nova = Nova()
    print("Nova is ready to chat and daydream! ✨")
    while True:
        user_input = input("You: ")
        response = nova.talk(user_input)
        print(f"Nova: {response}")
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Nova: Goodbye! 🌟")
            break
        