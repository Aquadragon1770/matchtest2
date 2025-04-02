import csv
import asyncio
from playwright.async_api import async_playwright

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

# Function to run the script with Playwright
async def run(playwright):
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    # Open the login page
    await page.goto("https://www.classcard.net/Login")
    
    # Wait for the user to manually log in
    print("Please log in manually. Waiting for 10 seconds...")
    await page.wait_for_timeout(10000)  # Adjusted wait time to 10 seconds to ensure manual login

    # Wait for the "game start" button to be present
    button_selector = '#wrapper-learn > div.start-opt-body > div > div.container-bottom > div > div.btn-blue.btn-opt-start'
    await page.wait_for_selector(button_selector)
    await page.click(button_selector)
    print("Clicked game start button")

    # Wait for the pop-up to appear and the text boxes to be clickable
    popup_selector = '#match-wrapper > div.match-content.cc-row'
    await page.wait_for_selector(popup_selector)
    
    # Wait for the game to load
    print("Waiting for the game to load...")
    await page.wait_for_timeout(5000)  # Increased wait time to 5 seconds to ensure the game is fully loaded

    # Read words and definitions from the CSV file
    csv_path = 'C:\\Users\\aquad\\OneDrive\\Desktop\\words.csv'
    csv_words_dict = read_words_from_csv(csv_path)
    print("Words and definitions from CSV:", csv_words_dict)

    game_end_time = asyncio.get_event_loop().time() + 300  # Run for 5 minutes
    successful_matches = 0

    while asyncio.get_event_loop().time() < game_end_time:
        matched_any = False
        while True:
            # Extract English words and audio cues
            english_words = []
            english_elements = []
            audio_cues = await page.query_selector_all('audio')  # Detect audio cues at the start of each loop

            for i in range(4):
                try:
                    word_selector = f'#left_card_{i} .cc-table.middle.fill-parent.match-text.text-center > div'
                    word_element = await page.query_selector(word_selector)
                    word_text = await word_element.inner_text() if word_element else ''
                    
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
                    word_element = await page.query_selector(word_selector)
                    word_text = await word_element.inner_text() if word_element else ''
                    korean_words.append(word_text)
                    korean_elements.append(word_element)
                except Exception as e:
                    print(f"Error extracting Korean word at index {i}: {e}")
                    korean_words.append('')
                    korean_elements.append(None)

            # Match audio cues to word definitions
            matched_audio_pairs = [(audio_element, csv_words_dict[definition], 'audio') 
                                   for audio_element in audio_cues 
                                   for definition in korean_words 
                                   if definition in csv_words_dict]

            # Handle matched audio cues
            for audio_element, definition, word_type in matched_audio_pairs:
                try:
                    await audio_element.click()
                    print(f"Clicked audio cue for definition '{definition}'")
                    await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"Error clicking audio: {e}")

            # Match other words (text matching)
            matched_pairs = [(english_elements[idx], csv_words_dict.get(word, ''), 'english') 
                             for idx, word in enumerate(english_words) 
                             if word in csv_words_dict and csv_words_dict[word] in korean_words]

            # Click on text and definition elements as usual
            for word_element, definition, word_type in matched_pairs:
                try:
                    if word_element:
                        await word_element.click()
                        print(f"Clicked word '{word_element}'")
                        await asyncio.sleep(0.2)

                    definition_xpath = f"//div[text()='{definition}']"
                    definition_element = await page.query_selector(definition_xpath)
                    await definition_element.click()
                    print(f"Clicked definition '{definition}'")
                    await asyncio.sleep(0.2)
                    successful_matches += 1
                    matched_any = True

                    await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"Error clicking elements for word '{word_element}' and definition '{definition}': {e}")

            if not matched_any:
                break

    await browser.close()

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

# Run the script
asyncio.run(main())