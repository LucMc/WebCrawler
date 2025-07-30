import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import os
import re

def scrape(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    paragraphs = soup.find_all('p')
    paragraph_texts = [p.get_text(strip=True) for p in paragraphs]

    headings = []
    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        headings.extend([h.get_text(strip=True) for h in soup.find_all(tag)])

    links = []
    for a in soup.find_all('a', href=True):
        links.append({
            'text': a.get_text(strip=True),
            'href': a['href']
        })

    # print("URL:\n", url)
    # print("heading:\n", headings)
    # print("paragraph texts:\n", paragraph_texts)

    return headings, paragraph_texts, links


def filter_link(base_url, link):
    link_url = link["href"]
    banned_starts =["/cookies", "../", "#", "?", "mailto", "tel"]
    if len(link_url)<2: return False, link_url

    for start in banned_starts:
        if link_url.startswith(start):
            return False, link_url

    if link_url.startswith("http"): 
        # print("ABS LINK:",link_url) #urljoin(base_url, link_url))
        return True, link_url

    elif link_url.startswith("/"): 
        formatted_url = urljoin(base_url, link_url)
        # print("RELATIVE LINK:", formatted_url)
        # print("base_url:\n", base_url)
        # print("link_url:\n", link_url)
        return True, formatted_url # DONT ALLOW FOR NOW BUT ADD IN FUTURE

    else:
        print("UNKNOWN TYPE", link_url)
        breakpoint()

def save_page_content(url, headings, paragraphs, output_dir="scraped_pages"):
    os.makedirs(output_dir, exist_ok=True)
    
    filename = re.sub(r'[^\w\-_.]', '_', url.replace('https://', '').replace('http://', ''))
    filename = filename[:100] + '.txt'
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"URL: {url}\n")
        f.write("=" * 50 + "\n\n")
        
        if headings:
            f.write("HEADINGS:\n")
            f.write("-" * 20 + "\n")
            for heading in headings:
                f.write(f"• {heading}\n")
            f.write("\n")
        
        if paragraphs:
            f.write("PARAGRAPHS:\n")
            f.write("-" * 20 + "\n")
            for para in paragraphs:
                if para.strip():
                    f.write(f"{para}\n\n")

def crawl(url: str | None = None,
          visited_urls: list = None,
          total_headings: list = None,
          total_paragraphs: list = None,
          depth: int = 0,
          max_depth: int = 2,
          max_links_per_page: int = 15
          ):

    if visited_urls is None:
        visited_urls = []
    if total_headings is None:
        total_headings = []
    if total_paragraphs is None:
        total_paragraphs = []
    
    # Get page info
    headings, paragraph_texts, links = scrape(url)
    
    # Save page content to file
    save_page_content(url, headings, paragraph_texts)

    if len(headings) == 0 or len(paragraph_texts)== 0:
        print(f"WARNING: {url} has {len(headings)} and {len(paragraph_texts)} parapgraphs.")

    if (url in visited_urls) or (depth >= max_depth):
        # return [], [], [] # Stops the tree essentially
        links = []
    
    # Update knowledge
    total_headings.append(headings)
    total_paragraphs.append(paragraph_texts)
    visited_urls.append(url)
    
    v_urls = [];headings = [];paragraphs = []

    for link in links[:max_links_per_page]: 
        valid, formatted_link = filter_link(url, link)

        if valid and not (formatted_link in visited_urls):
            print(f"Scraping website {len(visited_urls)}:", formatted_link)
            visited_urls, total_headings, total_paragraphs = crawl(formatted_link,
                                               visited_urls,
                                               total_headings,
                                               total_paragraphs,
                                               depth=depth+1)

            # print(f"headings: {len(total_headings)}, paragraphs: {len(total_paragraphs)} v_urls: {len(visited_urls)}")

    return visited_urls, total_headings, total_paragraphs


# In case of page not found
def post_processing(visited_urls, total_headings, total_paragraphs):

    # original_urls = visited_urls
    idx = 0
    remove_idxs = []

    for url, headings, paragraphs in zip(visited_urls, total_headings, total_paragraphs):
        for heading in headings:
            if "404" in headings:
                print("removing error 404 URL:", url)
                remove_idxs.append(idx)
                
        idx += 1
    print("Number of URL's to remove:", len(remove_idxs))
    filtered_urls = [x for i, x in enumerate(visited_urls) if i not in remove_idxs]
    print("Final number of URLS:", len(filtered_urls))
    return filtered_urls
                
# TODO: Some URL's have no headings or paragraphs!
def main():
    URL = "https://www.surrey.ac.uk/open-days"
    MAX_DEPTH = 2
    MAX_LINKS_PER_PAGE=None # None or int

    # scrape(URL) # For single page scrapring

    visited_urls, total_headings, total_paragraphs = crawl(URL, max_depth=MAX_DEPTH, max_links_per_page=MAX_LINKS_PER_PAGE)
    print("visited_urls:\n", visited_urls)

    import random
    if visited_urls:
        idx = random.randint(0, len(visited_urls) - 1)
        print("\n\nRandom idx:\n", idx)
        print("Random visited URL:\n", visited_urls[idx])
        print("headings:\n", total_headings[idx])
        print("paragraphs:\n", total_paragraphs[idx])
    
    print("Total websites", len(visited_urls))
    print("Unique websites", len(set(visited_urls)))

    filtered_urls = post_processing(visited_urls, total_headings, total_paragraphs)
    print("working websites", len(set(filtered_urls)))

if __name__ == "__main__":
    # hs, ps, ls = scrape("https://www.surrey.ac.uk/undergraduate/computer-science")
    # print("ls:\n", ls)
    # print("ps:\n", ps)
    # print("hs:\n", hs)
    
    main()
