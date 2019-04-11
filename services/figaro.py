import asyncio
import math

import logging
from bs4 import BeautifulSoup
from tornado.httpclient import HTTPRequest
from urllib.parse import urlencode

from crawler_utils.utils import chunks
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class Figaro(AbstractService):

    def __init__(self, f: Filter, enable_proxy=None) -> None:
        super().__init__(f, enable_proxy)

    def get_service_name(self) -> str:
        return "Figaro"

    def get_candidate_native_id(self, candidate) -> str:
        return candidate.id

    async def candidate_to_notification(self, candidate) -> Notification:
        url = f"https://immobilier.lefigaro.fr/annonces/annonce-{candidate.id}.html"
        res = await self.client.patient_fetch(
            HTTPRequest(method="GET", url=url))
        soup = BeautifulSoup(res.body.decode('latin-1'), 'lxml')
        images = [i['src'] for i in
                  soup.select('#js-container-main > div.container-player > div div > a > img')]
        return Notification(price=candidate.price,
                            location=candidate.location,
                            area=[i.text for i in soup.select('.list-features li') if 'm²' in i.text][0].strip(),
                            url=url,
                            pics_urls=images)

    async def run(self):
        first_page_ids, nb_of_els = await self.fetch_ids_from_page()
        nb_pages = math.ceil(nb_of_els / 35)
        if nb_pages > 1:
            other_pages_ids = [i for tup in
                               (await asyncio.wait([self.fetch_ids_from_page(i) for i in range(2, nb_pages + 1)]))[0]
                               for
                               i
                               in tup.result()[0]]
        else:
            other_pages_ids = []

        candidates_ids = [i for i in set(first_page_ids + other_pages_ids) if i]
        for c in chunks(candidates_ids, 20):
            await asyncio.wait([
                self.push_candidate(i) for i in c
            ])

    async def fetch_ids_from_page(self, page=1):
        url = "https://immobilier.lefigaro.fr/annonces/resultat/annonces.html?"
        querystring = {"transaction": "location", "location": ','.join([str(i) for i in self.filter.arrondissements]),
                       "priceMax": self.filter.max_price,
                       "areaMin": self.filter.min_area,
                       "page": page,
                       "type": ",".join(
                           ["appartement", "atelier", "chambre", "chambre d hote", "duplex", "loft", "chalet",
                            "chateau", "ferme", "gite", "hotel", "hotel particulier", "maison", "manoir", "moulin",
                            "peniche", "propriete", "villa"])}
        if self.filter.furnished is not None:
            querystring["furnished"] = "true"
        response = await self.client.patient_fetch(HTTPRequest(method="GET", url=url + urlencode(querystring)))
        soup = BeautifulSoup(response.body.decode('latin-1'), 'lxml')
        nb_of_els = int(soup.select('.counter strong')[0].text.strip())

        return [self.create_candidate(i) for i in soup.select('[data-agency-postal-code]')], nb_of_els

    def create_candidate(self, i):
        return Notification(id=i['data-classified-id'],
                            location=i['data-agency-postal-code'],
                            price=i.select('.price-label')[0].text.strip().split('\n')[0])


if __name__ == '__main__':
    f = Filter(arrondissements=[75001, 75002, 75003], max_price=1300, min_area=25)
    figaro = Figaro(f, False)
    asyncio.get_event_loop().run_until_complete(figaro.run())
    logging.info(figaro.notifications)
