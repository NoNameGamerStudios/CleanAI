import os
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time
import random
import re

# Set up logging
log_folder = "scraped_data"
os.makedirs(log_folder, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_folder, "scraper_log.txt"), level=logging.INFO, format="%(asctime)s - %(message)s")

# List of User-Agent strings to rotate
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
    'Mozilla/5.0 (Linux; Android 10; Pixel 4 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_1 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/537.36'
]

def fetch_urls_from_duckduckgo(query, num_results=20, max_pages=2):
    all_urls = []
    for page in range(0, max_pages):
        start = page * 10
        search_url = f'https://html.duckduckgo.com/html/?q={query}&s={start}'
        headers = {'User-Agent': random.choice(user_agents)}
        try:
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            # Find all <a> tags with hrefs that look like real URLs
            for a in soup.find_all('a', href=True):
                url = a['href']
                if url.startswith('http') and 'duckduckgo.com' not in url and url not in all_urls:
                    all_urls.append(url)
            if len(all_urls) >= num_results:
                break
            time.sleep(2)
        except Exception as e:
            logging.error(f"DuckDuckGo error: {e}")
            time.sleep(5)
            continue
    return all_urls[:num_results]

#def fetch_urls_from_google(query, num_results=20, max_pages=2):
 #   all_urls = []
 #   for page in range(0, max_pages):
 #       start = page * 10
 #       search_url = f"https://www.google.com/search?q={query}&start={start}"
 #       headers = {
 #           'User-Agent': random.choice(user_agents),
  #          'Accept-Language': 'en-US,en;q=0.9'
  #      }
 #       try:
 #           response = requests.get(search_url, headers=headers, timeout=10)
 #           response.raise_for_status()
 ##           soup = BeautifulSoup(response.text, 'html.parser')
 #           for a in soup.find_all('a', href=True):
 #               href = a['href']
 #               if href.startswith('/url?q='):
 #                   url = href.split('/url?q=')[1].split('&')[0]
 #                   if url.startswith('http') and url not in all_urls:
 #                       all_urls.append(url)
 #           if len(all_urls) >= num_results:
 #               break
 #           time.sleep(2)
 #       except Exception as e:
 #           logging.error(f"Google error: {e}")
 #           time.sleep(5)
 #           continue
 #   return all_urls[:num_results]



def scrape_content(url):
    try:
        logging.info(f"Starting to scrape: {url}")
        response = requests.get(url, headers={'User-Agent': random.choice(user_agents)}, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        # ...existing cleaning code...
        main_content = soup.get_text(separator='\n')
        # Only save if content is substantial
        if not main_content or len(main_content.strip()) < 200:
            logging.warning(f"Content too short or empty for {url}")
            return None, None
        title = soup.title.string.strip() if soup.title and soup.title.string else 'No title'
        return title, main_content
    except Exception as e:
        logging.error(f"Error scraping {url}: {e}")
        return None, None

def scrape_urls(urls):
    all_scraped_data = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(scrape_content, url): url for url in urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                title, content = future.result()
                if title and content:
                    all_scraped_data.append((title, content))
            except Exception as e:
                logging.error(f"Error processing URL {url}: {e}")
    return all_scraped_data

def main():
    search_query = input("Enter your search query: ")
    search_query_encoded = search_query.replace(" ", "+")
    num_results = 20

    print(f"Fetching URLs for search query: {search_query} from DuckDuckGo...")
    ddg_urls = fetch_urls_from_duckduckgo(search_query_encoded, num_results=num_results, max_pages=2)

    all_urls = list(dict.fromkeys(ddg_urls))  # Remove duplicates, preserve order

    if all_urls:
        print(f"Found {len(all_urls)} URLs. Starting to scrape...")
        scraped_data = scrape_urls(all_urls)
        if scraped_data:
            folder_name = os.path.join(os.path.dirname(__file__), "scraped_data")
            os.makedirs(folder_name, exist_ok=True)
            for idx, (title, content) in enumerate(scraped_data):
                safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', title)[:50]
                filename = os.path.join(folder_name, f"{safe_title or 'untitled'}_{idx}.txt")
                with open(filename, "w", encoding="utf-8") as f:
                    
                    f.write(f"{content}")
            print(f"Scraped content saved to '{folder_name}'.")
        else:
            print("No content scraped.")
    else:
        print("No URLs found to scrape.")

if __name__ == '__main__':
    main()
