from getpass import getpass
from bs4 import BeautifulSoup
import requests
from requests.exceptions import ReadTimeout
from time import sleep

LOGIN_URL = 'https://www.etutor.pl/account/login'
REPETITIONS_URL = 'https://www.etutor.pl/words/user-words'
REPETITION_BLOCKS_URL = 'https://www.etutor.pl/words/user-words-editor-preview/'

USER_AGENT = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64;rv:89.0)Gecko/20100101 Firefox/90.0'
}

def get_custom_hrefs(href_names):
    print('Wybierz bloki do przetworzenia:\n'
          '2,4,3 etc.\n')
    for index, (href, hname) in enumerate(href_names, start=1):
        print(f'{str(index):4s}{hname}')
    print()

    choices = [int(x)
               for x in input('#: ').split(',')
               if x.strip().isnumeric()]

    hrefs = []
    for ch in choices:
        if 0 < ch <= len(href_names):
            href = href_names[ch-1][0]
            hrefs.append(href)
    return hrefs


def load_config():
    try:
        with open('config.txt', 'r', encoding='utf-8') as conf:
            options_list = sorted(conf.readlines())
    except FileNotFoundError:
        config = {
            'block_order': 'from_top',
            'delimiter': 'tab',
            'field_order': '1,2,3,4',
            'ignore_sentences': 'false',
            'repetition_order': 'oldest_first'
        }
        print('==> Brak pliku konfiguracyjnego\n'
              'Załadowano domyślną konfigurację:')
        for op, val in config.items():
            print(f'  {op:16s} : {val}')
        return config

    print('Załadowana konfiguracja:')
    key_val = []
    for line in options_list:
        line = line.strip()
        if not line or line.strip().startswith('#'):
            continue

        t = line.split('=', 1)
        op, val = t[0].strip().lower(), t[-1].strip().lower()
        key_val.append((op, val))
        print(f'  {op:16s} : {val}')
    return dict(key_val)


def main():
    config = load_config()

    print('\nZaloguj się do eTutor, aby kontynuuować\n')
    auth_data = {
        'login': input('Nazwa użytkownika: '),
        'haslo': getpass('Hasło: ')
    }

    print('Logowanie do eTutora...')
    with requests.Session() as ses:
        ses.headers.update(USER_AGENT)
        response = ses.post(LOGIN_URL, data=auth_data, timeout=10)

    if 'Zaloguj się - eTutor' in response.text:
        print('Logowanie nie powiodło się\n'
              'Nieprawidłowa nazwa użytkownika lub hasło')
        sleep(2)
        return None

    print('Zalogowano pomyślnie\n')
    print('Pozyskuję bloki z powtórkami...')
    response = ses.get(REPETITIONS_URL, timeout=10)
    soup = BeautifulSoup(response.text, 'lxml')
    href_data = soup.find_all('a', class_='listName')

    hrefs = [h['href'].rsplit('/', 1)[-1] for h in href_data]

    block_order = config.get('block_order', 'from_top')
    if block_order.startswith('from_b'):
        hrefs = hrefs[::-1]
    elif block_order.startswith('old'):
        hrefs = sorted(hrefs)
    elif block_order.startswith('new'):
        hrefs = sorted(hrefs, reverse=True)
    elif block_order.startswith('c'):
        full_block_info = soup.find_all('td', class_='wordsListName')
        block_info = [x.text.replace('\n', '').replace('\r', '').rsplit(')', 1)[0] + ')'
                      for x in full_block_info]
        block_info = [' '.join(x.split()) for x in block_info]
        
        href_names = tuple(zip(hrefs, block_info))
        hrefs = get_custom_hrefs(href_names)
    else:  # from_top
        hrefs = hrefs

    connector = '\t' if config['delimiter'] == 'tab' else '\n'
    new_first = config['repetition_order'].startswith('new')
    ignore_sentences = config['ignore_sentences'] == 'true'
    field_order = config['field_order'].split(',')

    print('Otwieram plik "karty.txt"\n')
    with open('karty.txt', 'a', encoding='utf-8') as f:
        for href in hrefs:
            print(f'Otwieram blok {href}')
            response = ses.get(REPETITION_BLOCKS_URL + href, timeout=10)

            print(f'Przetwarzam...')
            block_soup = BeautifulSoup(response.text, 'lxml')
            if ignore_sentences:
                block = block_soup.find_all('p', class_='hws phraseEntity')
            else:
                block = block_soup.select('p.hws.phraseEntity, div.maintext')

            processed = []
            for repetition in block:
                # processing with split and replace is much more efficient
                # than using bs4.find on each div inside the block
                extract = (repetition.text.strip())[:-11].replace('\n', '')

                phrase = extract.split('=', 1)[0].strip(', ').replace(' , ', ', ')
                translation = (extract.split('=', 1)[-1].split('\xa0', 1)[0]).strip()

                synonyms = ''
                if '\xa0synonym:' in extract:
                    synonyms = extract.split('\xa0synonym:')[-1].split('\xa0\r')[0]
                    synonyms = synonyms.strip()

                note = ''
                if 'Edit the note' in extract:
                    note = extract.rsplit('Edit the note', 1)[-1].strip()

                data = {'0': '', '1': translation, '2': phrase, '3': synonyms, '4': note}
                processed.append(connector.join([data[x] for x in field_order]) + '\n')

            if new_first:
                processed = processed[::-1]

            print('Zapisuję...')
            f.writelines(processed)
            print(f'Blok {href} gotowy\n')
            
    print('Zakończono\n'
          'Przetworzone karty zapisane do pliku "karty.txt"')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nUnicestwiony')
    except ReadTimeout as e:
        print('\nThe server did not send any data in the allotted amount of time:')
