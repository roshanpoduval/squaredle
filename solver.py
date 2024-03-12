import os
import json
import time
import twl
import dawg_python
import numpy as np
import regex as re
from math import sqrt
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
# from selenium.webdriver.support.ui import WebDriverWait
from pyscrabbler import getScrabbleWords
from selenium.common.exceptions import NoSuchElementException
DEBUG = False
SQUAREDLE_USER = os.environ.get('SQUAREDLE_USER')
SQUAREDLE_PASS = os.environ.get('SQUAREDLE_PASS')
NO_TWL = True
CDAWG = dawg_python.CompletionDAWG().load('NSWL2020.completion.dawg')
if NO_TWL: assert CDAWG is not None
default_delay = 0.5

driver = webdriver.Chrome()
driver.get("https://squaredle.app/")
# print(driver.title)

def twl_dawg_children(word, cdawg=CDAWG):
    possible_scrabble_letters = [] if NO_TWL else twl.children(word)
    if cdawg is None: return possible_scrabble_letters
    possible_other_letters = [possible_word.replace(word,'')[:1] if possible_word!=word else '$' for possible_word in cdawg.keys(word)]
    possible_searched_letters = list(possible_scrabble_letters) ; possible_searched_letters.extend(y for y in possible_other_letters if y not in possible_searched_letters)
    return possible_searched_letters

def twl_dawg_check(word, cdawg=CDAWG):
    output = False if NO_TWL else twl.check(word)
    if cdawg is None: return output
    return output or word in cdawg

def find_element(by=By.ID, name=None):
    for n in name:
        try:
            return driver.find_element(by, n)
        except NoSuchElementException as nsee:
            pass
    return driver.find_element(by, name)

def click_on_element(by=By.ID, name=None):
    element = driver.find_element(by, name)
    element.click()
    time.sleep(default_delay)

def hover_click_on_element(by=By.ID, name=None):
    element = driver.find_element(by, name)
    hover = ActionChains(driver).move_to_element(element)
    hover.perform()
    # time.sleep(default_delay/2.0)
    element.click()
    time.sleep(default_delay)

def guess_word(row, col, word, board2D, used_positions=[], cdawg=CDAWG, debug=DEBUG):
    if debug: print(f"Calling guess_word with ({row}, {col}) for '{word}'\nused_positions: {used_positions}")
    board_size = len(board2D)
    possible_scrabble_letters = twl_dawg_children(word) # twl.children(word)
    if debug: print(f'possible_scrabble_letters: {possible_scrabble_letters}')
    possible_next_letters = []
    possible_next_letters_locs = []
    for col_step in range(-1, 2, 1):
        for row_step in range(-1, 2, 1):
            if col_step == 0 and row_step == 0: continue
            new_row = row + row_step
            new_col = col + col_step
            if new_row<0 or new_row>=board_size: continue
            if new_col<0 or new_col>=board_size: continue
            upsn_flag = False
            for upsn in used_positions:
                if new_row==upsn[0] and new_col==upsn[1]: upsn_flag = True
            if upsn_flag: continue
            possible_next_letters.append(board2D[row+row_step][col+col_step])
            possible_next_letters_locs.append((new_row, new_col))
    # next_letters = list(set(possible_next_letters).intersection(possible_scrabble_letters))
    next_letters = []
    next_letters_locs = []
    for i in range(len(possible_next_letters)):
        if possible_next_letters[i] in possible_scrabble_letters:
            next_letters.append(possible_next_letters[i])
            next_letters_locs.append(possible_next_letters_locs[i])
    if debug: print(f'next_letters: {next_letters}')
    next_calls = []
    if twl_dawg_check(word) and (len(next_letters)==0 or possible_scrabble_letters[0]=='$'):
        next_calls.append(word)
    for i in range(len(next_letters)):
        next_calls.append(f'guess_word({next_letters_locs[i][0]}, {next_letters_locs[i][1]}, "{word}{next_letters[i]}", board2D, {used_positions+[(row, col)]})')
        # return guess_word(next_letters_locs[i][0], next_letters_locs[i][1], f'{word}{next_letters[i]}', board2D, used_positions+[(row, col)])
    return next_calls

try:
    click_on_element(By.CLASS_NAME, "skipTutorial")
    click_on_element(By.ID, "confirmAccept")
except NoSuchElementException as nsee:
    print("No tutorial to skip.")
finally:
    time.sleep(default_delay)

# try: # when they have some sale on squaredle+
#     click_on_element(By.ID, "featureMessage")
#     # hover_click_on_element(By.ID, "saleDontRemindLater")
#     webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
# except NoSuchElementException as nsee:
#     print("No subscription prompt.")
# finally:
#     time.sleep(default_delay)

## tries to sign in   
try:
    click_on_element(By.ID, 'drawerBtn')
    time.sleep(default_delay*.5)
    click_on_element(By.XPATH, '/html/body/div[1]/a[4]') # register/signin
    time.sleep(default_delay*.5)
    click_on_element(By.XPATH, '/html/body/div[10]/div/form/div[3]/a') # signin instead
    time.sleep(default_delay*.5)
    click_on_element(By.XPATH, '/html/body/div[11]/div/form/div[3]/input[1]') # email input box
    time.sleep(default_delay*.5)
    webdriver.ActionChains(driver).send_keys(SQUAREDLE_USER).perform()
    time.sleep(default_delay*.5)
    click_on_element(By.XPATH, '/html/body/div[11]/div/form/div[3]/input[2]') # pswd input box
    webdriver.ActionChains(driver).send_keys(SQUAREDLE_PASS).perform()
    time.sleep(default_delay*.5)
    webdriver.ActionChains(driver).send_keys(Keys.ENTER).perform()
    time.sleep(default_delay*.5)
    webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    time.sleep(default_delay*.5)
