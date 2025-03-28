import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException, ElementClickInterceptedException

# Specify the path to chromedriver.exe
service = Service('C:\\Users\\aquad\\OneDrive\\Desktop\\chromedriver-win32\\chromedriver.exe')

# Initialize the Chrome driver with a new user profile
chrome_options = Options()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-popup-blocking")

driver = webdriver.Chrome(service=service, options=chrome_options)

# Function to read words and definitions from CSV file
def read_words_from_csv(csv_path):
    words_dict = {}
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) == 2:
                word, definition = row
                words_dict[word.strip()] = definition.strip()
    return words_dict

# Function to click elements robustly with retries
def click_element(element, description):
    try:
        driver.execute_script("arguments[0].scrollIntoView();", element)
        if element.is_displayed():  # Ensure the element is still displayed
            element.click()
            print(f"Successfully clicked {description}")
            return True
    except StaleElementReferenceException:
        print(f"Element {description} became stale, retrying...")
        return False  # This triggers a retry in the main loop
    except ElementClickInterceptedException:
        print(f"Click for {description} was intercepted, retrying...")
        time.sleep(0.5)
        return False
    except Exception as e:
        print(f"Error clicking {description}: {e}")
        time.sleep(0.5)
        return False
    return False

# Function to detect and handle audio cues
def get_audio_cues():
    audio_cues = []
    try:
        # Find all audio elements on the page
        audio_elements = driver.find_elements(By.TAG_NAME, 'audio')
        for audio in audio_elements:
            if audio.get_attribute('src'):  # Only consider audio elements with a valid source
                audio_cues.append(audio)
    except Exception as e:
        print(f"Error finding audio cues: {e}")
    return audio_cues

# Function to match audio cues with definitions
def match_audio_to_definition(audio_cues, csv_words_dict, korean_words):
    matched_pairs = []
    for audio_element in audio_cues:
        for word, definition in csv_words_dict.items():
            if definition in korean_words:
                matched_pairs.append((audio_element, definition, 'audio'))
                break  # Once we find a match, stop looking for this audio cue
    return matched_pairs

try:
    # Open the login page
    driver.get("https://www.classcard.net/Login")

    # Wait for the user to manually log in
    print("Please log in manually. Waiting for 10 seconds...")
    time.sleep(10)  # Adjusted wait time to 10 seconds to ensure manual login

    # Handle unexpected alert if present
    try:
        alert = WebDriverWait(driver, 10).until(EC.alert_is_present())
        alert.accept()
        print("Alert accepted")
    except TimeoutException:
        print("No alert found")

    # Wait for the "game start" button to be present
    button_selector = '#wrapper-learn > div.start-opt-body > div > div.container-bottom > div > div.btn-blue.btn-opt-start'
    try:
        game_start_button = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, button_selector)))
        driver.execute_script("arguments[0].scrollIntoView();", game_start_button)
        driver.execute_script("arguments[0].click();", game_start_button)
        print("Clicked game start button")
    except NoSuchElementException:
        print("Game start button not found")

    # Wait for the pop-up to appear and the text boxes to be clickable
    popup_selector = '#match-wrapper > div.match-content.cc-row'
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, popup_selector)))

    # Wait for the game to load
    print("Waiting for the game to load...")
    time.sleep(5)  # Increased wait time to 5 seconds to ensure the game is fully loaded

    # Read words and definitions from the CSV file
    csv_path = 'C:\\Users\\aquad\\OneDrive\\Desktop\\words.csv'
    csv_words_dict = read_words_from_csv(csv_path)

    # Print the words and definitions read from the CSV file
    print("Words and definitions from CSV:", csv_words_dict)

    game_end_time = time.time() + 300  # Run for 5 minutes
    successful_matches = 0

    while time.time() < game_end_time:
        matched_any = False
        while True:
            # Extract English words and audio cues
            english_words = []
            english_elements = []
            audio_cues = get_audio_cues()  # Detect audio cues at the start of each loop

            for i in range(4):
                try:
                    word_selector = f'#left_card_{i} .cc-table.middle.fill-parent.match-text.text-center > div'
                    word_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, word_selector)))
                    word_text = word_element.text.strip()

                    if word_text == '':
                        audio_cues.append(word_element)
                    else:
                        english_words.append(word_text)
                        english_elements.append(word_element)

                except Exception as e:
                    print(f"Error extracting English word at index {i}: {e}")
                    english_words.append('')
                    english_elements.append(None)

            # Extract Korean words
            korean_words = []
            korean_elements = []
            for i in range(4):
                try:
                    word_selector = f'#right_card_{i} .cc-table.middle.fill-parent.match-text.text-center > div'
                    word_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, word_selector)))
                    korean_words.append(word_element.text.strip())
                    korean_elements.append(word_element)
                except Exception as e:
                    print(f"Error extracting Korean word at index {i}: {e}")
                    korean_words.append('')
                    korean_elements.append(None)

            # Match audio cues to word definitions
            matched_audio_pairs = match_audio_to_definition(audio_cues, csv_words_dict, korean_words)

            # Handle matched audio cues
            for audio_element, definition, word_type in matched_audio_pairs:
                if click_element(audio_element, f"audio cue for definition '{definition}'"):
                    time.sleep(0.2)

            # Match other words (text matching)
            matched_pairs = [(english_elements[idx], csv_words_dict.get(word, ''), 'english') for idx, word in enumerate(english_words) if word in csv_words_dict and csv_words_dict[word] in korean_words]

            # Click on text and definition elements as usual
            for word_element, definition, word_type in matched_pairs:
                try:
                    if word_element and word_element.is_displayed():  # Ensure word_element is not None and is displayed
                        if click_element(word_element, f"word '{word_element.text}'"):
                            time.sleep(0.2)

                    # Use the XPath to find and click the matching definition
                    definition_xpath = f"//div[text()='{definition}']"  # XPath to match the definition text
                    if click_element(definition_xpath, f"definition '{definition}'"):
                        time.sleep(0.2)
                        successful_matches += 1
                        matched_any = True

                        # Add a delay after matching a set
                        time.sleep(0.2)

                except Exception as e:
                    print(f"Error clicking elements for word '{word_element}' and definition '{definition}': {e}")

            # Handle wrong message popup
            try:
                WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.wrong-popup')))
                print("Wrong message popup detected, waiting for it to disappear...")
                WebDriverWait(driver, 1).until_not(EC.presence_of_element_located((By.CSS_SELECTOR, '.wrong-popup')))
                print("Wrong message popup disappeared.")
            except TimeoutException:
                pass  # No "wrong" message popup found

            if not matched_any:
                break

finally:
    # Do not quit the browser to allow manual quitting
    print("Matching game completed. Please quit the browser manually.")
