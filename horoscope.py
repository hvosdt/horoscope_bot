from bs4 import BeautifulSoup
import urllib.request
from pymongo.mongo_client import MongoClient

client = MongoClient('localhost', 27017)

db = client.horoscope_db
users = db.users
compatibility = db.compatibility
db_main = db.main
db_hea = db.hea
db_ero = db.ero
db_bus = db.bus

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

EXTRA_HORO = {
    'hea': 'Здоровье',
    'ero': 'Эротический',
    'bus': 'Деловой'
}

class Horoscope():
    def __init__(self, sign) -> None:
        self.sign = sign if sign else 'Aries'

    def get_main(self, period):
        horoscope = db_main.find({'sign': self.sign})[0]
        return horoscope[period]
    
    def get_extra(self, extra, period):
        result = []
        for i in extra:
            if i == 'hea':
                text = db_hea.find({'sign': self.sign})[0]
                result. append(EXTRA_HORO[i] + '\n' + text[period])
            if i == 'ero':
                text = db_ero.find({'sign': self.sign})[0]
                result. append(EXTRA_HORO[i] + '\n' + text[period])
            if i == 'bus':
                text = db_bus.find({'sign': self.sign})[0]
                result. append(EXTRA_HORO[i] + '\n' + text[period])
        return result