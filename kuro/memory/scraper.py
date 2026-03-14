import logging

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify

log = logging.getLogger("kuro.scraper")

MIN_CONTENT_LENGTH = 200  # chars — below this, the page is likely JS-rendered


def scrape_url(url: str) -> dict:
    """Fetch URL → clean HTML → markdown. Returns {title, content, url}.

    Raises ValueError if the page appears to be client-side rendered
    (content too short after extraction).
    """
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
    content = content.strip()

    if len(content) < MIN_CONTENT_LENGTH:
        raise ValueError(
            f"Page content too short ({len(content)} chars). "
            f"This site likely requires JavaScript to render. "
            f"Try pasting the article text directly instead of using the URL."
        )

    return {"title": title.strip(), "content": content, "url": url}
