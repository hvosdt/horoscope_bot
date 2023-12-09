from aiogram import Bot, Dispatcher, types
from typing import Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

import requests
import config
import logging
from time import sleep
from celery import Celery
from celery.schedules import crontab
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from pymongo.mongo_client import MongoClient
import redis
from bs4 import BeautifulSoup
import urllib.request
import xml.etree.ElementTree as ET

from horoscope import Horoscope

client = MongoClient('localhost', 27017)
redis_client = redis.StrictRedis(host="localhost", port=6379, db=0, decode_responses=True)

db = client.horoscope_db
users = db.users
compatibility = db.compatibility
db_main = db.main
db_hea = db.hea
db_ero = db.ero
db_bus = db.bus

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

logging.basicConfig(level=logging.DEBUG, filename='horoscope_bot.log')

client = Celery('haroscope', broker=config.CELERY_BROKER_URL)
client.conf.result_backend = config.CELERY_RESULT_BACKEND
client.conf.timezone = 'Europe/Moscow'

my_id = '182149382'

client.conf.beat_schedule = {
    'send_daily_horoscope': {
        'task': 'handlers.send_daily_horoscope',
        'schedule': crontab(hour=config.DAILY_HOUR, minute=config.DAILY_MINUTE)
    },
    'send_weekly_horoscope': {
        'task': 'handlers.send_weekly_horoscope',
        'schedule': crontab(day_of_week='sunday', hour=20, minute=0)
    },
    'parse_main_horoscope': {
        'task': 'handlers.parse_main_horoscope',
        'schedule': crontab(hour=config.MAIN_HOUR, minute=config.MAIN.MINUTE)
    },
    'parse_extra_horoscope': {
        'task': 'handlers.parse_extra_horoscope',
        'schedule': crontab(hour=config.EXTRA_HOUR, minute=config.EXTRA_MINUTE)
    }
}

bot = Bot(token=config.TELEGRAM_TOKEN)

dp = Dispatcher()

def send_msg(chat_id, text):
    response = requests.post('https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}&disable_web_page_preview=True'.format(
        token = config.TELEGRAM_TOKEN,
        chat_id = chat_id,
        text = text
    ))

@dp.message(Command('start'))
async def start(message: types.message):
    user = {
        'user_id': message.from_user.id,
        'first_name': message.from_user.first_name,
        'sign': ''
    }
    users.delete_one({'user_id': message.from_user.id})
    users.insert_one(user) 
          
    #send_msg(my_id, 'Нажали старт')
    await message.answer('Привет {name}!\nЯ буду присылать ежежневный и еженедельный гороскопы.\nТак же можно узнать вашу любовную совместимость нажав команду\n/compatibility\nВыбери свой знак зодиака!\n '.format(
        name=message.from_user.first_name,
        id = message.from_user.id
    ), reply_markup=get_keyboard_sign())
    

class SignCallbackFactory(CallbackData, prefix="sign"):
    #action: str
    value: Optional[str] = None

class ExtraSignCallbackFactory(CallbackData, prefix="extrasign"):
    #action: str
    value: Optional[str] = None
    key: Optional[str] = None

class PeriodCallbackFactory(CallbackData, prefix="period"):
    #action: str
    value: Optional[str] = None

class CompatibilityCallbackFactory(CallbackData, prefix="compatibility"):
    #action: str
    value: Optional[str] = None
    payload: Optional[str] = None
    
ZODIAC_SIGNS = {
    "aries": '♈ Овен',
    "taurus": '♉ Телец',
    "gemini": '♊ Близнецы',
    "cancer": '♋ Рак',
    "leo": '♌ Лев',
    "virgo": '♍ Дева',
    "libra": '♎ Весы',
    "scorpio": '♏ Скорпион',
    "sagittarius": '♐ Стрелец',
    "capricorn": '♑ Козерог',
    "aquarius": '♒ Водолей',
    "pisces": '♓ Рыбы'
} 

EXTRA_HORO = {
    'hea': 'Здоровье',
    'ero': 'Эротический',
    'bus': 'Деловой'
}

def get_keyboard_extrahoro(horo_dict):    
    builder = InlineKeyboardBuilder()
    for key, value in horo_dict.items():
        builder.button(
            text=value, callback_data=ExtraSignCallbackFactory(key=key, value=value)
        )
    builder.button(
            text='Готово', callback_data=ExtraSignCallbackFactory(value='Done')
        )
    builder.adjust(2)
    return builder.as_markup()

