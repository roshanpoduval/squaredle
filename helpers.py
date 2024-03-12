# import nltk ; nltk.download('words') # only need to do this once
from datetime import datetime
# import enchant
import os
import json
import pytz
import time
import functools
import numpy as np
import multiprocessing
# import regex as re
import re
from math import sqrt
import argparse as ap
from loguru import logger as log
import twl
import dawg_python
from nltk.corpus import words
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
# from playwright.sync_api import sync_playwright

log.level('ERROR')

SQUAREDLE_USER = os.environ.get('SQUAREDLE_USER')
SQUAREDLE_PASS = os.environ.get('SQUAREDLE_PASS')
NO_TWL = False
CDAWG = dawg_python.CompletionDAWG().load('NSWL2020.completion.dawg')
if NO_TWL: assert CDAWG is not None
# d = enchant.Dict("en_US")

def twl_dawg_check(word, cdawg=CDAWG):
    output = False if NO_TWL else twl.check(word)
    if cdawg is None: return output
    return output or word in cdawg

def check_if_word(word):
    output = 0
    if word in words.words() or twl_dawg_check(word): # or d.check(word)
        output = 99
    # elif : # check consecutive consonants/vowels and consonant to vowel ratio
    return output

def hint_time_check():
    now = datetime.now(pytz.timezone('US/Central'))
    if now.hour >= 17:
        return True
    else:
        return False

def wait(s):
    time.sleep(s)

def wait_forever():
    while (True): time.sleep(1)

def find_element(driver, by=By.ID, name=None):
    output = None
    if isinstance(name, list):
        for n in name:
            tries = 0
            while output is None and tries<5:
                try:
                    output = driver.find_element(by, n)
                # except NoSuchElementException as nsee:
                except Exception as e:
                    tries+=1
                    pass
            if output is None:
                raise Exception("None of the elements could be found.")
    else:
        tries = 0
        while output is None and tries<5:
            try:
                output = driver.find_element(by, name)
            # except NoSuchElementException as nsee:
            except Exception as e:
                tries+=1
                pass
        if output is None:
            raise Exception(f"The element '{name}' could not be found.")
    return output
        

def click_on_element(driver, by=By.ID, name=None, default_delay=.1):
    if isinstance(name, list):
        for n in name:
            try:
                element = find_element(driver, by, n)
                element.click()
                return
            except Exception as e:
                pass
        raise Exception("None of the elements could be clicked.")
    else:
        try:
            element = find_element(driver, by, name)
            element.click()
        except Exception as e:
            raise
    wait(default_delay)

def send_keys(driver, keys, default_wait=.01):
    ActionChains(driver).send_keys(keys).perform()
    wait(default_wait)

def close_popups(driver):
    send_keys(driver, Keys.ESCAPE)
    send_keys(driver, Keys.ESCAPE)
    send_keys(driver, Keys.ESCAPE)

def skip_tutorial(driver):
    log.info('skipping tutorial')
    click_on_element(driver, By.CLASS_NAME, "skipTutorial")
    click_on_element(driver, By.ID, "confirmAccept")

def login(driver):
    log.info('logging in')
    click_on_element(driver, By.ID, 'drawerBtn') # open drawer
    click_on_element(driver, By.CLASS_NAME, 'registerBtn', .5) 
    click_on_element(driver, By.XPATH, '/html/body/div[10]/div/form/div[3]/a', .5) # signin instead of register
    click_on_element(driver, By.XPATH, '/html/body/div[11]/div/form/div[3]/input[1]', .5) # email input box
    send_keys(driver, SQUAREDLE_USER)
    send_keys(driver, Keys.TAB)
    send_keys(driver, SQUAREDLE_PASS)
    send_keys(driver, Keys.ENTER)
    wait(.1)
    send_keys(driver, Keys.ESCAPE)
    send_keys(driver, Keys.ESCAPE)

def get_board(driver):
    board_arr = None
    board = find_element(driver, By.ID, "board")
    board_arr = np.array(board.text.split('\n'))
    board_arr = [s.lower() for s in board_arr if not s.isdigit()]
    return board_arr