except NoSuchElementException as nsee:
    print('Could not sign in.')

# try: # to select special games
#     click_on_element(By.XPATH, '/html/body/header/div/div[1]/button[1]')
#     time.sleep(default_delay)
#     click_on_element(By.XPATH, '/html/body/div[1]/a[7]')
#     time.sleep(default_delay)
#     # # Kwanza
#     # click_on_element(By.XPATH, '//*[@id="specialPuzzles"]/div/div[7]/a')
#     # 10x10 'Abandon hope game' 
#     click_on_element(By.XPATH, '//*[@id="specialPuzzles"]/div/div[54]/div[3]/a')
#     # # 10x10 Themed game
#     # click_on_element(By.XPATH, '//*[@id="specialPuzzles"]/div/div[55]/div[2]/a')
# except NoSuchElementException as nsee:
#     print("Menu not found.")
# finally:
#     time.sleep(default_delay*20)

board_arr = None
while board_arr is None:
    try:
        click_on_element(By.ID, 'showWordsInFoundOrderToggle')
    except NoSuchElementException as nsee:
        print("No toggle for showing words in found order.")
    except Exception as e:
        print(f'Error: {e}')
    
    try: # to get the bonus word hint
        click_on_element(By.XPATH, '//*[@id="wordsTodayTab"]/div[8]/section[4]/div/a')
        click_on_element(By.ID, 'sh4re')
        click_on_element(By.ID, 'shareContentCopyBtn')
        time.sleep(4) # squaredle waits like 5s before showing the button
        click_on_element(By.ID, 'bwotdHintBtn')
        bonus_word_hint = find_element(By.ID, 'bwotdHint').text
        # click_on_element(By.XPATH, '//*[@id="sh4re"]/h2/div/a/svg/use')
        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        if DEBUG: print(bonus_word_hint)
    except NoSuchElementException as nsee:
        print("Couldn't find share button.")
    finally:
        time.sleep(default_delay)
    
    game = find_element(By.ID, "game")
    board = find_element(By.ID, "board")
    board_arr = np.array(board.text.split('\n'))
    board_arr = [s.lower() for s in board_arr]

board_size = int(sqrt(len(board_arr)))
board2D = np.reshape(board_arr, (-1, board_size))
print(board2D)
words = []
for col in range(board_size):
    for row in range(board_size):
        if DEBUG: print(f'Checking grid position ({row}, {col}) ({board2D[row][col]})')
        # recurse_flag = True
        next_calls = guess_word(row, col, board2D[row][col], board2D)
        while type(next_calls) is list and len(next_calls)>0:
            if DEBUG: print("Starting loop")
            if DEBUG: print(next_calls)
            temp_nc = []
            for nc in next_calls:
                # results = exec(nc)
                results = None
                exec(f'results = {nc}')
                # if type(results) is list:
                for result in results:
                    if 'guess_word(' in result:
                        temp_nc.append(result)
                    else:
                        words.append(result)
            next_calls = temp_nc
            if DEBUG:
                for nc in next_calls:
                    print(f'nc: {nc}')
        words = list(set([word for word in words if len(word)>3]))
if DEBUG: print(words)

# print(len(bonus_word_hint))
# print(bonus_word_hint.split('*'))
# print(twl.children(bonus_word_hint.split('*')[0]))

# exit(0)


found_words = []
# for i in range(len(words)):
popup_count = 0
for word in tqdm(words):
    tries = 0
    while word not in found_words:
        webdriver.ActionChains(driver).send_keys(word).perform()
        time.sleep(default_delay*.015)
        webdriver.ActionChains(driver).send_keys(Keys.ENTER).perform()
        time.sleep(default_delay*.015)
        webdriver.ActionChains(driver).send_keys(Keys.ENTER).perform()
        time.sleep(default_delay*.015)
        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(default_delay*.015)
        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        found_words = find_element(By.ID, 'wordsInFoundOrder').text
        for delim in ['\n',', ']:
            found_words = " ".join(found_words.split(delim))
        found_words = found_words.split()
        if word not in found_words:
            time.sleep(default_delay*.5)
        else:
            time.sleep(default_delay*.05)
        if DEBUG: print(f'found_words: {found_words}')
        if tries>=5: break
        tries+=1
        # break

time.sleep(default_delay*6)
webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
bonus_words_progress = find_element(By.XPATH, ['//*[@id="wordsTodayTab"]/div[8]/section[10]/div','//*[@id="wordsTodayTab"]/div[8]/section[18]/div'])
regex = r'(\d*)\sof\s(\d*)\sfound'
bonus_progress = []
for matchNum, match in enumerate(re.finditer(regex, bonus_words_progress.text), start=1):
    for groupNum in range(0, len(match.groups())):
        bonus_progress.append(match.group(groupNum+1))
bonus_progress = [row for row in bonus_progress if row.isnumeric()]
print(bonus_progress)


print(found_words)
with open('squaredle_words.json') as f: found_words_dict = json.load(f) # load previously found/saved words
[found_words_dict.update({word:1}) for word in found_words]
with open("squaredle_words.json", "w") as f:
    json.dump(found_words_dict, f, sort_keys=True, indent=4)
print("Sleeping to leave answers on screen.")
time.sleep(default_delay*5000000)
# sleep for long tim once complete so user can view results