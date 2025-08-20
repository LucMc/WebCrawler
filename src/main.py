import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import os
import re
from datetime import datetime


def scrape(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    # Get page title
    title = soup.find("title")
    page_title = title.get_text(strip=True) if title else "Unknown Title"

    paragraphs = soup.find_all("p")
    paragraph_texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]

    headings = []
    for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        headings.extend([h.get_text(strip=True) for h in soup.find_all(tag) if h.get_text(strip=True)])

    links = []
    for a in soup.find_all("a", href=True):
        link_text = a.get_text(strip=True)
        if link_text:  # Only include links with text
            links.append({"text": link_text, "href": a["href"]})

    return page_title, headings, paragraph_texts, links


def extract_metadata(url, page_title, headings, paragraphs):
    """Extract metadata from the scraped content"""

    # Determine page type based on url and content
    page_type = "general"
    url_lower = url.lower()
    title_lower = page_title.lower()

    if any(keyword in url_lower or keyword in title_lower for keyword in ["undergraduate", "bachelor", "bsc", "ba"]):
        page_type = "undergraduate"
    elif any(
        keyword in url_lower or keyword in title_lower for keyword in ["postgraduate", "masters", "phd", "msc", "ma"]
    ):
        page_type = "postgraduate"
    elif any(keyword in url_lower or keyword in title_lower for keyword in ["admissions", "apply", "application"]):
        page_type = "admissions"
    elif any(keyword in url_lower or keyword in title_lower for keyword in ["department", "school", "faculty"]):
        page_type = "department"
    elif any(keyword in url_lower or keyword in title_lower for keyword in ["open-day", "open day", "visit"]):
        page_type = "events"
    elif any(keyword in url_lower or keyword in title_lower for keyword in ["research", "phd"]):
        page_type = "research"

    # Extract keywords from content
    keywords = []
    all_text = " ".join([page_title] + headings + paragraphs[:3]).lower()  # First 3 paragraphs

    # Common university-related keywords to look for
    keyword_candidates = [
        "computer science",
        "engineering",
        "medicine",
        "law",
        "business",
        "psychology",
        "biology",
        "chemistry",
        "physics",
        "mathematics",
        "english",
        "history",
        "geography",
        "economics",
        "politics",
        "undergraduate",
        "postgraduate",
        "masters",
        "phd",
        "bachelor",
        "course",
        "degree",
        "program",
        "module",
        "study",
        "research",
        "campus",
        "accommodation",
        "fees",
        "scholarships",
        "international",
    ]

    for keyword in keyword_candidates:
        if keyword in all_text:
            keywords.append(keyword)

    # Remove duplicates and limit to top 10
    keywords = list(set(keywords))[:10]

    # Determine section title (use first heading or page title)
    section_title = headings[0] if headings else page_title

    # Clean section title
    section_title = re.sub(r"\s+", " ", section_title).strip()
    if len(section_title) > 100:
        section_title = section_title[:97] + "..."

    return {
        "section_title": section_title,
        "page_url": url,
        "page_type": page_type,
        "keywords": keywords,
        "headings": headings[:10],  # Limit to first 10 headings
        "last_scraped": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def filter_link(base_url, link):
    link_url = link["href"]
    banned_starts = ["/cookies", "../", "#", "?", "mailto", "tel", "javascript"]
    banned_extensions = [".pdf", ".doc", ".docx", ".jpg", ".png", ".gif"]

    if len(link_url) < 2:
        return False, link_url

    for start in banned_starts:
        if link_url.startswith(start):
            return False, link_url

    for ext in banned_extensions:
        if link_url.lower().endswith(ext):
            return False, link_url

    if link_url.startswith("http"):
        return True, link_url
    elif link_url.startswith("/"):
        formatted_url = urljoin(base_url, link_url)
        return True, formatted_url
    else:
        return False, link_url


def save_page_content(url, page_title, headings, paragraphs, output_dir="scraped_university_pages"):
    """Save content in structured format similar to reference file"""
    os.makedirs(output_dir, exist_ok=True)

    # Extract metadata
    metadata = extract_metadata(url, page_title, headings, paragraphs)

    # Create filename
    filename = re.sub(r"[^\w\-_.]", "_", url.replace("https://", "").replace("http://", ""))
    filename = filename[:100] + ".txt"
    filepath = os.path.join(output_dir, filename)
    excluded_terms = ["cookies", "|"]
    filtered_paragraphs = [
        item for item in paragraphs if not any(term in item for term in excluded_terms) and len(item) >= 20
    ]

    print("filtered_paragraphs:\n", len(filtered_paragraphs))
    chars = len("".join(filtered_paragraphs))
    print("chars:\n", chars)

    if chars > 350: # Min 350 chars
        with open(filepath, "w", encoding="utf-8") as f:
            # Write metadata section
            f.write("--- METADATA ---\n")
            f.write(f"section_title: {metadata['section_title']}\n")
            f.write(f"page_url: {metadata['page_url']}\n")
            f.write(f"page_type: {metadata['page_type']}\n")
            f.write(f"keywords: {metadata['keywords']}\n")
            f.write(f"headings: {metadata['headings']}\n")
            f.write(f"last_scraped: {metadata['last_scraped']}\n")

            # Write text section
            f.write("--- TEXT ---\n")
            # f.write(f"Page Title: {page_title}\n\n")

            # if headings:
            #     f.write("Main Headings:\n")
            #     for i, heading in enumerate(headings[:10], 1):
            #         f.write(f"{i}. {heading}\n")
            #     f.write("\n")

            for para in filtered_paragraphs:
                # if para.strip() and len(para.strip()) > 20:  # Filter out very short paragraphs
                f.write(f"{para}\n\n")


def crawl(
    url: str | None = None,
    visited_urls: list = None,
    all_content: list = None,
    depth: int = 0,
    max_depth: int = 2,
    max_links_per_page: int = 15,
):
    if visited_urls is None:
        visited_urls = []
    if all_content is None:
        all_content = []

    if url in visited_urls or depth >= max_depth:
        return visited_urls, all_content

    try:
        # Get page info
        page_title, headings, paragraph_texts, links = scrape(url)

        # Save page content to file
        save_page_content(url, page_title, headings, paragraph_texts)

        # Store content
        all_content.append({"url": url, "title": page_title, "headings": headings, "paragraphs": paragraph_texts})

        visited_urls.append(url)

        print(f"Scraped ({depth + 1}/{max_depth}): {url}")
        print(f"  Title: {page_title[:80]}...")
        print(f"  Headings: {len(headings)}, Paragraphs: {len(paragraph_texts)}")

        if len(headings) == 0 and len(paragraph_texts) == 0:
            print(f"  WARNING: No content found")

        # Continue crawling links
        valid_links = 0
        for link in links:
            if valid_links >= (max_links_per_page or float("inf")):
                break

            valid, formatted_link = filter_link(url, link)

            if valid and formatted_link not in visited_urls:
                # Only follow university-related links
                if any(domain in formatted_link for domain in ["surrey.ac.uk", "ac.uk"]) or url in formatted_link:
                    visited_urls, all_content = crawl(
                        formatted_link,
                        visited_urls,
                        all_content,
                        depth=depth + 1,
                        max_depth=max_depth,
                        max_links_per_page=max_links_per_page,
                    )
                    valid_links += 1

    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")

    return visited_urls, all_content


def post_processing(all_content):
    """Filter out pages with no useful content"""

    filtered_content = []
    for content in all_content:
        # Check if page has substantial content
        has_headings = len(content["headings"]) > 0
        has_paragraphs = len([p for p in content["paragraphs"] if len(p.strip()) > 50]) > 0

        # Check for error pages
        is_error = any(
            "404" in str(item).lower() for item in content["headings"] + content["paragraphs"] + [content["title"]]
        )

        if (has_headings or has_paragraphs) and not is_error:
            filtered_content.append(content)
        else:
            print(f"Filtered out: {content['url']} (insufficient content or error page)")

    return filtered_content


def main():
    urls = [
        "https://www.surrey.ac.uk/open-days",
        "https://www.surrey.ac.uk/faculties-and-schools",
        "https://www.surrey.ac.uk/undergraduate",
        "https://www.surrey.ac.uk/study",
        "https://www.surrey.ac.uk/employability-and-careers",
        "https://en.wikipedia.org/wiki/University_of_Surrey",
        "https://www.surrey.ac.uk/accommodation",
        "https://www.surrey.ac.uk/library",
        "https://my.surrey.ac.uk/hive",
    ]

    MAX_DEPTH = 3
    MAX_LINKS_PER_PAGE = 20  # None for all

    for url in urls:
        print(f"Initial url: {url}")
        print(f"Max depth: {MAX_DEPTH}")
        print(f"Max links per page: {MAX_LINKS_PER_PAGE}")
        print("-" * 50)
        visited_urls, all_content = crawl(url, max_depth=MAX_DEPTH, max_links_per_page=MAX_LINKS_PER_PAGE)

        print(f"\nScraping completed!")
        print(f"Total pages visited: {len(visited_urls)}")
        print(f"Unique pages: {len(set(visited_urls))}")

        # Filter content
        filtered_content = post_processing(all_content)
        print(f"Pages with useful content: {len(filtered_content)}")

        # Show sample results
        if filtered_content:
            print(f"\nSample page:")
            sample = filtered_content[0]
            print(f"url: {sample['url']}")
            print(f"Title: {sample['title']}")
            print(f"Headings: {len(sample['headings'])}")
            print(f"Paragraphs: {len(sample['paragraphs'])}")

            if sample["headings"]:
                print(f"First heading: {sample['headings'][0]}")


if __name__ == "__main__":
    main()
