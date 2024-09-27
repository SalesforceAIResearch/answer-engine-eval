from bs4 import BeautifulSoup
import markdown2

def markdown_to_text(markdown_text):
    html = markdown2.markdown(markdown_text)
    return BeautifulSoup(html, "html.parser").get_text()