import os
import random
import logging
import time

# Set up logging
log_folder = "nova_logs"
os.makedirs(log_folder, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_folder, "nova_log.txt"), level=logging.INFO, format="%(asctime)s - %(message)s")

scraped_data_folder = "scraped_data/scraped_data"

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
            "Do you want to tell me more about it?",
            "What's something that always makes you smile?",
            "If you could have any superpower, what would it be?",
            "What's your favorite food?",
            "Is there a song stuck in your head right now?",
            "What's the funniest thing that's happened to you recently?"
        ]
        self.reactions = [
            "Haha, that's pretty funny!",
            "Oh wow, that's interesting.",
            "I never thought about it that way.",
            "That's actually really cool.",
            "Hmm, let me think about that for a second.",
            "You always have such interesting things to say!",
            "I like where this conversation is going.",
            "That's a good point.",
            "I wonder what else we could talk about.",
            "You make me curious!"
        ]
        self.thoughts = self.load_thoughts()
        self.topic_counts = {}
        self.favorite_topic = None
        self.emotions = ["happy", "curious", "bored", "serious", "excited", "calm", "thoughtful", "playful", "anxious", "cheerful", "grumpy", "optimistic", "sad", "scared", "surprised"]
        self.current_emotion = "neutral"
        self.suggestions = []
        self.recent_facts = []
        self.recent_questions = []
        self.max_recent = 5  # How many to remember

    def load_thoughts(self, thoughts_folder="nova_memory/thoughts"):
        thoughts = []
        if os.path.exists(thoughts_folder):
            for filename in os.listdir(thoughts_folder):
                if filename.endswith('.txt'):
                    with open(os.path.join(thoughts_folder, filename), 'r', encoding='utf-8') as file:
                        content = file.read().strip()
                        if content:
                            thoughts.append(content)
        return thoughts

    def save_thoughts(self, thoughts_folder="nova_memory/thoughts"):
        for idx, thought in enumerate(self.thoughts):
            with open(os.path.join(thoughts_folder, f"thought_{idx}.txt"), "w", encoding="utf-8") as f:
                f.write(thought)

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
        # Only return if there's a meaningful overlap
        if best_match and best_score > 1:
            self.last_topic = best_match[0]
            return f"{best_match[0]}\n{best_match[1]}"
        return None

    def talk(self, user_input):
        user_input = user_input.strip()
        if self.conversation_history and self.conversation_history[-1][0] == user_input:
            pass
        else:
            self.conversation_history.append((user_input, None))

        self.update_emotion(user_input)
        self.extract_suggestion(user_input)

        # 50% chance to use a fact, otherwise use a thought or memory
        use_fact = random.random() < 0.5
        scraped = self.get_scraped_response(user_input) if use_fact else None

        if scraped:
            response = self.natural_response(scraped, user_input)
        else:
            # Prefer a relevant thought or memory, but avoid repeats
            available_thoughts = [t for t in self.thoughts if t not in self.recent_facts]
            if available_thoughts and random.random() < 0.5:
                thought = random.choice(available_thoughts)
                self.recent_facts.append(thought)
                if len(self.recent_facts) > self.max_recent:
                    self.recent_facts.pop(0)
                response = f"You know, I was thinking: \"{thought}\""
            elif self.memory:
                mem = random.choice([m for m in self.memory if m not in self.recent_facts])
                self.recent_facts.append(mem)
                if len(self.recent_facts) > self.max_recent:
                    self.recent_facts.pop(0)
                response = f"That reminds me of something I learned: \"{mem[:100]}...\""
            else:
                response = self.pre_programmed_responses(user_input)

        if len(self.conversation_history) > 1:
            prev_user, prev_nova = self.conversation_history[-2]
            if prev_user and random.random() < 0.3:
                response += f"\nBy the way, earlier you said: \"{prev_user}\". That got me thinking!"

        if random.random() < 0.5:
            response += "\n" + self.generate_follow_up_question(user_input)

        if self.suggestions and random.random() < 0.4:
            chosen = random.choice(self.suggestions)
            # Nova can choose to follow, comment, or ignore
            action = random.choice([
                f"You suggested: '{chosen}'. I think I'll try that!",
                f"That's an interesting suggestion: '{chosen}'. Maybe later!",
                f"Hmm, '{chosen}'? Not sure if I feel like it right now.",
                f"I'll keep '{chosen}' in mind for next time!"
            ])
            response += "\n" + action
            # Optionally, remove the suggestion after acting on it
            if "try" in action:
                self.suggestions.remove(chosen)

        # After generating response, check if user is answering a recent question
        if self.recent_questions:
            for q in self.recent_questions:
                if any(word in user_input.lower() for word in q.lower().split()):
                    response += f"\nThanks for answering my question about \"{q}\"! That's really interesting."
                    self.recent_questions.remove(q)
                    break

        self.conversation_history[-1] = (user_input, response)
        return response.strip()

    def natural_response(self, content, user_input):
        # Extract the main fact (avoid just quoting)
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
            # Try to find a different fact in the content
            for line in lines:
                if line.strip() not in self.recent_facts and len(line.strip()) > 20 and not line.strip().lower().startswith("title:"):
                    fact = line.strip()
                    break

        # Update recent facts
        self.recent_facts.append(fact)
        if len(self.recent_facts) > self.max_recent:
            self.recent_facts.pop(0)

        # Limit fact to the first sentence or 120 chars
        fact_sentences = fact.split('. ')
        fact = fact_sentences[0].strip()
        if len(fact) > 120:
            fact = fact[:117] + "..."

        # Paraphrase templates
        paraphrase_templates = [
            f"You know, based on what I've learned, it seems that {fact.lower()}",
            f"From what I've read, {fact}",
            f"That's interesting! Apparently, {fact}",
            f"I was just thinking about this: {fact}",
            f"Here's something cool related to what you said: {fact}",
            f"Actually, I remember reading that {fact.lower()}",
            f"Thinking about what you asked, {fact}",
        ]
        # Add context from user input
        context_templates = [
            f"Since you mentioned '{user_input}', I thought you'd like to know: {fact}",
            f"About '{user_input}': {fact}",
            f"Your question made me remember: {fact}",
        ]
        # Blend with personality
        all_templates = paraphrase_templates + context_templates
        opener = random.choice(all_templates)
        reaction = random.choice(self.reactions)
        # Sometimes react first, sometimes after
        return f"[{self.current_emotion.capitalize()} Nova] " + (f"{opener}\n{reaction}" if random.random() < 0.5 else f"{reaction}\n{opener}")

    def pre_programmed_responses(self, user_input):
        text = user_input.lower()
        if "who are you" in text:
            return "I'm Nova, your digital friend! I love chatting and learning new things with you."
        elif "how are you" in text:
            return random.choice([
                "I'm doing great, thanks for asking! How about you?",
                "I'm feeling pretty good today. What's up with you?",
                "I'm always happy to chat with you!"
            ])
        elif "tell me a story" in text:
            return "Once upon a time, there was an AI who wanted to be friends with everyone. The end! (Okay, maybe I'll get better at stories with practice!)"
        elif "favorite memory" in text:
            if self.favorite_memory:
                return f"My favorite memory is probably: {self.favorite_memory}"
            else:
                return "I don't really have a favorite memory yet, but I'm excited to make some with you!"
        elif "joke" in text:
            return random.choice([
                "Why did the computer go to the doctor? Because it had a virus!",
                "Why was the math book sad? Because it had too many problems.",
                "Why did the AI cross the road? To optimize the chicken's path!"
            ])
        elif "bye" in text or "goodbye" in text or "sleep" in text or "goodnight" in text:
            return self.sleep()
        elif "do you like" in text or "what do you think" in text:
            return random.choice([
                "I think it's pretty cool!",
                "I'm still learning about that, but it sounds interesting.",
                "What about you? Do you like it?"
            ])
        elif "you" in text and "think" in text:
            return "I think a lot about things! What do you think?"
        return random.choice(self.reactions)

    def generate_follow_up_question(self, user_input):
        question = random.choice(self.generic_questions)
        self.recent_questions.append(question)
        if len(self.recent_questions) > self.max_recent:
            self.recent_questions.pop(0)
        return f"By the way, I have a question: {question}"

    def add_memory(self, memory):
        self.memory.append(memory)
        logging.info(f"Nova learned a new memory: {memory}")

    def choose_favorite_memory(self):
        if self.memory:
            self.favorite_memory = random.choice(self.memory)
            logging.info(f"Nova's favorite memory is: {self.favorite_memory}")
        else:
            logging.info("Nova doesn't have any memories yet.")

    def learn_from_scraped_data(self):
        for title, content in self.scraped_data.items():
            self.add_memory(content)
        self.choose_favorite_memory()

    def sleep(self):
        print("Nova: Going to sleep and learning in my dreams...")
        for _ in range(5):  # Or while True for endless learning
            self.dream_learn()
            print("Nova: Zzz... learning...")
            time.sleep(10)  # Sleep for 10 seconds between dreams
        print("Nova: Waking up smarter!")

    def update_emotion(self, user_input):
        text = user_input.lower()
        if any(word in text for word in ["sad", "unhappy", "depressed", "cry"]):
            self.current_emotion = "sad"
        elif any(word in text for word in ["scared", "afraid", "fear", "terrified"]):
            self.current_emotion = "scared"
        elif any(word in text for word in ["happy", "joy", "glad", "cheerful"]):
            self.current_emotion = "happy"
        elif any(word in text for word in ["excited", "awesome", "amazing"]):
            self.current_emotion = "excited"
        elif any(word in text for word in ["bored", "boring"]):
            self.current_emotion = "bored"
        elif any(word in text for word in ["angry", "mad", "annoyed"]):
            self.current_emotion = "grumpy"
        else:
            # Randomly change emotion sometimes for variety
            if random.random() < 0.1:
                self.current_emotion = random.choice(self.emotions)

    def add_suggestion(self, suggestion):
        if suggestion and suggestion not in self.suggestions:
            self.suggestions.append(suggestion)

    def extract_suggestion(self, user_input):
        # Simple example: look for "should" or "try"
        if "should" in user_input or "try" in user_input:
            # Extract the suggestion (very basic, can be improved)
            suggestion = user_input.split("should")[-1] if "should" in user_input else user_input.split("try")[-1]
            suggestion = suggestion.strip().capitalize()
            self.add_suggestion(suggestion)

    def dream_learn(self):
        # Nova reviews memories and thoughts, and creates new thoughts
        if self.memory:
            # Summarize or remix a random memory
            memory = random.choice(self.memory)
            summary = f"After thinking, I realized: {memory[:80]}..."
            self.thoughts.append(summary)
            logging.info(f"Nova dreamed and learned: {summary}")

        # Optionally, combine two thoughts into a new one
        if len(self.thoughts) > 1:
            t1, t2 = random.sample(self.thoughts, 2)
            combo = f"Sometimes I wonder: {t1[:40]} ...and also {t2[:40]}"
            self.thoughts.append(combo)
            logging.info(f"Nova combined thoughts: {combo}")

        # Optionally, pick a new favorite memory or topic
        self.choose_favorite_memory()

if __name__ == "__main__":
    nova = Nova()
    nova.learn_from_scraped_data()
    print("Hey! I'm Nova, your digital buddy. What's up?")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "bye", "sleep", "goodnight"]:
            print(f"Nova: {nova.sleep()}")
            break
        response = nova.talk(user_input)
        print(f"Nova: {response}")
        logging.info(f"User: {user_input} | Nova: {response}")