def get_keyboard_sign():    
    builder = InlineKeyboardBuilder()
    for key, value in ZODIAC_SIGNS.items():    
        builder.button(
            text=value, callback_data=SignCallbackFactory(value=key)
        )
    
    builder.adjust(3)
    return builder.as_markup()

def get_keyboard_period():    
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text='На сегодня', callback_data=PeriodCallbackFactory(value='today')
    )
    
    builder.button(
        text='На завтра', callback_data=PeriodCallbackFactory(value='tomorrow')
    )
    
    builder.button(
        text='На неделю', callback_data=PeriodCallbackFactory(value='week')
    )
    
    builder.adjust(3)
    return builder.as_markup()

def get_keyboard_compatibility(payload=None):    
    builder = InlineKeyboardBuilder()
    for key, value in ZODIAC_SIGNS.items():    
        builder.button(
            text=value, callback_data=CompatibilityCallbackFactory(value=key, payload=payload)
        )
    
    builder.adjust(3)
    return builder.as_markup()


@dp.callback_query(SignCallbackFactory.filter())
async def callbacks_num_change_fab(
        callback: types.CallbackQuery, 
        callback_data: SignCallbackFactory
):
    data = {}
    sign = callback_data.value
    data['chat_id'] = callback.from_user.id
    user = users.find({'user_id': callback.from_user.id})[0]
    #user['sign'] = sign.lower()
    users.update_one({'user_id': callback.from_user.id}, {'$set': {'sign': sign}})
    redis_client.hset(str(callback.from_user.id), mapping=EXTRA_HORO)
    await bot.send_message(text='Какие еще гороскопы хотите получать? Выберите один или несколько вариантов и нажмите Готово.', chat_id=callback.from_user.id, reply_markup=get_keyboard_extrahoro(EXTRA_HORO))
    #send_msg(callback.from_user.id, horoscope.get_tooday())
        
    await callback.answer()

@dp.callback_query(ExtraSignCallbackFactory.filter())
async def callbacks_num_change_fab(
        callback: types.CallbackQuery, 
        callback_data: ExtraSignCallbackFactory
):
    
    horo_dict = redis_client.hgetall(str(callback.from_user.id))
    if callback_data.value == 'Done':
        extra = []
        for key, value in horo_dict.items():
            if '✔' in value:
                extra.append(key)
                users.update_one({'user_id': callback.from_user.id}, {'$set': {'extra': extra}})
        await bot.send_message(text='Отлично, я буду присылать гороскоп каждое утро. Также вы можете получить гороскоп прямо сейчас нажав на кнопки ниже или выбрав команду /horoscope. : ', chat_id=callback.from_user.id, reply_markup=get_keyboard_period())
                

    horo_dict[callback_data.key] = '✔ ' + horo_dict[callback_data.key]
    redis_client.hset(str(callback.from_user.id), mapping=horo_dict)
    
    await bot.edit_message_reply_markup(chat_id=callback.from_user.id, message_id=callback.message.message_id, reply_markup=get_keyboard_extrahoro(horo_dict))
        
    await callback.answer()
    
@dp.callback_query(PeriodCallbackFactory.filter())
async def callbacks_num_change_fab(
        callback: types.CallbackQuery, 
        callback_data: PeriodCallbackFactory
):
    
    data = {}
    period = callback_data.value
    data['chat_id'] = callback.from_user.id
    user = users.find({'user_id': callback.from_user.id})[0]
    horoscope = Horoscope(user['sign'])
    send_msg(callback.from_user.id, horoscope.get_main(period))
    extra = horoscope.get_extra(user['extra'], period)
    ext = ''
    for i in extra:
        ext = ext + i + '\n\n'
    send_msg(callback.from_user.id, ext)
        
    await callback.answer()
        
