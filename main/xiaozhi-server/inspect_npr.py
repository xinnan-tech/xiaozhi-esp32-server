import requests
from bs4 import BeautifulSoup

base_url = "https://text.npr.org"
target_title = "In one south Minneapolis neighborhood, tragedy repeats but connection endures"

try:
    # 1. Fetch Home to find link
    print(f"Fetching home: {base_url}")
    resp = requests.get(base_url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    links = soup.find_all("a", class_="topic-title")
    target_url = None
    for link in links:
        if target_title.lower() in link.get_text().strip().lower():
            href = link.get('href')
            if not href.startswith("http"):
                target_url = base_url + href
            else:
                target_url = href
            print(f"Found URL: {target_url}")
            break
            
    if not target_url:
        print("Could not find article on home page. Trying to fetch a known recent ID if possible, or just fail.")
        # Fallback: User might have meant an article that was there.
        # If I can't find it, I will inspect a general article with transcript.
        # But let's assume it's there since the user just mentioned it.
    
    if target_url:
        # 2. Fetch Article
        print(f"Fetching article: {target_url}")
        art_resp = requests.get(target_url)
        art_soup = BeautifulSoup(art_resp.text, 'html.parser')
        
        # 3. Print structure around "Transcript"
        # We look for any tag containing "Transcript"
        print("\n--- Searching for 'Transcript' in tags ---")
        for tag in art_soup.find_all(string=lambda t: "Transcript" in str(t)):
            parent = tag.parent
            print(f"Tag: {parent.name}, Text: '{parent.get_text()}'")
            print(f"Parent Class: {parent.get('class')}")
            # print surrounding HTML
            print(f"HTML: {parent}")
            print("-" * 20)
            
except Exception as e:
    print(e)
