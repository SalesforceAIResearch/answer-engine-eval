from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time, re

def content_cleanup_youcom(driver):
    content_HTML = driver.find_element(By.XPATH, '//*[@data-testid="youchat-answer-turn-0"]').get_attribute('innerHTML')
    content_HTML = re.sub(r'style="[^"]*"', "", content_HTML)
    content_HTML = re.sub(r'class="[^"]*"', "", content_HTML)
    content_HTML = re.sub(r'data-testid="[^"]*"', "", content_HTML)
    content_HTML = re.sub(r'aria-label="[^"]*"', "", content_HTML)
    content_HTML = re.sub(r'data-eventactionname="[^"]*"', "", content_HTML)
    # data-eventactiontitle=
    content_HTML = re.sub(r'data-eventactiontitle="[^"]*"', "", content_HTML)
    return content_HTML

def get_shadow_root(driver, element):
    return driver.execute_script('return arguments[0].shadowRoot', element)


class AnswerEngineScraper:
    def __init__(self, run_headless=False):
        # Note: headless running is not super well-tested now... but seems to work more or less.
        self.driver = uc.Chrome(headless=run_headless)
    
    def scrape_you_com(self, search_query):
        # which the search input is not found
        search_input = None

        while True:
            print("Looking once more!")
            self.driver.get("https://you.com")
            time.sleep(3)

            # Find the search input field
            try:
                search_input = self.driver.find_element(By.ID, "search-input-textarea")
            except:
                pass
            if search_input:
                break

        # Type the query into the search bar
        search_input.send_keys(search_query)

        # Press Enter to submit the search
        search_input.send_keys(Keys.RETURN)

        # wait until the dom settles
        old_html = self.driver.page_source
        while True:
            time.sleep(3)
            print("Waiting for DOM to settle...")
            new_html = self.driver.page_source
            if old_html == new_html:
                break
            old_html = new_html

        print("DOM settled")

        content_HTML = content_cleanup_youcom(self.driver)

        soup = BeautifulSoup(content_HTML, 'html.parser')
        # go over each of the span, if it is allnum, then add brackets since it is a citation
        for span in soup.find_all('span'):
            if span.text.isnumeric():
                span.string = f"[{span.text}]"

        answer_text = soup.get_text()

        # Method 1 for sources, only retrieves cited sources
        # id2source = {}
        # for link in driver.find_elements(By.TAG_NAME, 'a'):
        #     if link.text.isnumeric():
        #         id2source[link.text] = link.get_attribute('href')
        # sources = [{"source_id": k, "source_url": v} for k, v in id2source.items()]

        # Method 2 for sources: open the source panel, and get the content within it

        # first scroll to the bottom
        self.driver.execute_script("arguments[0].scrollIntoView(false);", self.driver.find_element(By.XPATH, '//*[@data-testid="YouChat-app"]'))
        time.sleep(1.0)
        sources = []
        try:
            button = self.driver.find_element(By.XPATH, '//*[@data-testid="youchat-citation-pills-toggle"]')
            button.click()
        except:
            pass

        sources = []
        for link in self.driver.find_elements(By.TAG_NAME, 'a'):
            if "\n" in link.text.strip() and link.text.strip().split("\n")[0].isnumeric():
                sources.append({"source_url": link.get_attribute('href'), "source_id": int(link.text.strip().split("\n")[0]), "source": link.text.strip().split("\n")[1]})
        return answer_text, sources
    
    def scrape_perplexity(self, search_query):
        self.driver.get("https://www.perplexity.ai/")

        search_input = None
        while True:
            print("Looking once more!")
            self.driver.get("https://www.perplexity.ai/")
            time.sleep(3)

            # Find the search input field
            try:
                search_input = self.driver.find_element(By.TAG_NAME, "textarea")
            except:
                pass
            if search_input:
                break

        # Type the query into the search bar
        search_input.send_keys(search_query)

        # Press Enter to submit the search
        search_input.send_keys(Keys.RETURN)

        # wait until the dom settles
        old_html = self.driver.page_source
        while True:
            time.sleep(3)
            print("Waiting for DOM to settle...")
            new_html = self.driver.page_source
            if old_html == new_html:
                break
            old_html = new_html

        HTML = self.driver.page_source
        soup = BeautifulSoup(HTML, "html.parser")

        for svg in soup.find_all("svg"):
            svg.decompose()

        # find all elements that have a data-number attribute
        elements = soup.find_all(attrs={"data-number": True})
        for elem in elements:
            # set the inner text within it that has [number] in it
            elem.string = f"[{elem['data-number']}]"

        answer_text = ""
        elements = soup.find_all(class_="border-borderMain/50")
        for elem in elements:
            text = elem.get_text()
            if text.startswith("Answer") and len(text) > 10:
                answer_text = text[6:]
                # print(answer)

        links = soup.find_all("a")
        id2source = {}
        for link in links:
            # see if http is in the href and has data-number attribute
            # find the span child that has the data-number attribute
            span_child = link.find("span", attrs={"data-number": True})
            if "http" in link["href"] and span_child:
                if span_child["data-number"] not in id2source:
                    id2source[span_child["data-number"]] = link["href"]

        sources = [{"source_id": k, "source_url": v} for k, v in id2source.items()]
        return answer_text, sources
    
    def scrape_bing_chat(self, search_query):
        while True:
            print("Looking once more!")
            self.driver.get("https://www.bing.com/chat")
            time.sleep(3)

            # Find the search input field
            try:
                cib_serp = self.driver.execute_script('return document.querySelector("cib-serp")')
                cib_serp_shadow = get_shadow_root(self.driver, cib_serp)

                cib_action_bar = cib_serp_shadow.find_element(By.CSS_SELECTOR, "cib-action-bar")
                cib_action_bar_shadow = get_shadow_root(self.driver, cib_action_bar)

                # Get the cib-text-input element and its shadow root
                cib_text_input = cib_action_bar_shadow.find_element(By.CSS_SELECTOR, "cib-text-input")
                cib_text_input_shadow = get_shadow_root(self.driver, cib_text_input)

                # Finally, get the textarea element
                search_input = cib_text_input_shadow.find_element(By.CSS_SELECTOR, "textarea")
            except:
                pass
            if search_input:
                break

        # Type the query into the search bar
        search_input.send_keys(search_query)

        # Press Enter to submit the search
        search_input.send_keys(Keys.RETURN)

        # wait until the dom settles
        old_html = self.driver.page_source
        while True:
            time.sleep(3)
            print("Waiting for DOM to settle...")
            new_html = self.driver.page_source
            if old_html == new_html:
                break
            old_html = new_html

        time.sleep(5.0)
        print("DOM settled")

        cib_serp = self.driver.execute_script('return document.querySelector("cib-serp")')
        cib_serp_shadow = get_shadow_root(self.driver, cib_serp)

        cib_conversation = cib_serp_shadow.find_element(By.CSS_SELECTOR, "cib-conversation")
        cib_conversation_shadow = get_shadow_root(self.driver, cib_conversation)

        cib_chat_turn = cib_conversation_shadow.find_element(By.CSS_SELECTOR, "cib-chat-turn")
        cib_chat_turn_shadow = get_shadow_root(self.driver, cib_chat_turn)

        cib_message_groups = cib_chat_turn_shadow.find_elements(By.CSS_SELECTOR, "cib-message-group")

        last_message = cib_message_groups[-1]
        last_message_shadow = get_shadow_root(self.driver, last_message)
        # within there get cib-message

        cib_message = last_message_shadow.find_element(By.CSS_SELECTOR, "cib-message")
        cib_message_shadow = get_shadow_root(self.driver, cib_message)

        # now get cib-shared
        cib_shared = cib_message_shadow.find_element(By.CSS_SELECTOR, "cib-shared")

        soup = BeautifulSoup(cib_shared.get_attribute("innerHTML"), "html.parser")
        soup = soup.select_one(".content")
        answer_text = soup.get("aria-label")

        # replace [^1^] by [1]
        answer_text = re.sub(r"\[\^(\d+)\^\]", r"[\1]", answer_text)

        # next get the innerHTML of cib-message-attributions

        cib_message_attributions = cib_message_shadow.find_element(By.CSS_SELECTOR, "cib-message-attributions")
        cib_message_attributions_shadow = get_shadow_root(self.driver, cib_message_attributions)

        # within there, find all the cib-attribution-item
        cib_attribution_items = cib_message_attributions_shadow.find_elements(By.CSS_SELECTOR, "cib-attribution-item")
        sources = []
        for cib_attribution_item in cib_attribution_items:
            cib_attribution_item_shadow = get_shadow_root(self.driver, cib_attribution_item)
            links = cib_attribution_item_shadow.find_elements(By.CSS_SELECTOR, "a")
            for link in links:
                # print(link.get_attribute("href"), link.text)
                sources.append({"source_url": link.get_attribute('href'), "source_id": int(link.text.strip().split("\n")[0]), "source": link.text.strip().split("\n")[1]})
        return answer_text, sources

    def scrape(self, search_query, engine="you"):
        assert engine in ["you", "perplexity", "bing_chat"]
        if engine == "you":
            return self.scrape_you_com(search_query)
        elif engine == "perplexity":
            return self.scrape_perplexity(search_query)
        elif engine == "bing_chat":
            return self.scrape_bing_chat(search_query)

if __name__ == "__main__":
    scraper = AnswerEngineScraper(run_headless=False)
    for engine in ["you", "perplexity", "bing_chat"]:
        answer_text, sources = scraper.scrape("What is the best way to cook an egg?", engine)
        print("======================================================")
        print("======================================================")
        print("======================================================")
        print("======================================================")
        print(f"Answer from {engine}:")
        print(answer_text)
        print("Sources:")
        print(sources)
