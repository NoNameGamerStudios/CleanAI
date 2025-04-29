import os
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time
import random

# Set up logging
log_folder = "scraped_data"
os.makedirs(log_folder, exist_ok=True)  # Create subfolder if it doesn't exist
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

# Function to fetch URLs from DuckDuckGo with pagination
def fetch_urls_from_duckduckgo(query, num_results=50, max_pages=5):
    all_urls = []
    
    for page in range(0, max_pages):
        # DuckDuckGo search URL with pagination (start parameter controls the page number)
        start = page * 10  # Increment the page results by 10 per page
        search_url = f'https://duckduckgo.com/html/?q={query}&s={start}'  # Pagination implemented with 's'
        
        # Randomly select a User-Agent from the list
        headers = {'User-Agent': random.choice(user_agents)}
        
        try:
            # Send GET request to DuckDuckGo search page
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()  # Check for request errors

            # Parse the response HTML content
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all links in the search result page
            result_links = soup.find_all('a', {'class': 'result__a'})  # DuckDuckGo result links

            # Extract URLs
            urls = [link['href'] for link in result_links]
            all_urls.extend(urls)  # Add new URLs to the list

            logging.info(f"Found {len(urls)} URLs for page {page + 1} of query '{query}'.")
            
            # Check if we've reached the desired number of results
            if len(all_urls) >= num_results:
                break

            # Add delay to avoid rate-limiting (DuckDuckGo might flag if too many requests are made in short time)
            time.sleep(2)  # Wait for 2 seconds before making the next request

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching results for page {page + 1} of query '{query}': {e}")
            time.sleep(5)  # Wait before trying again if an error occurs
            continue
    
    logging.info(f"Total {len(all_urls)} URLs fetched for query '{query}'.")
    return all_urls[:num_results]  # Return only the desired number of results

# Function to scrape content from a single URL
def scrape_content(url):
    try:
        logging.info(f"Starting to scrape: {url}")
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        # Extract the title and text content (adjust to your needs)
        title = soup.title.string if soup.title else 'No title'
        body_text = soup.get_text()

        # Create a subfolder for storing the content
        folder_name = os.path.join(log_folder, "scraped_content")
        os.makedirs(folder_name, exist_ok=True)

        # Save the scraped content to a file (you can adjust the format as needed)
        filename = os.path.join(folder_name, f"scraped_content_{url.replace('https://', '').replace('http://', '').replace('/', '_')}.txt")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Title: {title}\n")
            f.write(f"URL: {url}\n")
            f.write(body_text)

        logging.info(f"Successfully scraped: {url}")
        return title, body_text

    except requests.exceptions.RequestException as e:
        logging.error(f"Error scraping {url}: {e}")
        return None, None

# Function to scrape content from a list of URLs using multiple threads
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
    user_input = input 
    search_query =  user_input("Enter your search query: ")  # Get search query from user input
    search_query = search_query.replace(" ", "+")  # Replace spaces with '+' for URL encoding
    num_results = 50  # Desired number of results


    # Step 1: Fetch URLs from DuckDuckGo with pagination (more results)
    print(f"Fetching URLs for search query: {search_query}")
    urls = fetch_urls_from_duckduckgo(search_query, num_results=num_results, max_pages=5)
    
    if urls:
        print(f"Found {len(urls)} URLs. Starting to scrape...")

        # Step 2: Scrape content from the fetched URLs
        scraped_data = scrape_urls(urls)

        # Optional: Save scraped data in a structured format (e.g., JSON, CSV, etc.)
        # Here we're just saving the data in a simple log file
        if scraped_data:
            # Save the scraped data in the 'scraped_data' subfolder
            with open(os.path.join(log_folder, "scraped_data.txt"), "w", encoding="utf-8") as f:
                for title, content in scraped_data:
                    f.write(f"Title: {title}\n")
                    f.write(f"Content: {content}\n\n")
            print(f"Scraped content saved to '{log_folder}/scraped_data.txt'.")
        else:
            print("No content scraped.")
    else:
        print("No URLs found to scrape.")

if __name__ == '__main__':
    main()