def get_bonus_word_hint(driver):
    bonus_word_hint = None
    click_on_element(driver, By.XPATH, [f'//*[@id="wordsTodayTab"]/div[8]/section[{x}]/div/a' for x in range(5,20)], 2) # share button for bonus word hint
    # click_on_element(driver, By.XPATH, [f'/html/body/div[2]/div[4]/div/div/div[2]/div[8]/section[{x}]/div/a' for x in range(1,20)], 2) # share button for bonus word hint
    # click_on_element(driver, By.XPATH, ['/html/body/div[2]/div[4]/div/div/div[2]/div[8]/section[5]/div/a','/html/body/div[2]/div[4]/div/div/div[2]/div[8]/section[8]/div/a'], 2) # share button for bonus word hint
    while bonus_word_hint is None:
        try:
            click_on_element(driver, By.ID, 'shareContentCopyBtn', 5)
            click_on_element(driver, By.XPATH, '/html/body/div[18]/div/div[5]/span/a') # reveal hint
            bonus_word_hint = find_element(driver, By.ID, 'bwotdHint').text
        except Exception as e:
            pass
        send_keys(driver, Keys.ESCAPE)
        send_keys(driver, Keys.ESCAPE)
    return bonus_word_hint

def get_found_words(driver):
    found_words = find_element(driver, By.ID, 'wordsInFoundOrder').text
    for delim in ['\n',', ']:
        found_words = " ".join(found_words.split(delim))
    found_words = found_words.split()
    # log.debug(f'found_words: {found_words}')
    return found_words

def try_word(driver, wg):
    found_words = get_found_words(driver)
    tries = 0
    while wg not in found_words and tries<3:
        send_keys(driver, Keys.ESCAPE)
        send_keys(driver, Keys.ESCAPE)
        send_keys(driver, wg, .02)
        send_keys(driver, Keys.ENTER)
        send_keys(driver, Keys.ENTER)
        send_keys(driver, Keys.ESCAPE)
        send_keys(driver, Keys.ESCAPE)
        found_words = get_found_words(driver)
        if wg not in found_words:
            tries+=1
        else:
            save_progress(driver)
            return wg

def try_words(driver, wgs):
    cwgs = []
    for wg in wgs:
        cwgs.append(try_word(driver, wg))
    return cwgs

def save_progress(driver):
    found_words = get_found_words(driver)
    with open('squaredle_words.json') as f: found_words_dict = json.load(f) # load previously found/saved words
    [found_words_dict.update({word:1}) for word in found_words]
    with open("squaredle_words.json", "w") as f:
        json.dump(found_words_dict, f, sort_keys=True, indent=4)

def get_word_progress(game_text, after_five):
    game_text = game_text.replace('\n\n','\n')
    word_progress = {}
    regex = r"(?P<word_length>\d*)(?: letters\s)(?P<word_list>[^\d \+]*)(?:\+(?P<asdf>\d*)(?: words? left)(?: - Reveal a random word)?)?"
    matches = re.finditer(regex, game_text, re.MULTILINE)
    for matchNum, match in enumerate(matches, start=1):
        word_length = int(match.group(1))
        word_list = match.group(2)
        num_words_remaining = match.group(3)
        if word_list is not None and len(word_list)>0:
            word_list = word_list.split('\n')
        else:
            word_list = []
        if num_words_remaining is not None:
            word_list.append('*' * word_length)
        word_progress[word_length] = [word for word in word_list if word not in ['Bonus','']]
    # if after_five:
    #     regex = r"(?P<word_length>\d*)(?: letters\s)(?P<word_list>[^\d ]*)(?:\n*)"
    #     matches = re.finditer(regex, game_text, re.MULTILINE)
    #     for matchNum, match in enumerate(matches, start=1):
    #         word_length = match.group(1)
    #         word_list = match.group(2).split('\n')
    #         word_progress[word_length] = [word for word in word_list if word not in ['Bonus','']]
    # else:
    #     regex = r'(?P<word_length>\d*)(?: letters\s)(?:\+)(?P<number_of_words>\d*)(?: words? left)'
    #     matches = re.finditer(regex, game_text, re.MULTILINE)
    #     for matchNum, match in enumerate(matches, start=1):
    #         word_length = int(match.group(1))
    #         number_of_words = int(match.group(2))
    #         word_array = ['*' * word_length ] # for _ in range(number_of_words)
    #         word_progress[word_length] = word_array
    return word_progress