@dp.callback_query(CompatibilityCallbackFactory.filter())
async def callbacks_num_change_fab(
        callback: types.CallbackQuery, 
        callback_data: CompatibilityCallbackFactory
):
    data = {}
    user = users.find({'user_id': callback.from_user.id})[0]
    if callback_data.payload == None:
        female = callback_data.value
        data['chat_id'] = callback.from_user.id

        await bot.send_message(text='Какой знак у мужчины?', chat_id=callback.from_user.id, reply_markup=get_keyboard_compatibility(payload=female))
    else:
        male = callback_data.value
        female = callback_data.payload
        horo = compatibility.find({'title': f'{female}-{male}'})[0]
        percent = horo['percent']
        description = f'<b>Ваша совместимость:</b> {percent}\n'
        for k, v in horo['description'].items():
            description = description + '\n' + f'<b>{k}</b>' +'\n' + v[0] + '\n'
        await bot.send_message(text=description, chat_id=callback.from_user.id, parse_mode='html')
    await callback.answer()
        
@dp.message(Command('horoscope'))
async def horoscope(message: types.message):
    await message.answer('Выбери период', reply_markup=get_keyboard_period())

@dp.message(Command('extra'))
async def horoscope(message: types.message):
    
    redis_client.hset(str(message.from_user.id), mapping=EXTRA_HORO)
    
    await message.answer('Как еще гороскоп вы хотите получать?', reply_markup=get_keyboard_extrahoro(EXTRA_HORO))
    
@dp.message(Command('compatibility'))
async def comand_compatibility(message: types.message):
    await message.answer('Какой знак у женщины?', reply_markup=get_keyboard_compatibility())
    
@client.task()
def send_daily_horoscope():
    for user in users.find():
        horoscope = Horoscope(user['sign'])
        main = 'Ваш гороскоп на сегодня:\n' + horoscope.get_main('today')
        send_msg(user['user_id'], main)
        try:
            extra = horoscope.get_extra(user['extra'], 'today')
            ext = ''
            for i in extra:
                ext = ext + i + '\n\n'
            send_msg(user['user_id'], ext)
        except:
            pass    

@client.task()
def send_weekly_horoscope():
    for user in users.find():
        horoscope = Horoscope(user['sign'])
        main = 'Ваш гороскоп на сегодня:\n' + horoscope.get_main('week')
        send_msg(user['user_id'], main)

def update_db(db_name, document):
    if db_name == 'hea':
        db_hea.delete_one({'sign': document['sign']})
        db_hea.insert_one(document)
    if db_name == 'ero':
        db_ero.delete_one({'sign': document['sign']})
        db_ero.insert_one(document)
    if db_name == 'bus':
        db_bus.delete_one({'sign': document['sign']})
        db_bus.insert_one(document)
    if db_name == 'main':
        db_main.delete_one({'sign': document['sign']})
        db_main.insert_one(document)
        
@client.task()        
def parse_main_horoscope():
    periods = ['today', 'tomorrow', 'week']
    for sign in ZODIAC_SIGNS.keys():
        document = {'sign': sign}
        for period in periods:
            url = f'https://horo.mail.ru/prediction/{sign}/{period}/'
            
            res = parse_page(url, 5)
            document[period] = res
        
        update_db('main', document)

def parse_page(url, count):
    while count > 0:
        try:
            sleep(3)
            page = urllib.request.urlopen(url).read()
            soup = BeautifulSoup(page, 'html.parser')

            data = soup.find('div', attrs={'class': 'article__item article__item_alignment_left article__item_html'})
            p = data.find_all('p')
            res = ''
            for i in p:
                res = res + i.text + '\n\n'
            return res
        except:
            sleep(10)
            parse_page(url, count-1)

@client.task()
def parse_extra_horoscope():
    horo_names = ['hea', 'ero', 'bus']
    for name in horo_names:
        filename = get_horo_from_url(name)
        collection = parse_xml(filename)
        for item in collection:
            update_db(name, item)
        
def get_horo_from_url(name):
    url = f'https://ignio.com/r/export/utf/xml/daily/{name}.xml'
    resp = requests.get(url)
    filename = f'{name}.xml'
    with open(filename, 'wb') as file:
        file.write(resp.content)
    return filename

def parse_xml(filename):
    tree = ET.parse(filename)
    
    root = tree.getroot() 
    collection = []
    for sign in root:
        name = sign.tag
        horo = {
            'sign': name
        }
                
        for day in sign:
            horo[day.tag] = day.text.replace('\n', '')
        collection.append(horo)
    return collection
        
if __name__ == '__main__':
    pass