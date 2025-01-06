import requests
from fake_useragent import UserAgent
import logging
from config import BASE_URL

ua = UserAgent()

def get_headers():
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "es,es-ES;q=0.9",
        "Connection": "keep-alive",
        "DeviceOS": "0",
        "User-Agent": ua.random,
        "X-DeviceOS": "0"
    }
    return headers

def get_listing(*, max_price:int = 200, category_id: int = 24200, offset: int = 0):
    logging.info(f'Getting wallapop listing {locals()}')
    try:
        res = requests.get(f'{BASE_URL}?offset={offset}&category_ids={category_id}&max_sale_price={max_price}', headers=get_headers()) # keywords=airpods
        # a = requests.get('https://api.wallapop.com/api/v3/search?source=api&category_ids=24200', headers=headers) # EL QUE USA WALLAPOP EN LA PÁGINA
        res.raise_for_status()
        return res.json()['search_objects']
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from Wallapop API: {e}")
        return None
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error fetching data from Wallapop API: {e}")
        return None
    
def search_keywords(keywords: str, offset:int = 0):
    logging.info(f'Searching in wallapop keywords {locals()} {keywords}')
    try:
        res = requests.get(f'{BASE_URL}?keywords={keywords}&offset={offset}', headers=get_headers())
        return res.json()['search_objects']
    except requests.exceptions.RequestException as e:
        logging.error(f"Error searching keywords in Wallapop API: {e}")
        return None
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error searching keywords from Wallapop API: {e}")
        return None