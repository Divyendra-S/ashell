import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify


def scrape_url(url: str) -> dict:
    """Fetch URL → clean HTML → markdown. Returns {title, content, url}."""
    resp = httpx.get(url, timeout=15, follow_redirects=True,
                     headers={"User-Agent": "Kuro/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Extract title
    title = (soup.title.string if soup.title else
             soup.find("h1").get_text() if soup.find("h1") else "Untitled")

    # Get main content
    main = soup.find("article") or soup.find("main") or soup.find("body")
    content = markdownify(str(main), heading_style="ATX", strip=["img"])

    return {"title": title.strip(), "content": content.strip(), "url": url}
