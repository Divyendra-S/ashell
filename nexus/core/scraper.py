import logging

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify

log = logging.getLogger("nexus.scraper")

MIN_CONTENT_LENGTH = 200


def scrape_url(url: str) -> dict:
    resp = httpx.get(url, timeout=15, follow_redirects=True,
                     headers={"User-Agent": "Nexus/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    title = (soup.title.string if soup.title else
             soup.find("h1").get_text() if soup.find("h1") else "Untitled")

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
