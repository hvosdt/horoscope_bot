from bs4 import BeautifulSoup
import urllib.request

ZODIAC_SIGNS = {
    "aries": 1, #Овен
    "taurus": 2, #Телец
    "gemini": 3, #Близнецы
    "cancer": 4, #Рак
    "leo": 5, #Лев
    "virgo": 6, #Дева
    "libra": 7, #Весы
    "scorpio": 8, #Скорпион
    "sagittarius": 9, #Стрелец
    "capricorn": 10, #Козерог
    "aquarius": 11, #Водолей
    "pisces": 12 #Рыбы
}

def parse_horoscope_page(url):
    #items = []
    #url = 'https://horo.mail.ru/prediction/gemini/today/'
    page = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(page, 'html.parser')
    #tbody = soup.find('tbody')
    '''
    with open('body.html', 'w') as file:
        file.write(str(soup))
    '''
    data = soup.find('div', attrs={'class': 'article__item article__item_alignment_left article__item_html'})
    p = data.find_all('p')
    res = ''
    for i in p:
        res = res + i.text + '\n\n'
    return res

class Horoscope():
    def __init__(self, sign) -> None:
        self.sign = sign if sign else 'Aries'

    def get(self, period):
        url = f'https://horo.mail.ru/prediction/{self.sign}/{period}/'
        print(url)
        horoscope = parse_horoscope_page(url)
        return horoscope
    
    def get_tooday(self):
        url = f'https://horo.mail.ru/prediction/{self.sign}/today/'
        print(url)
        horoscope = parse_horoscope_page(url)
        return horoscope
    
    def get_tomorrow(self):
        url = f'https://horo.mail.ru/prediction/{self.sign}/tomorrow/'
        horoscope = parse_horoscope_page(url)
        return horoscope

    def get_week(self):
        url = f'https://horo.mail.ru/prediction/{self.sign}/week/'
        horoscope = parse_horoscope_page(url)
        return horoscope