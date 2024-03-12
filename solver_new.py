from helpers import *

parser = ap.ArgumentParser("Squaredle solver")
parser.add_argument('--log_level', type=str, default='ERROR', help='Set the log level. [ERROR, WARNING, INFO, DEBUG] (default is ERROR)')
parser.add_argument('--no_login', action='store_true', help='Flag to disable login. (default is to login)')
parser.add_argument('--special', type=str, help='Used to select special game mode. (default is None for current puzzle)')
parser.add_argument('--close', action='store_true', help='Flag to enable closing browser on completion.')
parser.add_argument('--headless', action='store_true', help='Flag to enable headless browser.')
parser.add_argument('--tutorial',action='store_true', help="Flag to enable tutorial mode. Default behavior is to skip the tutorial. Enabling tutorial may mess with auto-login.")
args = parser.parse_args()

if __name__ == "__main__":
    log.add('solver.log')
    log.debug(args)
    log.level(args.log_level)
    # playwright = sync_playwright().start()
    # browser = playwright.chromium.launch(headless=args.headless)
    # squaredle = browser.new_page()
    # squaredle.goto("https://squaredle.app/")
    squaredle = webdriver.Chrome(); squaredle.get("https://squaredle.app/")
    
    if not args.tutorial:
        skip_tutorial(squaredle)
    
    close_popups(squaredle)
    
    if not args.no_login:
        login(squaredle)
        wait(5)
        close_popups(squaredle)
    
    board_array = get_board(squaredle)
    log.debug(board_array)
    
    # # click_on_element(squaredle, By.XPATH, '/html/body/div[2]/main/div[2]/div[2]/div/div[3]', .1)
    
    board_size = int(sqrt(len(board_array)))
    board2D = np.reshape(board_array, (-1, board_size))
    board2D = tuple(tuple(row) for row in board2D)
    log.info(f'\n{board2D}')
    
    after_five = False
    if hint_time_check():
        log.info(f'It is after 5, so hints are enabled.')
        after_five = True
        click_on_element(squaredle, By.ID, 'hintSort', .1)
        click_on_element(squaredle, By.ID, 'hintFirstLetters', .1)
    game_text = find_element(squaredle, By.XPATH, "/html/body/div[2]/div[4]/div/div/div[2]/div[8]").text\
        .replace('Tap a missing word to reveal it','')\
        .replace('Bonus Word of the Day','\nBonus Word of the Day')
    log.debug(f'\n{game_text}')
    
    bonus_word = get_bonus_word(game_text)
    word_progress = get_word_progress(game_text, after_five)
    bonus_word_progress = get_bonus_word_progress(game_text)
    found_words = get_found_words(squaredle)
    
    click_on_element(squaredle, By.ID, 'showWordsInFoundOrderToggle')
    if '*' in bonus_word:
        log.debug(f'Getting bonus word hint.')
        bonus_word_hint = get_bonus_word_hint(squaredle)
        word_guesses = get_try_word_guesses(squaredle, bonus_word_hint, board2D)
        # for wg in word_guesses:
        #     try_word(squaredle, wg)
    
    # for wg in guess_words(board2D):
    #     try_word(squaredle, wg)
    log.debug(f'word_progress: {word_progress}')
    for word_length, word_list in sorted(list(word_progress.items()), key=lambda x:int(x[0]), reverse=after_five):
        log.debug(f'\n{word_length} letters:\n{word_list}')
        for word in word_list:
            if '*' in word:
                # word_guesses = get_try_word_guesses(squaredle, word, board2D)
                word_guesses = get_word_guesses(word, board2D)
                log.debug(f'word_guesses:\n{word_guesses}')
                for wg in word_guesses:
                    cgw = try_word(squaredle, wg)
    #                 break # remove this to try all guesses (if you have two word hints like r***, the second one will be skipped [also bonus words])
    # # may still need to do a more thorough check for bonus words            
    
    if args.close or args.headless:
        log.debug('closing...')
        # browser.close()
        # playwright.stop()
    else:
        wait_forever() # while (True): time.sleep(1)