#Nova AI: Code Explanation

Imports and Setup

*import os*
*import random*
*import logging*
*import time*
*import json*
*import string*
*import re*
*from nueral_model import score_options*
*from moralcoach import moral_score*
*from naturalitycoach import natural_score*

**Imports: Standard Python libraries for file handling, randomness, logging, time, JSON, string manipulation, and regex.**
**Coach Imports: Imports scoring functions from your coach modules.**

Logging and File Paths
*log_folder = "nova_logs"*
*os.makedirs(log_folder, exist_ok=True)*
*logging.basicConfig(filename=os.path.join(log_folder, "nova_log.txt"), level=logging.INFO, format="%(asctime)s - %(message)s")*

*scraped_data_folder = "scraped_data/scraped_data"*
*thoughts_folder = "nova_memory/thoughts"*
*memory_file = "nova_memory/personality.json"*
*saved_memory_file = "nova_memory/memories.json"*

**Logging: Sets up a log folder and log file for Nova’s activity.**
**File Paths: Defines where Nova stores scraped data, thoughts, personality, and memories.**

Utility: Load Scraped Data

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

**Loads all .txt files from the scraped data folder.**
**Stores the first line as the title and the rest as content in a dictionary.**

Nova Class: Initialization
class Nova:
    def __init__(self):
        self.memory = []
        self.scraped_data = load_scraped_data()
        self.favorite_memory = None
        self.last_topic = None
        self.conversation_history = []
        self.awaiting_continue = False
        # ... more attributes ...
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

**Initializes Nova’s state: memory, scraped data, conversation history, and personality traits.**
**Loads personality and memory from files.**
**Sets Nova as “on” by default.**

Loading and Saving Thoughts, Personality, and Memory
    load_thoughts: Loads Nova’s private thoughts from files.
load_personality / save_personality: Loads and saves Nova’s personality traits as JSON.
load_memory / save_memory: Loads and saves conversation history from/to log files.
save_dream: Saves Nova’s dreams to a file.
Logging and Data Retrieval
log_processing: Logs Nova’s internal processing steps for debugging or transparency.
get_scraped_response: Finds the most relevant scraped fact for a user query.
Sleep and Dream Functions
sleep: Nova “sleeps,” generates a dream, and wakes up.
procedural_dream: Creates a dream narrative using recent memories and random elements.
Sharing Thoughts and Dreams
maybe_share_thought: 30% chance to share a private thought.
maybe_share_dream: 20% chance to share a private dream.

Core Reasoning: think Method
        
        def think(self, user_input, return_log=False):
        reasoning_log = []
        candidate_responses = [
            f"{self.personality_prefix()}What else would you like to talk about?",
            f"{self.personality_prefix()}I'm here if you want to share more.",
            f"{self.personality_prefix()}That sounds interesting! Tell me more?",
        ]
        logic_response, logic_scores = score_options(user_input, candidate_responses)
        moral_scores = [moral_score(resp) for resp in candidate_responses]
        natural_scores = [natural_score(resp) for resp in candidate_responses]
        combined_scores = [
            logic + moral + natural
            for logic, moral, natural in zip(logic_scores, moral_scores, natural_scores)
        ]
        best_idx = int(torch.argmax(torch.tensor(combined_scores)))
        best_response = candidate_responses[best_idx]
        # ...
        if return_log:
            return best_response, reasoning_log
        return best_response

Generates candidate responses.
Scores each response using logic, moral, and naturality coaches.
Combines scores and selects the best response.
Optionally returns a reasoning log for transparency.

Conversation Handling: talk Method

        def talk(self, user_input):
        user_input = user_input.strip()
        self.conversation_history.append((user_input, None))
        self.update_emotion(user_input)
        self.extract_suggestion(user_input)
        response, reasoning_log = self.think(user_input, return_log=True)
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
        self.conversation_history[-1] = (user_input, moderated_response)
        return moderated_response

Processes user input: updates emotion, suggestions, and memory.
Calls think to generate a response and then moderates it.
Updates Nova’s personality and saves memory.

Helper Methods
random_response: Returns a random generic response.
reason_about: Returns a reasoning statement about a topic.
recall_memory: Sometimes references a relevant past memory.
personality_prefix: Adds personality-based prefixes to Nova’s speech.
natural_response: Builds a fact-based response with personality flavor.
reflect_on_fact: Reflects on a fact based on personality.
extract_suggestion: Extracts suggestions from user input.
extract_topic: Extracts topics from user input.
generate_follow_up_question / generate_dynamic_question: Generates follow-up questions.
ask_to_learn: Asks the user to teach Nova something new.
update_emotion: Updates Nova’s emotion based on user input.
update_personality: Adjusts personality traits based on sentiment.
proactive_topic_starter: Sometimes starts a new topic.
get_dominant_personality: Returns the dominant personality trait.
analyze_sentiment: Analyzes sentiment of user input.
moderate_response: Adjusts response tone if needed.
continue_conversation / stop_conversation: Checks if the conversation should continue or stop.
learn_from_conversation: Learns new facts from user corrections.
shutdown / startup: Powers Nova off/on.

Main Loop

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

Starts Nova and enters a chat loop.
Handles special commands: exit, shutdown, startup, reboot, sleep, stasis.
Calls Nova’s talk method for normal conversation.
Logs all interactions.

Summary
Nova is a modular, personality-driven AI chatbot.
She uses multiple “coach” modules to score and select her responses.
She maintains memory, personality, and context across conversations.
The main loop allows for interactive chatting and special commands.