def get_bonus_word(game_text):
    regex = r"(?:Bonus Word of the Day\s)(?P<bonus_word>.*)(?:.*\s)"
    matches = re.finditer(regex, game_text, re.MULTILINE)
    for matchNum, match in enumerate(matches, start=1):
        log.debug(f"Match {matchNum} was found at {match.start()}-{match.end()}: {match.group()}")
        return match.group(1)

def get_bonus_word_progress(game_text):
    regex = r"(?:Bonus words found\s)(?P<numerator>\d*)(?: of )(?P<denominator>\d*)(?: found\s)(?P<bonus_word_list>.*)"
    matches = re.finditer(regex, game_text, re.MULTILINE)
    for matchNum, match in enumerate(matches, start=1):
        log.debug(f"Match {matchNum} was found at {match.start()}-{match.end()}: {match.group()}")
        return (match.group(1), match.group(2), match.group(3),)

@functools.lru_cache(maxsize=None)
def get_letter(x, y, board):
    return board[x][y]

@functools.lru_cache(maxsize=None)
def get_positions(letter, board, used_positions=()):
    psns = []
    if len(used_positions)==0:
        for i,row in enumerate(board):
            for j,cell in enumerate(row):
                if cell == letter or letter == '*':
                    psns.append((i,j))
    elif len(used_positions)==1:
        new_positions = []
        for col_step in range(-1,2,1):
            for row_step in range(-1,2,1):
                if col_step==0 and row_step==0: continue
                new_row = used_positions[0][0]+row_step
                new_col = used_positions[0][1]+col_step
                if new_row<0 or new_row>=len(board): continue
                if new_col<0 or new_col>=len(board): continue
                new_positions.append((new_row, new_col))
        for np in new_positions:
            if get_letter(np[0],np[1],board) == letter or letter == '*':
                psns.append(np)
    else:
        psns = get_positions(letter, board, (used_positions[-1],))
        psns = [p for p in psns if p not in used_positions]
    return psns
        
# def merge_names(a, b):
#     return '{} & {}'.format(a, b)
# if __name__ == '__main__':
#     names = ['Brown', 'Wilson', 'Bartlett', 'Rivera', 'Molloy', 'Opie']
#     with multiprocessing.Pool(processes=3) as pool:
#         results = pool.starmap(merge_names, product(names, repeat=2))
#     print(results)
# this won't really work for when multiple letters are repeated
# I need a network flow solution (work backwards? does that even matter?)
@functools.lru_cache(maxsize=None)
def get_word_guesses(word, board, used_positions=(), position=0, driver=None):
    next_calls = []
    if position<len(word):
        # log.debug(f'position: {position}')
        # log.debug(f'{word[position]}')
        possible_positions = get_positions(word[position], board, used_positions)
        # log.debug(f'possible_positions: {possible_positions}')
        results = []
        mp_starmap_args = []
        for pp in possible_positions:
            new_word = word[:position] + get_letter(pp[0], pp[1], board) + word[position+1:]
            # log.debug(f'new_word: {new_word}')
            results.append(get_word_guesses(new_word, board, used_positions+(pp,), position+1, driver))
            # next_calls.append(f'get_word_guesses("{new_word}", board, {used_positions+(pp,)}, {position+1}, driver)')
            # mp_starmap_args.append((new_word, board, used_positions+(pp,), position+1, driver))
        # with multiprocessing.Pool(processes=1) as pool:
        #     results = pool.starmap(get_word_guesses, mp_starmap_args)
        # for nc in next_calls:
        #     exec(f'results.append({nc})')
        while any(isinstance(sublist, list) for sublist in results):
            # results = [item for sublist in results for item in sublist]
            # results = [item for sublist in results for item in sublist if item is not None]
            results = [item for sublist in results if sublist is not None for item in sublist if item is not None]
        results = list(set(results))
        results = sorted(results, key=check_if_word, reverse=True)
        correct_word_guesses = []
        if driver is not None and len(results)>=5:
            correct_word_guesses.append(try_words(driver, results))
        else:
            correct_word_guesses = results
        return correct_word_guesses
    else:
        if '*' in word:
            log.ERROR(f'Word "{word}" still has "*" in it at end of recursion.')
            return
        # elif not check_if_word(word):
        #     # log.warning(f'Word "{word}" may not be a word.')
        #     return
        return [word]

