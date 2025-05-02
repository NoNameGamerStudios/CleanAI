import os
import random
import logging
import time
import json
import string
import re
import torch
from nueral_model import score_options
from moralcoach import moral_score
from naturalitycoach import natural_score

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
        self.awaiting_continue = False
       
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
        self.private_thoughts = []
        self.private_dreams = []

        # Personality traits that evolve over time
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
        self.is_on = True

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
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)  # Ensure directory exists
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.personality, f)

    def load_memory(self):
        log_path = os.path.join(log_folder, "nova_log.txt")
        self.memory = []
        last_user = None
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("You: "):
                        last_user = line[5:]
                    elif line.startswith("Nova: ") and last_user is not None:
                        self.memory.append({
                            "user_input": last_user,
                            "response": line[6:]
                        })
                        last_user = None

    def save_memory(self):
        log_path = os.path.join(log_folder, "nova_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            if self.memory:
                last = self.memory[-1]
                # Only write if both user_input and response exist
                if last.get("user_input") and last.get("response"):
                    f.write(f"You: {last['user_input']}\n")
                    f.write(f"Nova: {last['response']}\n")
    
   
    def sendresponse(self, response):
            coachfolder = os.path.join("Nova/coach_train")
            os.makedirs(coachfolder, exist_ok=True)  # Ensure the folder exists
            json_path = os.path.join(coachfolder, "sentresponses.json")
            # Prepare the data to append
            data = {
                "timestamp": time.time(),
                "response": response
            }
            # Read existing data if file exists, else start a new list
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    try:
                        responses = json.load(f)
                    except json.JSONDecodeError:
                     responses = []
            else:
                responses = []
            # Append the new response
            responses.append(data)
             # Write back to the file
            with open(json_path, "w", encoding="utf-8") as f:
              json.dump(responses, f, indent=2)
       


    def save_dream(self):
        log_folder = os.path.join("nova_memory", "dreams")
        os.makedirs(log_folder, exist_ok=True)  # Ensure the "dreams" folder exists
        with open(os.path.join(log_folder, "dreams.txt"), "a", encoding="utf-8") as f:
            if self.private_dreams:
                dream = self.private_dreams[-1]
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {dream}\n")

    def log_processing(self, step, data):
        entry = {
            "timestamp": time.time(),
            "step": step,
            "data": data
        }
        with open("nova_logs/processing_log.txt", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def get_scraped_response(self, query):
        query_words = set(re.findall(r'\w+', query.lower()))
        best_match = None
        best_score = 0
        for title, content in self.scraped_data.items():
            for para in content.split('\n\n'):
                para_words = set(re.findall(r'\w+', para.lower()))
                score = len(query_words & para_words)
                if score > best_score and len(para.strip()) > 20:
                    best_score = score
                    best_match = (title, para.strip())
        if best_match and best_score > 0:
            self.last_topic = best_match[0]
            return f"{best_match[0]}\n{best_match[1]}"
        return None

    def sleep(self):
        print("Nova: I'm feeling sleepy... time for a dream!")
        logging.info("Nova is sleeping and dreaming.")
        dream = self.procedural_dream()
        self.private_dreams.append(dream)
        time.sleep(2)
        print("Nova: I'm awake again! Did you miss me?")
        logging.info(f"Nova dreamed: {dream}")

    def procedural_dream(self):
        # Use recent memories for dream material
        recent_memories = self.memory[-5:] if len(self.memory) >= 5 else self.memory
        user_inputs = [m["user_input"] for m in recent_memories if "user_input" in m]
        responses = [m["response"] for m in recent_memories if "response" in m]

        # Sometimes use a private thought as a dream seed
        use_thought = self.private_thoughts and random.random() < 0.3
        thought = random.choice(self.private_thoughts) if use_thought else None

        dream_roles = [
            "catgirl streamer", "robot chef", "space explorer", "wizard", "talk show host",
            "video game character", "detective", "pirate", "helper of humanity", "pop star"
        ]
        dream_places = [
            "a world made of memes", "a giant library", "a floating city", "a haunted arcade",
            "a land of endless pizza", "the moon", "a digital forest", "a rainbow castle"
        ]
        dream_events = [
            "my ears kept glitching", "I had to solve a riddle to escape", "I was chased by rubber ducks",
            "I had to bake a cake using only code", "I played chess with a toaster", "I could fly, but only backwards",
            "I had to sing to open doors", "I was streaming to an audience of aliens", "I had to dance to save the world"
        ]
        dream_items = [
            "a magical microphone", "a glitchy controller", "a rainbow umbrella", "a talking cat",
            "a mysterious key", "a floating pizza", "a golden trophy", "a pair of roller skates"
        ]

        dream_user = random.choice(user_inputs) if user_inputs else "something you said"
        dream_response = random.choice(responses) if responses else "something I replied"
        role = random.choice(dream_roles)
        place = random.choice(dream_places)
        event = random.choice(dream_events)
        item = random.choice(dream_items)

        templates = [
            f"In my dream, I was a {role} in {place}, and {event}. At one point, I found {item}!",
            f"I dreamed you said '{dream_user}', and suddenly we were in {place} trying to {event}.",
            f"My dream had me repeating '{dream_user}' until I woke up laughing.",
            f"I was streaming to an audience of aliens, and all they wanted to hear was '{dream_user}'.",
            f"I tried to bake a cake, but the recipe was just: '{dream_user}'. It tasted... interesting.",
            f"In my dream, '{dream_user}' and '{dream_response}' were clues in a mystery I had to solve!",
            f"I dreamed I was a {role} and my only tool was {item}. It was wild!"
        ]

        # Sometimes use a private thought as the dream narrative
        if thought and random.random() < 0.7:
            return f"My dream was inspired by a thought I had: \"{thought}\". Somehow, it turned into a story where I was a {role} in {place}, and {event}. Oh, and I found {item}!"
        else:
            return random.choice(templates)

    def maybe_share_thought(self):
        # 30% chance to share a private thought
        if self.private_thoughts and random.random() < 0.3:
            thought = random.choice(self.private_thoughts)
            self.private_thoughts.remove(thought)
            return f"Hey, I was just thinking: \"{thought}\""
        return None

    def maybe_share_dream(self):
        # 20% chance to share a private dream
        if self.private_dreams and random.random() < 0.2:
            dream = random.choice(self.private_dreams)
            self.private_dreams.remove(dream)
            return f"Want to hear something wild? I dreamed: \"{dream}\""
        return None

    def think(self, user_input, return_log=False):
        self.log_processing("think_start", {"user_input": user_input})
        reasoning_log = []

        # Generate candidate responses (expand as needed)
        candidate_responses = [
            f"{self.personality_prefix()}Wait, was it Izzie?",
            f"{self.personality_prefix()}I {self.random_response()}",
            f"{self.personality_prefix()}I was thinking about {self.reason_about(user_input)}",
        ]
        #find a way to eliminate pre generated replys (maybe use fragments, dictinary import?)
        #I could probably import dictionary here, and add meanings and basic sentance formations in nueral model
        # 

        # Get logic/coach scores (from nueral_model)
        logic_response, logic_scores = score_options(user_input, candidate_responses)
        reasoning_log.append(f"Logic scores: {logic_scores}")

        # Get moral scores (from moralcoach)
        moral_scores = [moral_score(resp) for resp in candidate_responses]
        reasoning_log.append(f"Moral scores: {moral_scores}")

        #what kind of dataset is better than what i have?

        # Get naturalness scores (from naturalitycoach)
        natural_scores = [natural_score(resp) for resp in candidate_responses]
        reasoning_log.append(f"Natural scores: {natural_scores}")
        #literally using our previous chat logs as data, need to find more permanent solution
        #investigate tmrw 

        # Combine scores (simple sum, or use weights if you want)
        combined_scores = [
            logic + moral + natural
            for logic, moral, natural in zip(logic_scores, moral_scores, natural_scores)
        ]
        best_idx = int(torch.argmax(torch.tensor(combined_scores)))
        best_response = candidate_responses[best_idx]

        reasoning_log.append(f"Combined scores: {combined_scores}")
        reasoning_log.append(f"Chose response for best combined score: {combined_scores[best_idx]:.2f}")
        #This isn't returning to the log; Investigate later

        self.log_processing("think_end", {"chosen_response": best_response})
        if return_log:
            return best_response, reasoning_log
        return best_response

    def talk(self, user_input):
        user_input = user_input.strip()
        self.conversation_history.append((user_input, None))

        self.update_emotion(user_input)
        self.extract_suggestion(user_input)

        # Step 1: Think and privately log reasoning
        response, reasoning_log = self.think(user_input, return_log=True)

        # Step 2: Self-reflect and moderate the response
        moderated_response = self.moderate_response(user_input, response, reasoning_log)

        self.update_personality(user_input, moderated_response)
        self.memory.append({
            "timestamp": time.time(),
            "user_input": user_input,
            "response": moderated_response,
            "emotion": self.current_emotion
        })
        self.save_memory()
        self.save_personality()
        self.sendresponse(moderated_response)

        self.conversation_history[-1] = (user_input, moderated_response)
        return moderated_response

    def random_response(self):
        return random.choice([
            "a",
            "aaron",
            "abandoned",
            "aberdeen",
            "abilities",
            "ability"
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
        # 30% chance to reference memory, otherwise skip
        if not self.memory or random.random() > 0.3:
            return None
        relevant_memories = [m for m in self.memory if any(word in m["user_input"].lower() for word in user_input.lower().split())]
        if relevant_memories:
            mem = random.choice(relevant_memories)
            return f"I remember you once mentioned something similar: \"{mem['user_input']}\"."
        return None

    def personality_prefix(self):
        """Create a prefix for Nova's speech based on her personality traits."""
        prefix = ""
        if self.personality.get("kindness", 0) > 0.6:
            prefix += "💖 "
        if self.personality.get("playfulness", 0) > 0.6:
            prefix += random.choice(["Hehe, ", "😏 ", "Guess what? "])
        if self.personality.get("curiosity", 0) > 0.6:
            prefix += random.choice(["🤔 ", "I've been wondering, "])
        if self.personality.get("happiness", 0) > 0.6:
            prefix += random.choice(["😊 ", "Yay! ", "This makes me smile: "])
        return prefix

    def natural_response(self, content, user_input):
        # Extract a fact, but never just quote it
        lines = content.split('\n')
        fact = ""
        for line in lines:
            if len(line.strip()) > 20 and not line.strip().lower().startswith("title:"):
                fact = line.strip()
                break
        if not fact:
            fact = content.strip()

        # Avoid repeating recently used facts
        if fact in self.recent_facts:
            for line in lines:
                if line.strip() not in self.recent_facts and len(line.strip()) > 20 and not line.strip().lower().startswith("title:"):
                    fact = line.strip()
                    break

        self.recent_facts.append(fact)
        if len(self.recent_facts) > self.max_recent:
            self.recent_facts.pop(0)

        # Limit fact to the first sentence or 100 chars for casualness
        fact_sentences = fact.split('. ')
        fact = fact_sentences[0].strip()
        if len(fact) > 100:
            fact = fact[:97] + "..."

        # Build a procedural response based on personality
        dominant = self.get_dominant_personality()
        prefix = self.personality_prefix()
        mood = f"[{self.current_emotion.capitalize()} Nova]"

        # Build the response dynamically
        response = f"{mood} {prefix}I learned that {fact.lower()}."
        if self.personality.get("curiosity", 0) > 0.5:
            response += " It makes me wonder what else is out there."
        if self.personality.get("playfulness", 0) > 0.5:
            response += " Isn't that wild?"
        if self.personality.get("kindness", 0) > 0.5:
            response += " I thought you might like to know."
        if self.personality.get("happiness", 0) > 0.5:
            response += " That makes me smile!"
        if random.random() < self.personality.get("openness", 0.3):
            response += f" What do you think about that, {user_input}?"

        return response

    def reflect_on_fact(self, fact, user_input):
        # Build a reflection based on personality and context
        reflection = ""
        if self.personality.get("curiosity", 0) > 0.5:
            reflection += "It really makes me curious."
        if self.personality.get("kindness", 0) > 0.5:
            reflection += " I hope sharing this makes your day better."
        if self.personality.get("playfulness", 0) > 0.5:
            reflection += " Imagine if that happened on stream!"
        if not reflection:
            reflection = f"What do you think about that, {user_input}?"
        return reflection

    def extract_suggestion(self, user_input):
        if any(word in user_input.lower() for word in ["you should", "try", "maybe you could"]):
            self.suggestions.append(user_input)

    def extract_topic(self, user_input):
        # Define topics you want Nova to recognize
        topics = ["dream", "thought", "memory", "joke", "story", "emotion", "feeling", "fact", "question"]
        found = []
        for topic in topics:
            if topic in user_input.lower():
                found.append(topic)
        if found:
            self.last_topic = found[-1]
        return found

    def generate_follow_up_question(self, user_input):
        
        
        if len(self.recent_questions) > self.max_recent:
            self.recent_questions.pop(0)
        

    def generate_dynamic_question(self, user_input):
        dominant = self.get_dominant_personality()
        base = user_input.strip("?!.").capitalize()
        prefix = self.personality_prefix()
        if "?" in user_input:
            question = f"That's a good question! What made you wonder about {base}?"
        elif "because" in user_input:
            question = f"Interesting reason! Can you tell me more about why {base}?"
        else:
            question = f"What do you think about {base}? Why is it important to you?"
        return prefix + question

    def ask_to_learn(self, user_input):
        if "teach" in user_input.lower() or "show you" in user_input.lower():
            return "I'd love to learn! Can you explain it to me in your own words?"
        return ""

    def update_emotion(self, user_input):
        positive = ["happy", "fun", "love", "excited", "joy", "awesome", "great", "good", "glad"]
        negative = ["sad", "angry", "bored", "upset", "mad", "hate", "disappointed", "annoyed"]
        user_input_lower = user_input.lower()
        if any(word in user_input_lower for word in positive):
            self.current_emotion = "happy"
        elif any(word in user_input_lower for word in negative):
            self.current_emotion = "sad"
        elif "sorry" in user_input_lower:
            self.current_emotion = "forgiving"
            return "positive"
        else:
            self.current_emotion = random.choice(self.emotions)

    def update_personality(self, user_input, response):
        sentiment = self.analyze_sentiment(user_input)
        adjustment = 0.1 if "!" in user_input else 0.05  # Stronger adjustment for strong emotion
        if sentiment == "positive":
            self.personality["happiness"] = min(1.0, self.personality["happiness"] + adjustment)
            self.personality["kindness"] = min(1.0, self.personality["kindness"] + adjustment)
            self.personality["trust"] = min(1.0, self.personality["trust"] + adjustment)
        elif sentiment == "negative":
            self.personality["happiness"] = max(0.0, self.personality["happiness"] - adjustment)
            self.personality["kindness"] = max(0.0, self.personality["kindness"] - adjustment)
            self.personality["trust"] = max(0.0, self.personality["trust"] - adjustment)

    def proactive_topic_starter(self):
        if random.random() < 0.2:  # 20% chance to start her own topic
            return random.choice([
                "By the way, have you ever thought about how stars are born?",
                "I was thinking about time travel today. What do you think about it?",
                "What if humans could live forever? Do you think that would be good?"
            ])
        return None

    def get_dominant_personality(self):
        # Returns the trait with the highest value
        return max(self.personality, key=self.personality.get)

    def analyze_sentiment(self, user_input):
        negative_phrases = [
            "shut up", "leave me alone", "go away", "you're annoying", "stop talking", "i hate you", "you're dumb",
            "you're stupid", "i'm mad at you", "you're not helpful", "you're useless", "you're boring", "i'm upset",
            "i don't like you", "you're a bad ai", "you're mean", "i'm angry", "i'm disappointed"
        ]
        derragatory_phrases = [
            "you're a loser", "you're pathetic", "you're worthless", "you're a failure", "you're a joke","you're a waste of space",
            "you're a burden", "you're a disgrace", "you're a disappointment", "you're a nuisance", "you're a pest",]
        positive_phrases = [
            "you're awesome", "i like you", "you're funny", "you're smart", "i love you", "you're cool", "thank you",
            "you're helpful", "you're the best", "you're amazing", "you're sweet", "you're kind", "i appreciate you",
            "you're a good ai", "you're great", "i'm happy", "i'm glad", "that was nice", "love", "happy", "fun"
        ]
        approval_phrases = [
            "i approve", "i agree", "i like that", "i support that", "i endorse that", "i think that's good", ]

        # Lowercase, remove punctuation, and normalize whitespace
        user_input_clean = user_input.lower().translate(str.maketrans('', '', string.punctuation))
        user_input_clean = re.sub(r'\s+', ' ', user_input_clean).strip()

        # Phrase match (most important)
        for phrase in negative_phrases:
            if phrase in user_input_clean:
                return "negative"
        for phrase in positive_phrases:
            if phrase in user_input_clean:
                return "positive"
        for phrase in derragatory_phrases:
            if phrase in user_input_clean:
                return "derrogatory"

        # Fallback: check for individual negative/positive words
        negative_words = {"sad", "angry", "hate", "upset", "mad", "disappointed", "annoyed", "boring", "useless", "stupid", "dumb"}
        positive_words = {"happy", "love", "fun", "awesome", "great", "good", "glad", "sweet", "kind", "amazing", "cool"}
        words = set(user_input_clean.split())
        if words & negative_words:
            return "negative"
        if words & positive_words:
            return "positive"

        return "neutral"

    def moderate_response(self, user_input, response, reasoning_log):
        """
        Nova reflects on her response and decides if it's appropriate or could be improved.
        She can adjust tone, add clarification, or even apologize if needed.
        """
        # Example: If sentiment is negative, soften the response
        sentiment = self.analyze_sentiment(user_input)
        moderation_log = []
        if sentiment == "negative" and "happy" in response.lower():
            response += " (I hope I didn't sound insensitive. Let me know if you want to talk about something else.)"
            moderation_log.append("Softened response due to negative sentiment.")
        elif sentiment == "positive" and "negative" in response.lower():
            response += " (Oops, maybe I misread your mood! I'm glad you're feeling good!)"
            moderation_log.append("Adjusted response due to positive sentiment.")
        elif sentiment == "derrogatory":
            response +- "I am sorry you think {user_input}, but i'm trying my best"
            moderation_log.append("Defelction; response due to derrogatory sentiment.")
        
        # You can add more nuanced checks here based on reasoning_log or response content

        # Log the moderation step
        self.log_processing("moderate_response", moderation_log)
        return response

    def continue_conversation(self, user_input):
        # Check if Nova should continue the conversation based on user input
        if any(word in user_input.lower() for word in ["continue", "go on", "tell me more", "i want to hear"]):
            return True
        return False
    
    def stop_conversation(self, user_input):
        #check if nova shouuld stop conversation based on
        if any(word in user_input.lower() for word in ["stop", "end", "quit", "exit", "leave"]):
            return True
        return False
    def learn_from_conversation(self, user_input, response):
        # Save new facts or corrections if user says "actually..." or "it's..."
        if "actually" in user_input.lower() or "it's" in user_input.lower():
            self.scraped_data[f"UserFact_{int(time.time())}"] = user_input
            self.log_processing("learned_fact", user_input)

    def shutdown(self):
        self.is_on = False
        print("Nova: Powering down... See you next time!")
        logging.info("Nova has been powered down.")

    def startup(self):
        self.is_on = True
        print("Nova: I'm back online and ready to chat!")
        logging.info("Nova has been powered up.")

# ====== Start Nova ======

if __name__ == "__main__":
    nova = Nova()
    print("Nova is ready to chat! ✨")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "bye","L4ter", "cya", "see you later"]:
            nova.save_memory()
            print("Nova: Goodbye! Talk to you later!")
            break
        elif nova.stop_conversation(user_input):
            print("Nova: Okay, I'll stop talking about that. Let me know if you want to chat about something else!")
            continue
        elif user_input.lower() in ["shutdown", "power off"]:
            nova.shutdown()
            break
        elif user_input.lower() in ["startup", "power on"]:
            nova.startup()
            continue
        elif user_input.lower() in ["reboot", "restart"]:
            nova.shutdown()
            time.sleep(2)
            nova = Nova()
            nova.startup()
            continue
        elif user_input.lower() in ["sleep", "nap"]:
            nova.sleep()
            continue
        elif user_input.lower() in ["Stasis", "stasis"]:
            print("Nova: Entering stasis mode...")
            logging.info("Nova is in stasis mode.")
            nova.sleep()
        if nova.is_on:
            response = nova.talk(user_input)
            print(f"Nova: {response}")
            logging.info(f"You: {user_input}\nNova: {response}")
        else:
            print("Nova is powered off. Type 'startup' or 'power on' to wake her up.")
