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
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
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
                if last.get("user_input") and last.get("response"):
                    f.write(f"You: {last['user_input']}\n")
                    f.write(f"Nova: {last['response']}\n")

    def sendresponse(self, response):
        coachfolder = os.path.join("Nova/coach_train")
        os.makedirs(coachfolder, exist_ok=True)
        json_path = os.path.join(coachfolder, "sentresponses.json")
        data = {
            "timestamp": time.time(),
            "response": response
        }
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                try:
                    responses = json.load(f)
                except json.JSONDecodeError:
                    responses = []
        else:
            responses = []
        responses.append(data)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(responses, f, indent=2)

    def log_processing(self, step, data):
        entry = {
            "timestamp": time.time(),
            "step": step,
            "data": data
        }
        with open("nova_logs/processing_log.txt", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def think(self, user_input, return_log=False):
        self.log_processing("think_start", {"user_input": user_input})
        reasoning_log = []

        # Candidate responses: only from thoughts and relevant memory
        candidate_responses = []

        # Use a thought if available
        if self.thoughts:
            candidate_responses.append(random.choice(self.thoughts))

        # Use memory if relevant
        relevant_memories = [
            m["response"] for m in self.memory
            if any(word in m["user_input"].lower() for word in user_input.lower().split())
        ]
        candidate_responses.extend(relevant_memories)

        # If nothing generated, fallback to a thought or a minimal echo
        if not candidate_responses:
            if self.thoughts:
                candidate_responses.append(random.choice(self.thoughts))
            else:
                candidate_responses.append(user_input)

        # Remove duplicates and empty responses
        candidate_responses = [resp for i, resp in enumerate(candidate_responses)
                               if resp and resp.strip() and resp not in candidate_responses[:i]]

        # Get logic/coach scores (from nueral_model)
        logic_scores = score_options(candidate_responses)
        reasoning_log.append(f"Logic scores: {logic_scores}")

        # Get moral scores (from moralcoach)
        moral_scores = [moral_score(resp) for resp in candidate_responses]
        reasoning_log.append(f"Moral scores: {moral_scores}")

        # Get naturalness scores (from naturalitycoach)
        natural_scores = [natural_score(resp) for resp in candidate_responses]
        reasoning_log.append(f"Natural scores: {natural_scores}")

        # Combine scores (simple sum, or use weights if you want)
        combined_scores = [
            logic["score"] + moral + natural
            for logic, moral, natural in zip(logic_scores, moral_scores, natural_scores)
        ]
        best_idx = int(torch.argmax(torch.tensor(combined_scores)))
        best_response = candidate_responses[best_idx]

        reasoning_log.append(f"Combined scores: {combined_scores}")
        reasoning_log.append(f"Chose response for best combined score: {combined_scores[best_idx]:.2f}")

        self.log_processing("think_end", {"chosen_response": best_response})
        if return_log:
            return best_response, reasoning_log
        return best_response

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
        self.sendresponse(moderated_response)
        self.conversation_history[-1] = (user_input, moderated_response)
        return moderated_response

    def proactive_topic_starter(self):
        # Remove all pre-gen topics, only return None or a dynamic suggestion if you want
        return None

    def random_response(self):
        return random.choice([
            "a", "aa", "aaa", "aaron", "ab", "abandoned", "abc", "aberdeen", "abilities", "ability", "able", "aboriginal", "abortion", "about", "above", "abraham", "abroad", "abs", "absence", "absent", "absolute", "absolutely", "absorption", "abstract", "abstracts", "abu", "abuse", "ac", "academic", "academics", "academy", "acc", "accent", "accept", "acceptable", "acceptance", "accepted", "accepting", "accepts", "access", "accessed", "accessibility", "accessible", "accessing", "accessories", "accessory", "accident", "accidents", "accommodate", "accommodation", "accommodations", "accompanied", "accompanying", "accomplish", "accomplished", "accordance", "according", "accordingly", "account", "accountability", "accounting", "accounts", "accreditation", "accredited", "accuracy", "accurate", "accurately", "accused", "acdbentity", "ace", "acer", "achieve", "achieved", "achievement", "achievements", "achieving", "acid", "acids", "acknowledge", "acknowledged", "acm", "acne", "acoustic", "acquire", "acquired", "acquisition", "acquisitions", "acre", "acres", "acrobat", "across", "acrylic", "act", "acting", "action", "actions", "activated", "activation", "active", "actively", "activists", "activities", "activity", "actor", "actors", "actress", "acts", "actual", "actually", "acute", "ad", "ada", "adam", "adams", "adaptation", "adapted", "adapter", "adapters", "adaptive", "adaptor", "add", "added", "addiction", "adding", "addition", "additional", "additionally", "additions", "address", "addressed", "addresses", "addressing", "adds", "adelaide", "adequate", "adidas", "adipex", "adjacent", "adjust", "adjustable", "adjusted", "adjustment", "adjustments", "admin", "administered", "administration", "administrative", "administrator", "administrators", "admission", "admissions", "admit", "admitted", "adobe", "adolescent", "adopt", "adopted", "adoption", "adrian", "ads", "adsl", "adult", "adults", "advance", "advanced", "advancement", "advances", "advantage", "advantages", "adventure", "adventures", "adverse", "advert", "advertise", "advertisement", "advertisements", "advertiser", "advertisers", "advertising", "advice", "advise", "advised", "advisor", "advisors", "advisory", "advocacy", "advocate", "adware", "ae", "aerial", "aerospace", "af", "affair", "affairs", "affect", "affected", "affecting", "affects", "affiliate", "affiliated", "affiliates", "affiliation", "afford", "affordable", "afghanistan", "afraid", "africa", "african", "after", "afternoon", "afterwards", "ag", "again", "against", "age", "aged", "agencies", "agency", "agenda", "agent", "agents", "ages", "aggregate", "aggressive", "aging", "ago", "agree", "agreed", "agreement", "agreements", "agrees", "agricultural", "agriculture", "ah", "ahead", "ai", "aid", "aids", "aim", "aimed", "aims", "air", "aircraft", "airfare", "airline", "airlines", "airplane", "airport", "airports", "aj", "ak", "aka", "al", "ala", "alabama", "alan", "alarm", "alaska", "albania", "albany", "albert", "alberta", "album", "albums", "albuquerque", "alcohol", "alert", "alerts", "alex", "alexander", "alexandria", "alfred", "algebra", "algeria", "algorithm", "algorithms", "ali", "alias", "alice", "alien", "align", "alignment", "alike", "alive", "all", "allah", "allan", "alleged", "allen", "allergy", "alliance", "allied", "allocated", "allocation", "allow", "allowance", "allowed", "allowing", "allows", "alloy", "almost", "alone", "along", "alot", "alpha", "alphabetical", "alpine", "already", "also", "alt", "alter", "altered", "alternate", "alternative", "alternatively", "alternatives", "although", "alto", "aluminium", "aluminum", "alumni", "always", "am", "amanda", "amateur", "amazing", "amazon", "amazoncom", "amazoncouk", "ambassador", "amber", "ambien", "ambient", "amd", "amend", "amended", "amendment", "amendments", "amenities", "america", "american", "americans", "americas", "amino", "among", "amongst", "amount", "amounts", "amp", "ampland", "amplifier", "amsterdam", "amy", "an", "ana", "anaheim", "anal", "analog", "analyses", "analysis", "analyst", "analysts", "analytical", "analyze", "analyzed", "anatomy", "anchor", "ancient", "and", "andale", "anderson", "andorra", "andrea", "andreas", "andrew", "andrews", "andy", "angel", "angela", "angeles", "angels", "anger", "angle", "angola", "angry", "animal", "animals", "animated", "animation", "anime", "ann", "anna", "anne", "annex", "annie", "anniversary", "annotated", "annotation", "announce", "announced", "announcement", "announcements", "announces", "annoying", "annual", "annually", "anonymous", "another", "answer", "answered", "answering", "answers", "ant", "antarctica", "antenna", "anthony", "anthropology", "anti", "antibodies", "antibody", "anticipated", "antigua", "antique", "antiques", "antivirus", "antonio", "anxiety", "any", "anybody", "anymore", "anyone", "anything", "anytime", "anyway", "anywhere", "aol", "ap", "apache", "apart", "apartment", "apartments", "api", "apnic", "apollo", "app", "apparatus", "apparel", "apparent", "apparently", "appeal", "appeals", "appear", "appearance", "appeared", "appearing", "appears", "appendix", "apple", "appliance", "appliances", "applicable", "applicant", "applicants", "application", "applications", "applied", "applies", "apply", "applying", "appointed", "appointment", "appointments", "appraisal", "appreciate", "appreciated", "appreciation", "approach", "approaches", "appropriate", "appropriations", "approval", "approve", "approved", "approx", "approximate", "approximately", "apps", "apr", "april", "apt", "aqua", "aquarium", "aquatic", "ar", "arab", "arabia", "arabic", "arbitrary", "arbitration", "arc", "arcade", "arch", "architect", "architects", "architectural", "architecture", "archive", "archived", "archives", "arctic", "are", "area", "areas", "arena", "arg", "argentina", "argue", "argued", "argument", "arguments", "arise", "arising", "arizona", "arkansas", "arlington", "arm", "armed", "armenia", "armor", "arms", "armstrong", "army", "arnold", "around", "arrange", "arranged", "arrangement", "arrangements", "array", "arrest", "arrested", "arrival", "arrivals", "arrive", "arrived", "arrives", "arrow", "art", "arthritis", "arthur", "article", "articles", "artificial", "artist", "artistic", "artists", "arts", "artwork", "aruba", "as", "asbestos", "ascii", "ash", "ashley", "asia", "asian", "aside", "asin", "ask", "asked", "asking", "asks", "asn", "asp", "aspect", "aspects", "aspnet", "ass", "assault", "assembled", "assembly", "assess", "assessed", "assessing", "assessment", "assessments", "asset", "assets", "assign", "assigned", "assignment", "assignments", "assist", "assistance", "assistant", "assisted", "assists", "associate", "associated", "associates", "association", "associations", "assume", "assumed", "assumes", "assuming", "assumption", "assumptions", "assurance", "assure", "assured", "asthma", "astrology", "astronomy", "asus", "at", "ata", "ate", "athens", "athletes", "athletic", "athletics", "ati", "atlanta", "atlantic", "atlas", "atm", "atmosphere", "atmospheric", "atom", "atomic", "attach", "attached", "attachment", "attachments", "attack", "attacked", "attacks", "attempt", "attempted", "attempting", "attempts", "attend", "attendance", "attended", "attending", "attention", "attitude", "attitudes", "attorney", "attorneys", "attract", "attraction", "attractions", "attractive", "attribute", "attributes", "au", "auburn", "auckland", "auction", "auctions", "aud", "audi", "audience", "audio", "audit", "auditor", "aug", "august", "aurora", "aus", "austin", "australia", "australian", "austria", "authentic", "authentication", "author", "authorities", "authority", "authorization", "authorized", "authors", "auto", "automated", "automatic", "automatically", "automation", "automobile", "automobiles", "automotive", "autos", "autumn", "av", "availability", "available", "avatar", "ave", "avenue", "average", "avg", "avi", "aviation", "avoid", "avoiding", "avon", "aw", "award", "awarded", "awards", "aware", "awareness", "away", "awesome", "awful", "axis", "aye", "az", "azerbaijan"
            "b", "ba", "babe", "babes", "babies", "baby", "bachelor", "back", "backed", "background", "backgrounds", "backing", "backup", "bacon", "bacteria", "bacterial", "bad", "badge", "badly", "bag", "baghdad", "bags", "bahamas", "bahrain", "bailey", "baker", "baking", "balance", "balanced", "bald", "bali", "ball", "ballet", "balloon", "ballot", "balls", "baltimore", "ban", "banana", "band", "bands", "bandwidth", "bang", "bangbus", "bangkok", "bangladesh", "bank", "banking", "bankruptcy", "banks", "banned", "banner", "banners", "baptist", "bar", "barbados", "barbara", "barbie", "barcelona", "bare", "barely", "bargain", "bargains", "barn", "barnes", "barrel", "barrier", "barriers", "barry", "bars", "base", "baseball", "based", "baseline", "basement", "basename", "bases", "basic", "basically", "basics", "basin", "basis", "basket", "basketball", "baskets", "bass", "bat", "batch", "bath", "bathroom", "bathrooms", "baths", "batman", "batteries", "battery", "battle", "battlefield", "bay", "bb", "bbc", "bbs", "bbw", "bc", "bd", "bdsm", "be", "beach", "beaches", "beads", "beam", "bean", "beans", "bear", "bearing", "bears", "beast", "beastality", "beastiality", "beat", "beatles", "beats", "beautiful", "beautifully", "beauty", "beaver", "became", "because", "become", "becomes", "becoming", "bed", "bedding", "bedford", "bedroom", "bedrooms", "beds", "bee", "beef", "been", "beer", "before", "began", "begin", "beginner", "beginners", "beginning", "begins", "begun", "behalf", "behavior", "behavioral", "behaviour", "behind", "beijing", "being", "beings", "belarus", "belfast", "belgium", "belief", "beliefs", "believe", "believed", "believes", "belize", "belkin", "bell", "belle", "belly", "belong", "belongs", "below", "belt", "belts", "ben", "bench", "benchmark", "bend", "beneath", "beneficial", "benefit", "benefits", "benjamin", "bennett", "benz", "berkeley", "berlin", "bermuda", "bernard", "berry", "beside", "besides", "best", "bestiality", "bestsellers", "bet", "beta", "beth", "better", "betting", "betty", "between", "beverage", "beverages", "beverly", "beyond", "bg", "bhutan", "bi", "bias", "bible", "biblical", "bibliographic", "bibliography", "bicycle", "bid", "bidder", "bidding", "bids", "big", "bigger", "biggest", "bike", "bikes", "bikini", "bill", "billing", "billion", "bills", "billy", "bin", "binary", "bind", "binding", "bingo", "bio", "biodiversity", "biographies", "biography", "biol", "biological", "biology", "bios", "biotechnology", "bird", "birds", "birmingham", "birth", "birthday", "bishop", "bit", "bitch", "bite", "bits", "biz", "bizarre", "bizrate", "bk", "bl", "black", "blackberry", "blackjack", "blacks", "blade", "blades", "blah", "blair", "blake", "blame", "blank", "blanket", "blast", "bleeding", "blend", "bless", "blessed", "blind", "blink", "block", "blocked", "blocking", "blocks", "blog", "blogger", "bloggers", "blogging", "blogs", "blond", "blonde", "blood", "bloody", "bloom", "bloomberg", "blow", "blowing", "blue", "blues", "bluetooth", "blvd", "bm", "bmw", "bo", "board", "boards", "boat", "boating", "boats", "bob", "bobby", "boc", "bodies", "body", "bold", "bolivia", "bolt", "bomb", "bon", "bond", "bondage", "bonds", "bone", "bones", "bonus", "book", "booking", "bookings", "bookmark", "bookmarks", "books", "bookstore", "bool", "boolean", "boom", "boost", "boot", "booth", "boots", "border", "borders", "bored", "boring", "born", "borough", "bosnia", "boss", "boston", "both", "bother", "botswana", "bottle", "bottles", "bottom", "bought", "boulder", "boulevard", "bound", "boundaries", "boundary", "bouquet", "boutique", "bow", "bowl", "bowling", "box", "boxed", "boxes", "boxing", "boy", "boys", "bp", "br", "bra", "bracelet", "bracelets", "bracket", "brad", "bradford", "bradley", "brain", "brake", "brakes", "branch", "branches", "brand", "brandon", "brands", "bras", "brass", "brave", "brazil", "brazilian", "breach", "bread", "break", "breakdown", "breakfast", "breaking", "breaks",  "breath", "breathing", "breed", "breeding", "breeds", "brian", "brick", "bridal", "bride", "bridge", "bridges", "brief", "briefing", "briefly", "briefs", "bright", "brighton", "brilliant", "bring", "bringing", "brings", "brisbane", "bristol", "britain", "britannica", "british", "britney", "broad", "broadband", "broadcast", "broadcasting", "broader", "broadway", "brochure", "brochures", "broke", "broken", "broker", "brokers", "bronze", "brook", "brooklyn", "brooks", "bros", "brother", "brothers", "brought", "brown", "browse", "browser", "browsers", "browsing", "bruce", "brunei", "brunette", "brunswick", "brush", "brussels", "brutal", "bryan", "bryant", "bs", "bt", "bubble", "buck", "bucks", "budapest", "buddy", "budget", "budgets", "buf", "buffalo", "buffer", "bufing", "bug", "bugs", "build", "builder", "builders", "building", "buildings", "builds", "built", "bukkake", "bulgaria", "bulgarian", "bulk", "bull", "bullet", "bulletin", "bumper", "bunch", "bundle", "bunny", "burden", "bureau", "buried", "burke", "burlington", "burn", "burner", "burning", "burns", "burst", "burton", "bus", "buses", "bush", "business", "businesses", "busty", "busy", "but", "butler", "butt", "butter", "butterfly", "button", "buttons", "butts", "buy", "buyer", "buyers", "buying", "buys", "buzz", "bw", "by", "bye", "byte", "bytes"
            "c", "ca", "cab", "cabin", "cabinet", "cabinets", "cable", "cables", "cache", "cached", "cad", "cadillac", "cafe", "cage", "cake", "cakes", "cal", "calcium", "calculate", "calculated", "calculation", "calculations", "calculator", "calculators", "calendar", "calendars", "calgary", "calibration", "calif", "california", "call", "called", "calling", "calls", "calm", "calvin", "cam", "cambodia", "cambridge", "camcorder", "camcorders", "came", "camel", "camera", "cameras", "cameron", "cameroon", "camp", "campaign", "campaigns", "campbell", "camping", "camps", "campus", "cams", "can", "canada", "canadian", "canal", "canberra", "cancel", "cancellation", "cancelled", "cancer", "candidate", "candidates", "candle", "candles", "candy", "cannon", "canon", "cant", "canvas", "canyon", "cap", "capabilities", "capability", "capable", "capacity", "cape", "capital", "capitol", "caps", "captain", "capture", "captured", "car", "carb", "carbon", "card", "cardiac", "cardiff", "cardiovascular", "cards", "care", "career", "careers", "careful", "carefully", "carey", "cargo", "caribbean", "caring", "carl", "carlo", "carlos", "carmen", "carnival", "carol", "carolina", "caroline", "carpet", "carried", "carrier", "carriers", "carries", "carroll", "carry", "carrying", "cars", "cart", "carter", "cartoon", "cartoons", "cartridge", "cartridges", "cas", "casa", "case", "cases", "casey", "cash", "cashiers", "casino", "casinos", "casio", "cassette", "cast", "casting", "castle", "casual", "cat", "catalog", "catalogs", "catalogue", "catalyst", "catch", "categories", "category", "catering", "cathedral", "catherine", "catholic", "cats", "cattle", "caught", "cause", "caused", "causes", "causing", "caution", "cave", "cayman", "cb", "cbs", "cc", "ccd", "cd", "cdna", "cds", "cdt", "ce", "cedar", "ceiling", "celebrate", "celebration", "celebrities", "celebrity", "celebs", "cell", "cells", "cellular", "celtic", "cement", "cemetery", "census", "cent", "center", "centered", "centers", "central", "centre", "centres", "cents", "centuries", "century", "ceo", "ceramic", "ceremony", "certain", "certainly", "certificate", "certificates", "certification", "certified", "cest", "cet", "cf", "cfr", "cg", "cgi", "ch", "chad", "chain", "chains", "chair", "chairman", "chairs", "challenge", "challenged", "challenges", "challenging", "chamber", "chambers", "champagne", "champion", "champions", "championship", "championships", "chan", "chance", "chancellor", "chances", "change", "changed", "changelog", "changes", "changing", "channel", "channels", "chaos", "chapel", "chapter", "chapters", "char", "character", "characteristic", "characteristics", "characterization", "characterized", "characters", "charge", "charged", "charger", "chargers", "charges", "charging", "charitable", "charity", "charles", "charleston", "charlie", "charlotte", "charm", "charming", "charms", "chart", "charter", "charts", "chase", "chassis", "chat", "cheap", "cheaper", "cheapest", "cheat", "cheats", "check", "checked", "checking", "checklist", "checkout", "checks", "cheers", "cheese", "chef", "chelsea", "chem", "chemical", "chemicals", "chemistry", "chen", "cheque", "cherry", "chess", "chest", "chester", "chevrolet", "chevy", "chi", "chicago", "chick", "chicken", "chicks", "chief", "child", "childhood", "children", "childrens", "chile", "china", "chinese", "chip", "chips", "cho", "chocolate", "choice", "choices", "choir", "cholesterol", "choose", "choosing", "chorus", "chose", "chosen", "chris", "christ", "christian", "christianity", "christians", "christina", "christine", "christmas", "christopher", "chrome", "chronic", "chronicle", "chronicles", "chrysler", "chubby", "chuck", "church", "churches", "ci", "cia", "cialis", "ciao", "cigarette", "cigarettes", "cincinnati", "cindy", "cinema", "cingular", "cio", "cir", "circle", "circles", "circuit", "circuits", "circular", "circulation", "circumstances", "circus", "cisco", "citation", "citations", "cite", "cited", "cities", "citizen", "citizens", "citizenship", "city", "citysearch", "civic", "civil", "civilian", "civilization", "cj", "cl", "claim", "claimed", "claims", "claire", "clan", "clara", "clarity", "clark", "clarke", "class", "classes", "classic", "classical", "classics", "classification", "classified", "classifieds", "classroom", "clause", "clay", "clean", "cleaner", "cleaners", "cleaning", "cleanup", "clear", "clearance", "cleared", "clearing", "clearly", "clerk", "cleveland", "click", "clicking", "clicks", "client", "clients", "cliff", "climate", "climb", "climbing", "clinic", "clinical", "clinics", "clinton", "clip", "clips", "clock", "clocks", "clone", "close", "closed", "closely", "closer", "closes", "closest", "closing", "closure", "cloth", "clothes", "clothing", "cloud", "clouds", "cloudy", "club", "clubs", "cluster", "clusters", "cm", "cms", "cn", "cnet", "cnetcom", "cnn", "co", "coach", "coaches", "coaching", "coal", "coalition", "coast", "coastal", "coat", "coated", "coating", "cod", "code", "codes", "coding", "coffee", "cognitive", "cohen", "coin", "coins", "col", "cold", "cole", "coleman", "colin", "collaboration", "collaborative", "collapse", "collar", "colleague", "colleagues", "collect", "collectables", "collected", "collectible", "collectibles", "collecting", "collection", "collections", "collective", "collector", "collectors", "college", "colleges", "collins", "cologne", "colombia", "colon", "colonial", "colony", "color", "colorado", "colored", "colors", "colour", "colours", "columbia", "columbus", "column", "columnists", "columns", "com", "combat", "combination", "combinations", "combine", "combined", "combines", "combining", "combo", "come", "comedy", "comes", "comfort", "comfortable", "comic", "comics", "coming", "comm", "command", "commander", "commands", "comment", "commentary", "commented", "comments", "commerce", "commercial", "commission", "commissioner", "commissioners", "commissions", "commit", "commitment", "commitments", "committed", "committee", "committees", "commodities", "commodity", "common", "commonly", "commons", "commonwealth", "communicate", "communication", "communications", "communist", "communities", "community", "comp", "compact", "companies", "companion", "company", "compaq", "comparable", "comparative", "compare", "compared", "comparing", "comparison", "comparisons", "compatibility", "compatible", "compensation", "compete", "competent", "competing", "competition", "competitions", "competitive", "competitors", "compilation", "compile", "compiled", "compiler", "complaint", "complaints", "complement", "complete", "completed", "completely", "completing", "completion", "complex", "complexity", "compliance", "compliant", "complicated", "complications", "complimentary", "comply", "component", "components", "composed", "composer", "composite", "composition", "compound", "compounds", "comprehensive", "compressed", "compression", "compromise", "computation", "computational", "compute", "computed", "computer", "computers", "computing", "con", "concentrate", "concentration", "concentrations", "concept", "concepts", "conceptual", "concern", "concerned", "concerning", "concerns", "concert", "concerts", "conclude", "concluded", "conclusion", "conclusions", "concord", "concrete", "condition", "conditional", "conditioning", "conditions", "condo", "condos", "conduct", "conducted", "conducting", "conf", "conference", "conferences", "conferencing", "confidence", "confident", "confidential", "confidentiality", "config", "configuration", "configure", "configured", "configuring", "confirm", "confirmation", "confirmed", "conflict", "conflicts", "confused", "confusion", "congo", "congratulations", "congress", "congressional", "conjunction", "connect", "connected", "connecticut", "connecting", "connection", "connections", "connectivity", "connector", "connectors", "cons", "conscious", "consciousness", "consecutive", "consensus", "consent", "consequence", "consequences", "consequently", "conservation", "conservative", "consider", "considerable", "consideration", "considerations", "considered", "considering", "considers", "consist", "consistency", "consistent", "consistently", "consisting", "consists", "console", "consoles", "consolidated", "consolidation", "consortium", "conspiracy", "const", "constant", "constantly", "constitute", "constitutes", "constitution", "constitutional", "constraint", "constraints", "construct", "constructed", "construction", "consult", "consultancy", "consultant", "consultants", "consultation", "consulting", "consumer", "consumers", "consumption", "contact", "contacted", "contacting", "contacts", "contain", "contained", "container", "containers", "containing", "contains", "contamination", "contemporary", "content", "contents", "contest", "contests", "context", "continent", "continental", "continually", "continue", "continued", "continues", "continuing", "continuity", "continuous", "continuously", "contract", "contracting", "contractor", "contractors", "contracts", "contrary", "contrast", "contribute", "contributed", "contributing", "contribution", "contributions", "contributor", "contributors", "control", "controlled", "controller", "controllers", "controlling", "controls", "controversial", "controversy", "convenience", "convenient", "convention", "conventional", "conventions", "convergence", "conversation", "conversations", "conversion", "convert", "converted", "converter", "convertible", "convicted", "conviction", "convinced", "cook", "cookbook", "cooked", "cookie", "cookies", "cooking", "cool", "cooler", "cooling", "cooper", "cooperation", "cooperative", "coordinate", "coordinated", "coordinates", "coordination", "coordinator", "cop", "cope", "copied", "copies", "copper", "copy", "copying", "copyright", "copyrighted", "copyrights", "coral", "cord", "cordless", "core", "cork", "corn", "cornell", "corner", "corners", "cornwall", "corp", "corporate", "corporation", "corporations", "corps", "corpus", "correct", "corrected", "correction", "corrections", "correctly", "correlation", "correspondence", "corresponding", "corruption", "cos", "cosmetic", "cosmetics", "cost", "costa", "costs", "costume", "costumes", "cottage", "cottages", "cotton", "could", "council", "councils", "counsel", "counseling", "count", "counted", "counter", "counters", "counties", "counting", "countries", "country", "counts", "county", "couple", "coupled", "couples", "coupon", "coupons", "courage", "courier", "course", "courses", "court", "courtesy", "courts", "cove", "cover", "coverage", "covered", "covering", "covers", "cow", "cowboy", "cox", "cp", "cpu", "cr", "crack", "cradle", "craft", "crafts", "craig", "crap", "craps", "crash", "crawford", "crazy", "cream", "create", "created", "creates", "creating", "creation", "creations", "creative", "creativity", "creator", "creature", "creatures", "credit", "credits", "creek", "crest", "crew", "cricket", "crime", "crimes", "criminal", "crisis", "criteria", "criterion", "critical", "criticism", "critics", "crm", "croatia", "crop", "crops", "cross", "crossing", "crossword", "crowd", "crown", "crucial", "crude", "cruise", "cruises", "cruz", "cry", "crystal", "cs", "css", "cst", "ct", "cu", "cuba", "cube", "cubic", "cuisine", "cult", "cultural", "culture", "cultures", "cumulative", "cup", "cups", "cure", "curious", "currencies", "currency", "current", "currently", "curriculum", "cursor", "curtis", "curve", "curves", "custody", "custom", "customer", "customers", "customise", "customize", "customized", "customs", "cut", "cute", "cuts", "cutting", "cv", "cvs", "cw", "cyber", "cycle", "cycles", "cycling", "cylinder", "cyprus", "cz", "czech"
            "d", "da", "dad", "daddy", "daily", "dairy", "daisy", "dakota", "dale", "dallas", "dam", "damage", "damaged", "damages", "dame", "dan", "dana", "dance", "dancing", "danger", "dangerous", "daniel", "danish", "danny", "dans", "dare", "dark", "darkness", "darwin", "das", "dash", "dat", "data", "database", "databases", "date", "dated", "dates", "dating", "daughter", "daughters", "dave", "david", "davidson", "davis", "dawn", "day", "days", "dayton", "db", "dc", "dd", "ddr", "de", "dead", "deadline", "deadly", "deaf", "deal", "dealer", "dealers", "dealing", "deals", "dealt", "dealtime", "dean", "dear", "death", "deaths", "debate", "debian", "deborah", "debt", "debug", "debut", "dec", "decade", "decades", "december", "decent", "decide", "decided", "decimal", "decision", "decisions", "deck", "declaration", "declare", "declared", "decline", "declined", "decor", "decorating", "decorative", "decrease", "decreased", "dedicated", "dee", "deemed", "deep", "deeper", "deeply", "deer", "def", "default", "defeat", "defects", "defence", "defend", "defendant", "defense", "defensive", "deferred", "deficit", "define", "defined", "defines", "defining", "definitely", "definition", "definitions", "degree", "degrees", "del", "delaware", "delay", "delayed", "delays", "delegation", "delete", "deleted", "delhi", "delicious", "delight", "deliver", "delivered", "delivering", "delivers", "delivery", "dell", "delta", "deluxe", "dem", "demand", "demanding", "demands", "demo", "democracy", "democrat", "democratic", "democrats", "demographic", "demonstrate", "demonstrated", "demonstrates", "demonstration", "den", "denial", "denied", "denmark", "dennis", "dense", "density", "dental", "dentists", "denver", "deny", "department", "departmental", "departments", "departure", "depend", "dependence", "dependent", "depending", "depends", "deployment", "deposit", "deposits", "depot", "depression", "dept", "depth", "deputy", "der", "derby", "derek", "derived", "des", "descending", "describe", "described", "describes", "describing", "description", "descriptions", "desert", "deserve", "design", "designated", "designation", "designed", "designer", "designers", "designing", "designs", "desirable", "desire", "desired", "desk", "desktop", "desktops", "desperate", "despite", "destination", "destinations", "destiny", "destroy", "destroyed", "destruction", "detail", "detailed", "details", "detect", "detected", "detection", "detective", "detector", "determination", "determine", "determined", "determines", "determining", "detroit", "deutsch", "deutsche", "deutschland", "dev", "devel", "develop", "developed", "developer", "developers", "developing", "development", "developmental", "developments", "develops", "deviant", "deviation", "device", "devices", "devil", "devon", "devoted", "df", "dg", "dh", "di", "diabetes", "diagnosis", "diagnostic", "diagram", "dial", "dialog", "dialogue", "diameter", "diamond", "diamonds", "diana", "diane", "diary", "dice", "dictionaries", "dictionary", "did", "die", "died", "diego", "dies", "diesel", "diet", "dietary", "diff", "differ", "difference", "differences", "different", "differential", "differently", "difficult", "difficulties", "difficulty", "diffs", "dig", "digest", "digit", "digital", "dim", "dimension", "dimensional", "dimensions", "dining", "dinner", "dip", "diploma", "dir", "direct", "directed", "direction", "directions", "directive", "directly", "director", "directories", "directors", "directory", "dirt", "dirty", "dis", "disabilities", "disability", "disable", "disabled", "disagree", "disappointed", "disaster", "disc", "discharge", "disciplinary", "discipline", "disciplines", "disclaimer", "disclaimers", "disclose", "disclosure", "disco", "discount", "discounted", "discounts", "discover", "discovered", "discovery", "discrete", "discretion", "discrimination", "discs", "discuss", "discussed", "discusses", "discussing", "discussion", "discussions", "disease", "diseases", "dish", "dishes", "disk", "disks", "disney", "disorder", "disorders", "dispatch", "dispatched", "display", "displayed", "displaying", "displays", "disposal", "disposition", "dispute", "disputes", "dist", "distance", "distances", "distant", "distinct", "distinction", "distinguished", "distribute", "distributed", "distribution", "distributions", "distributor", "distributors", "district", "districts", "disturbed", "div", "dive", "diverse", "diversity", "divide", "divided", "dividend", "divine", "diving", "division", "divisions", "divorce", "divx", "diy", "dj", "dk", "dl", "dm", "dna", "dns", "do", "doc", "dock", "docs", "doctor", "doctors", "doctrine", "document", "documentary", "documentation", "documentcreatetextnode", "documented", "documents", "dod", "dodge", "doe", "does", "dog", "dogs", "doing", "doll", "dollar", "dollars", "dolls", "dom", "domain", "domains", "dome", "domestic", "dominant", "dominican", "don", "donald", "donate", "donated", "donation", "donations", "done", "donna", "donor", "donors", "dont", "doom", "door", "doors", "dos", "dosage", "dose", "dot", "double", "doubt", "doug", "douglas", "dover", "dow", "down", "download", "downloadable", "downloadcom", "downloaded", "downloading", "downloads", "downtown", "dozen", "dozens", "dp", "dpi", "dr", "draft", "drag", "dragon", "drain", "drainage", "drama", "dramatic", "dramatically", "draw", "drawing", "drawings", "drawn", "draws", "dream", "dreams", "dress", "dressed", "dresses", "dressing", "drew", "dried", "drill", "drilling", "drink", "drinking", "drinks", "drive", "driven", "driver", "drivers", "drives", "driving", "drop", "dropped", "drops", "drove", "drug", "drugs", "drum", "drums", "drunk", "dry", "dryer", "ds", "dsc", "dsl", "dt", "dts", "du", "dual", "dubai", "dublin", "duck", "dude", "due", "dui", "duke", "dumb", "dump", "duncan", "duo", "duplicate", "durable", "duration", "durham", "during", "dust", "dutch", "duties", "duty", "dv", "dvd", "dvds", "dx", "dying", "dylan", "dynamic", "dynamics"
            "e", "ea", "each", "eagle", "eagles", "ear", "earl", "earlier", "earliest", "early", "earn", "earned", "earning", "earnings", "earrings", "ears", "earth", "earthquake", "ease", "easier", "easily", "east", "easter", "eastern", "easy", "eat", "eating", "eau", "ebay", "ebony", "ebook", "ebooks", "ec", "echo", "eclipse", "eco", "ecological", "ecology", "ecommerce", "economic", "economics", "economies", "economy", "ecuador", "ed", "eddie", "eden", "edgar", "edge", "edges", "edinburgh", "edit", "edited", "editing", "edition", "editions", "editor", "editorial", "editorials", "editors", "edmonton", "eds", "edt", "educated", "education", "educational", "educators", "edward", "edwards", "ee", "ef", "effect", "effective", "effectively", "effectiveness", "effects", "efficiency", "efficient", "efficiently", "effort", "efforts", "eg", "egg", "eggs", "egypt", "egyptian", "eh", "eight", "either", "ejaculation", "el", "elder", "elderly", "elect", "elected", "election", "elections", "electoral", "electric", "electrical", "electricity", "electro", "electron", "electronic", "electronics", "elegant", "element", "elementary", "elements", "elephant", "elevation", "eleven", "eligibility", "eligible", "eliminate", "elimination", "elite", "elizabeth", "ellen", "elliott", "ellis", "else", "elsewhere", "elvis", "em", "emacs", "email", "emails", "embassy", "embedded", "emerald", "emergency", "emerging", "emily", "eminem", "emirates", "emission", "emissions", "emma", "emotional", "emotions", "emperor", "emphasis", "empire", "empirical", "employ", "employed", "employee", "employees", "employer", "employers", "employment", "empty", "en", "enable", "enabled", "enables", "enabling", "enb", "enclosed", "enclosure", "encoding", "encounter", "encountered", "encourage", "encouraged", "encourages", "encouraging", "encryption", "encyclopedia", "end", "endangered", "ended", "endif", "ending", "endless", "endorsed", "endorsement", "ends", "enemies", "enemy", "energy", "enforcement", "eng", "engage", "engaged", "engagement", "engaging", "engine", "engineer", "engineering", "engineers", "engines", "england", "english", "enhance", "enhanced", "enhancement", "enhancements", "enhancing", "enjoy", "enjoyed", "enjoying", "enlarge", "enlargement", "enormous", "enough", "enquiries", "enquiry", "enrolled", "enrollment", "ensemble", "ensure", "ensures", "ensuring", "ent", "enter", "entered", "entering", "enterprise", "enterprises", "enters", "entertaining", "entertainment", "entire", "entirely", "entities", "entitled", "entity", "entrance", "entrepreneur", "entrepreneurs", "entries", "entry", "envelope", "environment", "environmental", "environments", "enzyme", "eos", "ep", "epa", "epic", "epinions", "epinionscom", "episode", "episodes", "epson", "eq", "equal", "equality", "equally", "equation", "equations", "equilibrium", "equipment", "equipped", "equity", "equivalent", "er", "era", "eric", "ericsson", "erik", "erotic", "erotica", "erp", "error", "errors", "es", "escape", "escort", "escorts", "especially", "espn", "essay", "essays", "essence", "essential", "essentially", "essentials", "essex", "est", "establish", "established", "establishing", "establishment", "estate", "estates", "estimate", "estimated", "estimates", "estimation", "estonia", "et", "etc", "eternal", "ethernet", "ethical", "ethics", "ethiopia", "ethnic", "eu", "eugene", "eur", "euro", "europe", "european", "euros", "ev", "eva", "eval", "evaluate", "evaluated", "evaluating", "evaluation", "evaluations", "evanescence", "evans", "eve", "even", "evening", "event", "events", "eventually", "ever", "every", "everybody", "everyday", "everyone", "everything", "everywhere", "evidence", "evident", "evil", "evolution", "ex", "exact", "exactly", "exam", "examination", "examinations", "examine", "examined", "examines", "examining", "example", "examples", "exams", "exceed", "excel", "excellence", "excellent", "except", "exception", "exceptional", "exceptions", "excerpt", "excess", "excessive", "exchange", "exchanges", "excited", "excitement", "exciting", "exclude", "excluded", "excluding", "exclusion", "exclusive", "exclusively", "excuse", "exec", "execute", "executed", "execution", "executive", "executives", "exempt", "exemption", "exercise", "exercises", "exhaust", "exhibit", "exhibition", "exhibitions", "exhibits", "exist", "existed", "existence", "existing", "exists", "exit", "exotic", "exp", "expand", "expanded", "expanding", "expansion", "expansys", "expect", "expectations", "expected", "expects", "expedia", "expenditure", "expenditures", "expense", "expenses", "expensive", "experience", "experienced", "experiences", "experiencing", "experiment", "experimental", "experiments", "expert", "expertise", "experts", "expiration", "expired", "expires", "explain", "explained", "explaining", "explains", "explanation", "explicit", "explicitly", "exploration", "explore", "explorer", "exploring", "explosion", "expo", "export", "exports", "exposed", "exposure", "express", "expressed", "expression", "expressions", "ext", "extend", "extended", "extending", "extends", "extension", "extensions", "extensive", "extent", "exterior", "external", "extra", "extract", "extraction", "extraordinary", "extras", "extreme", "extremely", "eye", "eyed", "eyes", "ez"

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
        # Remove all pre-gen topics, only return None or a dynamic suggestion if you want
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
