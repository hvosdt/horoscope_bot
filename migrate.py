from bs4 import BeautifulSoup
import urllib.request
from pymongo.mongo_client import MongoClient

client = MongoClient('localhost', 27017)

db = client.horoscope_db
compatibility = db.compatibility
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

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
    #url = 'https://horo.mail.ru/compatibility/zodiac/2/'
    page = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(page, 'html.parser')
    tbody = soup.find_all('tbody')
    
    with open('body.html', 'w') as file:
        file.write(str(soup))
    d = {}
    
    for p in soup.select('p'):
        if p.find_previous('h2'):
            if d.get(p.find_previous('h2').text) == None:
                d[p.find_previous('h2').text]=[]
                per = soup.find('div', attrs={'class': 'p-item__left-icon-text'})
        else:
            continue
        d[p.find_previous('h2').text].append(p.text)
    
    for k, v in d.items():  
        print(k)
        print(v[0])
    return d, per.text
    
def migrate_db():
    signs = []
    for i in ZODIAC_SIGNS:
        signs.append(i)
    print(signs)
    i = 1
    j = 1
    res = {}
    for sign in signs:
        for j in range(12):
            try:
                title = '{sign1}-{sign2}'.format(
                    sign1 = sign,
                    sign2 = signs[j])
                
                description, percent = parse_horoscope_page(f'https://horo.mail.ru/compatibility/zodiac/{i}/')
                compatibility.insert_one({
                    'title': title,
                    'description': description,
                    'percent': percent
                    }
                )
            except: pass
            i += 1
            
if __name__ == '__main__': 
    migrate_db