def get_try_word_guesses(driver, word, board, used_positions=(), position=0):
    return get_word_guesses(word, board, used_positions, position, driver)

def twl_dawg_children(word, cdawg=CDAWG):
    possible_scrabble_letters = [] if NO_TWL else twl.children(word)
    if cdawg is None: return possible_scrabble_letters
    possible_other_letters = [possible_word.replace(word,'')[:1] if possible_word!=word else '$' for possible_word in cdawg.keys(word)]
    possible_searched_letters = list(possible_scrabble_letters) ; possible_searched_letters.extend(y for y in possible_other_letters if y not in possible_searched_letters)
    return possible_searched_letters

def guess_word_helper(row, col, word, board, used_positions=[], cdawg=CDAWG):
    log.debug(f"Calling guess_word with ({row}, {col}) for '{word}'\nused_positions: {used_positions}")
    board_size = len(board)
    possible_scrabble_letters = twl_dawg_children(word) # twl.children(word)
    log.debug(f'possible_scrabble_letters: {possible_scrabble_letters}')
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
            possible_next_letters.append(board[row+row_step][col+col_step])
            possible_next_letters_locs.append((new_row, new_col))
    # next_letters = list(set(possible_next_letters).intersection(possible_scrabble_letters))
    next_letters = []
    next_letters_locs = []
    for i in range(len(possible_next_letters)):
        if possible_next_letters[i] in possible_scrabble_letters:
            next_letters.append(possible_next_letters[i])
            next_letters_locs.append(possible_next_letters_locs[i])
    log.debug(f'next_letters: {next_letters}')
    next_calls = []
    if twl_dawg_check(word) and (len(next_letters)==0 or possible_scrabble_letters[0]=='$'):
        next_calls.append(word)
    for i in range(len(next_letters)):
        next_calls.append(f'guess_word_helper({next_letters_locs[i][0]}, {next_letters_locs[i][1]}, "{word}{next_letters[i]}", board, {used_positions+[(row, col)]})')
        # return guess_word(next_letters_locs[i][0], next_letters_locs[i][1], f'{word}{next_letters[i]}', board2D, used_positions+[(row, col)])
    return next_calls

def guess_words(board):
    board_size = len(board)
    words = []
    for col in range(board_size):
        for row in range(board_size):
            log.debug(f'Checking grid position ({row}, {col}) ({board[row][col]})')
            # recurse_flag = True
            next_calls = guess_word_helper(row, col, board[row][col], board)
            while type(next_calls) is list and len(next_calls)>0:
                log.debug("Starting loop")
                log.debug(next_calls)
                temp_nc = []
                for nc in next_calls:
                    # results = exec(nc)
                    results = None
                    exec(f'results = {nc}')
                    # if type(results) is list:
                    for result in results:
                        if 'guess_word_helper(' in result:
                            temp_nc.append(result)
                        else:
                            words.append(result)
                next_calls = temp_nc
                for nc in next_calls:
                    log.debug(f'nc: {nc}')
            words = list(set([word for word in words if len(word)>3]))
    log.debug(words)

if __name__=='__main__':
    board = (('e' 'b' 'm' 'd'),
             ('g' 'a' 'l' 'k'),
             ('j' 'i' 'c' 'f'),
             ('p' 'h' 'n' 'o'))
    log.debug(get_word_guesses('ba****ip', board))
    # board = (('b' 'b' 's' 's'),
    #          ('o' 'b' 'b' 's'),
    #          ('y' 'b' 'b' 'b'),
    #          ('s' 's' 'y' 'b'))
    # log.debug(get_word_guesses('b**s', board))