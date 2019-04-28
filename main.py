from flask import Flask, request
import logging
from flask import Flask, request
import logging
from math import sin, cos, sqrt, atan2, radians
import requests
import json

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, filename='app.log', format='%(asctime'
                                                                   ')s %(levelname)s %(name)s %(message)s')

sessionStorage = {}

api_key = "dda3ddba-c9ea-4ead-9010-f4" \
          "3fbc15c6e3"


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)

    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }

    handle_dialog(response, request.json)

    logging.info('Request: %r', response)

    return json.dumps(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']

    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови свое имя!'

        sessionStorage[user_id] = {
            'first_name': None,
            'city': None,
            'address': '',
            'cords': [],
            'points': []
        }
        res['response']['buttons'] = [
            {
                'title': 'Помощь',
                'hide': False
            }
        ]

        return
    if sessionStorage[user_id]['first_name'] is None:
        if 'помощь' == req['request']['nlu']['tokens'][0]:
            res['response']['text'] = get_help(user_id)
            return

        first_name = get_first_name(req)

        if first_name is None:
            res['response']['text'] = \
                'Не расслышала имя. Повтори, пожалуйста!'
            return
        else:
            sessionStorage[user_id]['first_name'] = first_name.title()
            res['response'][
                'text'] = f"Привет, {sessionStorage[user_id]['first_name']}," \
                f" в каком городе вы находитесь?"
            res['response']['buttons'] = [
                {
                    'title': 'Помощь',
                    'hide': False
                }
            ]
            return

    if sessionStorage[user_id]['city'] is None:
        if 'помощь' == req['request']['nlu']['tokens'][0]:
            res['response']['text'] = get_help(user_id)

        city = get_city(req)
        if city is None:
            res['response']['text'] = 'Не могу найти город с таким названием'
            return
        else:
            sessionStorage[user_id]['city'] = city
            # cr = get_cords(city)
            sessionStorage[user_id]['cords'] = [float(i) for i in get_cords(city).split(',')]
            res['response'][
                'text'] = f'Отлично, {sessionStorage[user_id]["first_name"].title()}.' \
                f' Теперь ты можешь найти нужное тебе место! \n ' \
                f'Поиск будет проводиться от центра города \n ' \
                f'Вы также можете уточнить свое местоположение написав' \
                f' "Добавь адрес [адрес]" или ' \
                f'найти какой либо объект командой "Найди [объект]"'
            res['response']['buttons'] = [
                {
                    'title': 'Помощь',
                    'hide': False
                }
            ]

    if 'помощь' == req['request']['nlu']['tokens'][0]:
        res['response']['text'] = get_help(user_id)

    if len(req['request']['nlu']['tokens']) >= 2 and 'добавь' == req['request']['nlu']['tokens'][0] and 'адрес' \
            == req['request']['nlu']['tokens'][1]:

        address = ' '.join(req['request']['nlu']['tokens'][2:])

        if address:
            geocoder_request = "http://geocode-maps.yandex.ru/1.x/?geocode={}" \
                               "&format=json".format(sessionStorage[user_id]['city'] + ', ' + address)
            response = requests.get(geocoder_request)
            if response:
                json_response = response.json()
                toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
                cords = [float(i) for i in toponym["Point"]["pos"].split()]

                kind = toponym['metaDataProperty']['GeocoderMetaData']['kind']

                if kind == 'house':
                    sessionStorage[user_id]['address'] = address
                    sessionStorage[user_id]['cords'] = cords
                    res['response']['text'] = "Адрес успешно изменен"
                    res['response']['buttons'] = [
                        {
                            'title': 'Помощь',
                            'hide': False
                        }
                    ]
                    return
                else:
                    res['response']['text'] = "По этому адресу нет дома."
                    res['response']['buttons'] = [
                        {
                            'title': 'Помощь',
                            'hide': False
                        }
                    ]
                    return

    elif 'найди' == req['request']['nlu']['tokens'][0]:

        if len(req['request']['nlu']['tokens']) > 1:
            cords = get_cords(sessionStorage[user_id]['city'] + ', ' + sessionStorage[user_id]['address'])
            search = "https://search-maps.yandex.ru/v1/"

            search_params = {
                "apikey": 'dda3ddba-c9ea-4ead-9010-f43fbc15c6e3',
                "text": ' '.join(req['request']['nlu']['tokens'][1:]),
                "lang": "ru_RU",
                "type": "biz",
                "ll": cords
            }

            response = requests.get(search, params=search_params)

            if not response:
                res['response']['text'] = "Мне не удалось найти ни одной организации"
                res['response']['buttons'] = [
                    {
                        'title': 'Помощь',
                        'hide': False
                    }
                ]
            else:

                response = response.json()

                if len(response['features']) > 1:

                    object = response['features'][0]
                    address = object['properties']['CompanyMetaData']['address']
                    cords = object['geometry']['coordinates']
                    name = object['properties']['CompanyMetaData']['name']
                    distance = get_distance(sessionStorage[user_id]['cords'], cords)
                    res['response']['text'] = f'Название: {name} \n' \
                        f'Адрес: {address} \n' \
                        f'Расстояние: {distance} км.'
                else:

                    res['response']['text'] = "Я не смогла найти не одного объекта"
                    res['response']['buttons'] = [
                        {
                            'title': 'Помощь',
                            'hide': False
                        }
                    ]

        else:

            res['response']['text'] = "Вы не ввели название места"
            res['response']['buttons'] = [
                {
                    'title': 'Помощь',
                    'hide': False
                }
            ]


def get_help(user_id):

    if sessionStorage[user_id]['first_name'] is None:
        return "Назовите своё имя, сударь"

    elif sessionStorage[user_id]['city'] is None:
        return "Назовите свой город"
    else:
        return 'Вы также можете уточнить свое местоположение написав "Добавь адрес [адрес]" \n ' \
               " Например: Добавь адрес Чичерина 27\n " \
               "В адресе должен быть обязательно указан дом \n" \
               "Для поиска объектов напишите в " \
               " таком формате:Найди (объект) \n" \
               "Например: Найди аптеку \n " \


def get_cities(req):
    for entity in req['request']['nlu']['entities']:

        if entity['type'] == 'YANDEX.GEO':

            if 'city' in entity['value'].keys():
                return entity['value']['city']


def get_city(req):
    for entity in req['request']['nlu']['entities']:

        if entity['type'] == 'YANDEX.GEO':
            if 'city' in entity['value'].keys():
                return entity['value']['city']


def get_first_name(req):
    # перебираем сущности
    for entity in req['request']['nlu']['entities']:
        # находим сущность с типом 'YANDEX.FIO'
        if entity['type'] == 'YANDEX.FIO':
            # Если есть сущность с ключом 'first_name',
            # то возвращаем ее значение.
            # Во всех остальных случаях возвращаем None.
            return entity['value'].get('first_name', None)


def get_cords(place):
    geocoder_request = "http://geocode-maps.yandex.ru/1.x/?geocode={}&format=json".format(place)
    try:
        response = requests.get(geocoder_request)
        if response:
            json_response = response.json()
            toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["Point"]["pos"]
            cords = ','.join(toponym.split())
            return cords
        else:
            return None
    except:
        return None
    return cords


def get_geo_info(city_name, type_info):
    url = "https://geocode-maps.yandex.ru/1.x/"

    params = {
        'geocode': city_name,
        'format': 'json'
    }
    response = requests.get(url, params)
    json = response.json()
    if type_info == 'country':
        return \
            json['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['metaDataProperty'][
                'GeocoderMetaData'][
                'AddressDetails']['Country']['CountryName']

    elif type_info == 'coordinates':
        point_str = json['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
        point_array = [float(x) for x in point_str.split(' ')]

        return point_array


def get_distance(p1, p2):
    R = 6373.0

    lon1 = radians(float(p1[0]))
    lat1 = radians(float(p1[1]))
    lon2 = radians(float(p2[0]))
    lat2 = radians(float(p2[1]))

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    return distance


if __name__ == '__main__':
    app.run()
