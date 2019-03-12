import asyncio

import json
import logging
import re
from tornado.httpclient import HTTPRequest
from tornado.httputil import url_concat

from crawler_utils.utils import read_prop
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class LeBonCoin(AbstractService):

    def get_service_name(self) -> str:
        return "LeBonCoin"

    def get_candidate_native_id(self, candidate):
        return candidate['list_id']

    async def candidate_to_notification(self, candidate) -> Notification:
        return Notification(
            price=candidate.get('price')[0],
            location=read_prop(candidate, 'location', 'zipcode'),
            area={e['key']: e['value'] for e in candidate['attributes']}.get('square'),
            url=candidate.get('url'),
            pics_urls=read_prop(candidate, 'images', 'urls_large')
        )

    async def run(self):
        url = "https://www.leboncoin.fr/recherche/"
        headers = {
            'Connection': "keep-alive",
            'Pragma': "no-cache",
            'Cache-Control': "no-cache",
            'Upgrade-Insecure-Requests': "1",
            'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36",
            'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            'Accept-Encoding': "gzip, deflate, br",
            'Accept-Language': "ru-RU,ru;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
            'cache-control': "no-cache"
        }
        for page in range(9999):
            querystring = {"category": "10",
                           "locations": ','.join([f'Paris_{e}' for e in self.filter.arrondissements]),
                           "square": f"{self.filter.min_area}-max",
                           "price": f"min-{self.filter.max_price}",
                           "page": page
                           }

            response = await self.client.patient_fetch(
                HTTPRequest(method='GET', url=url_concat(url, querystring), headers=headers))
            content = response.body.decode()
            match_pos = re.search(r'FLUX_STATE = (.+)', content).regs[1]
            match_string = content[match_pos[0]:match_pos[1]]
            data = json.loads(match_string)['adSearch']['data']
            if 'Aucune annonce de particulier n’a été trouvée' in content:
                break
            ads = data.get('ads', []) + data.get('ads_alu', [])
            for c in ads:
                await self.push_candidate(c)


if __name__ == '__main__':
    f = Filter(arrondissements=[75001, 75002, 75003], max_price=1300, min_area=25)
    coin = LeBonCoin(f)
    res = asyncio.get_event_loop().run_until_complete(coin.run())
    logging.info(res)
