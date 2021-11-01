import random
from concurrent.futures import ThreadPoolExecutor
from getpass import getpass

import requests
from bs4 import BeautifulSoup
from requests.exceptions import ReadTimeout

LOGIN_URL = 'https://www.etutor.pl/account/login'
REPETITIONS_URL = 'https://www.etutor.pl/words/user-words'
REPETITION_BLOCKS_URL = 'https://www.etutor.pl/words/user-words-editor-preview/'
USER_AGENTS = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64;rv:89.0)Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:73.0) Gecko/20100101 Firefox/73.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 Edg/92.0.902.67',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0'
)


class ProgressBar:
    def __init__(self, message, no_of_items):
        self.message = message
        self.no_of_items = no_of_items
        self.progress = []

    def __enter__(self):
        print(f'{self.message}  [{self.no_of_items * " "}]\r', end='')
        return self

    def __exit__(self, ex_type, ex_val, ex_tb):
        print()

    def advance(self, filling='#'):
        self.progress.append(filling)
        bar = "".join(self.progress) + (self.no_of_items - len(self.progress)) * " "
        print(f'{self.message}  [{bar}]\r', end='')


def download_blocks(session, progress):
    def downloaded(href):
        session.headers.update({'User-Agent': random.choice(USER_AGENTS)})
        response = session.get(REPETITION_BLOCKS_URL + href, timeout=10)
        if response.status_code == 200:
            progress.advance()
            return BeautifulSoup(response.text, 'lxml')

        progress.advance('-')
        return None
    return downloaded


def get_custom_hrefs(href_names):
    print('Wybierz bloki powtórek do pobrania:\n'
          '2,4,3 etc.\n')
    for index, (_, hname) in enumerate(href_names, start=1):
        print(f'{str(index):4s}{hname}')
    print()

    choices = [int(x) for x in input('#: ').split(',') if x.strip().isnumeric()]
    return [href_names[x-1][0] for x in choices if 0 < x <= len(href_names)]


def print_config(config):
    print('Załadowana konfiguracja:')
    for option, val in config.items():
        print(f'  {option:16s} : {val}')


def load_config():
    try:
        with open('config.txt', 'r', encoding='utf-8') as conf:
            options_list = sorted(conf.readlines())
    except FileNotFoundError:
        print('==> Brak pliku konfiguracyjnego.')
        return {
            'block_order': 'newest_first',
            'delimiter': 'tab',
            'field_order': '1,2,3,4',
            'ignore_sentences': 'false',
            'max_workers': '4',
            'repetition_order': 'newest_first'
        }

    key_val = []
    for line in options_list:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        t = line.split('=', 1)
        option, val = t[0].strip().lower(), t[-1].strip().lower()
        key_val.append((option, val))
    return dict(key_val)


def main():
    config = load_config()
    print_config(config)

    print('\nZaloguj się do eTutor, aby kontynuować\n')
    auth_data = {
        'login': input('Nazwa użytkownika: '),
        'haslo': getpass('Hasło: ')
    }

    print('Logowanie do eTutora...')
    with requests.Session() as ses:
        ses.headers.update({'User-Agent': random.choice(USER_AGENTS)})
        response = ses.post(LOGIN_URL, data=auth_data, timeout=10)

    if 'Zaloguj się - eTutor' in response.text:
        print('Logowanie nie powiodło się\n'
              'Nieprawidłowa nazwa użytkownika lub hasło')
        import time
        time.sleep(2)
        return None

    print('Zalogowano pomyślnie\n')
    print('Szukam powtórek...')
    response = ses.get(REPETITIONS_URL, timeout=10)
    soup = BeautifulSoup(response.text, 'lxml')

    hrefs = [h['href'].rsplit('/', 1)[-1]
             for h in soup.find_all('a', class_='listName')]

    block_order = config['block_order']
    if block_order.startswith('from_b'):
        hrefs = hrefs[::-1]
    elif block_order.startswith('old'):
        hrefs = sorted(hrefs)
    elif block_order.startswith('new'):
        hrefs = sorted(hrefs, reverse=True)
    elif block_order.startswith('c'):
        block_info = [
            ' '.join(
                (x.text.replace('\n', '').replace('\r', '').rsplit(')', 1)[0] + ')').split()
            )
            for x in soup.find_all('td', class_='wordsListName')
        ]
        hrefs = get_custom_hrefs(tuple(zip(hrefs, block_info)))
    else:  # from_top
        hrefs = hrefs

    connector = '\t' if config['delimiter'] == 'tab' else '\n'
    new_first = config['repetition_order'].startswith('new')
    ignore_sentences = config['ignore_sentences'] == 'true'
    field_order = config['field_order'].split(',')
    no_of_hrefs = len(hrefs)

    # eTutor doesn't tolerate more than 6 workers, using 4 as default just to be safe
    with \
        ProgressBar('Pobieram powtórki     ', no_of_hrefs) as progress, \
        ThreadPoolExecutor(max_workers=int(config['max_workers'])) as executor \
            :
        dl_func = download_blocks(ses, progress)
        blocks = executor.map(dl_func, hrefs)

    dl_error = False
    with \
        ProgressBar('Przetwarzam i zapisuję', no_of_hrefs) as progress, \
        open('karty.txt', 'a', encoding='utf-8') as f \
            :
        for block in blocks:
            if block is None:
                dl_error = True
                progress.advance('-')
                continue

            if ignore_sentences:
                repetitions = block.find_all('p', class_='hws phraseEntity')
            else:
                repetitions = block.select('p.hws.phraseEntity, div.maintext')

            processed = []
            for repetition in repetitions:
                # processing with split and replace is much
                # more efficient than using bs4 find methods
                extract = repetition.text.strip()[:-11].replace('\n', '')

                phrase = extract.split('=', 1)[0].strip(', ').replace(' , ', ', ')
                translation = extract.split('=', 1)[-1].split('\xa0', 1)[0]

                if '\xa0synonym:' in extract:
                    synonyms = extract.split('\xa0synonym:')[-1].split('\xa0\r')[0]
                else:
                    synonyms = ''

                if 'Edit the note' in extract:
                    note = extract.rsplit('Edit the note', 1)[-1]
                else:
                    note = ''

                data = {'0': '',
                        '1': translation,
                        '2': phrase,
                        '3': synonyms,
                        '4': note}
                processed.append(connector.join([data[x].strip() for x in field_order]) + '\n')

            if new_first:
                f.writelines(processed[::-1])
            else:
                f.writelines(processed)

            progress.advance()

    if dl_error:
        print('** Nie udało się pobrać wszystkich powtórek **\n'
              '** Zmniejsz ilość wątków używanych do pobierania **')
    else:
        print('** Zakończono - karty zapisane do pliku "karty.txt" **')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nUnicestwiony')
    except ReadTimeout:
        print('\nThe server did not send any data in the allotted amount of time')
