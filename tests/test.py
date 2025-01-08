from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import requests
import os
from googletrans import Translator
import logging
import re
from collections import Counter


logging.basicConfig(level=logging.INFO)
logging.info("Visiting site..")

options = webdriver.ChromeOptions()



driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.maximize_window()


url = "https://elpais.com"
driver.get(url)

lang_attribute = driver.find_element(By.XPATH, "/html").get_attribute("lang")
if lang_attribute == "es":
    logging.info("The website is displayed in Spanish.")
else:
    logging.warning(f"The website language is not Spanish. Detected: {lang_attribute}")


def handle_popups():
    try:
        accept_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'didomi-notice-agree-button'))
        )
        accept_button.click()
        logging.info("Cookie consent accepted.")
    except Exception as e:
        logging.info("No cookie consent pop-up or already handled.")
   
    
    try:
        subscription_popup = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'ev-open-modal'))
        )
        driver.execute_script("arguments[0].style.display = 'none';", subscription_popup)
        logging.info("Subscription popup hidden.")
    except Exception:
        logging.info("No subscription popup found.")

handle_popups()


def remove_obstructions():
    try:
        blocking_iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in blocking_iframes:
            driver.execute_script("arguments[0].style.visibility = 'hidden';", iframe)
        logging.info("Removed blocking iframes.")
    except Exception as e:
        logging.info("No blocking iframes found.")




def navigate_to_opinion():
    for attempt in range(5):  
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '/html/body/header/header/div[2]/div[1]/nav/div/a[2]'))
            )
            opinion_section = driver.find_element(By.XPATH, '/html/body/header/header/div[2]/div[1]/nav/div/a[2]')
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", opinion_section)
            driver.execute_script("arguments[0].click();", opinion_section)
            logging.info("Navigated to Opinion section.")
            return
        except StaleElementReferenceException:
            logging.warning("Stale element reference error. Retrying...")
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1}: Failed to navigate to Opinion section: {e}")
            remove_obstructions()
            handle_popups()
    logging.error("Failed to navigate to Opinion section after retries.")
    driver.quit()
    exit()


navigate_to_opinion()


translator = Translator()


image_dir = "article_images"
os.makedirs(image_dir, exist_ok=True)


def fetch_article_data():
    articles_data = []
    for index in range(5):  
        try:
   
            articles = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article"))
            )

  
            article = articles[index]
            title_element = article.find_element(By.CSS_SELECTOR, "h2")
            title = title_element.text
            link = title_element.find_element(By.TAG_NAME, "a").get_attribute("href")

            driver.get(link)


            paragraphs = driver.find_elements(By.CSS_SELECTOR, "p")
            content = " ".join([p.text for p in paragraphs])


            try:
                image_element = driver.find_element(By.CSS_SELECTOR, "figure img")
                image_url = image_element.get_attribute("src")
                image_path = os.path.join(image_dir, f"article_{index + 1}.jpg")
                with open(image_path, "wb") as f:
                    f.write(requests.get(image_url, timeout=5).content)
            except Exception:
                logging.info(f"No image found for article {index + 1}.")


            translated_title = translator.translate(title, src="es", dest="en").text


            articles_data.append({
                "title": title,
                "content": content,
                "translated_title": translated_title
            })

            driver.get(url)
            if len(articles_data)<5:
                navigate_to_opinion()

        except Exception as e:
            logging.error(f"Error processing article {index + 1}: {e}")

    return articles_data

articles_data = fetch_article_data()


driver.quit()


logging.info("\n--- Articles in Spanish ---\n")
for article in articles_data:
    print(f"Title: {article['title']}")
    print(f"Content: {article['content'][:500]}...")

logging.info("\n--- Translated Titles ---\n")
translated_titles = [article["translated_title"] for article in articles_data]
for title in translated_titles:
    print(title)


all_words = " ".join(translated_titles)
all_words = re.sub(r"[()\[\]{}<>.,!?;:\"'`]|\s+", " ", all_words) 
word_list = all_words.split()
word_counts = Counter([word.lower() for word in word_list if len(word) >= 2])
repeated_words = {word: count for word, count in word_counts.items() if count >= 2}



logging.info("\n--- Repeated Words in Translated Titles ---\n")
for word, count in repeated_words.items():
    print(f"{word}: {count}")
