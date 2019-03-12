import json
import logging
from bs4 import BeautifulSoup
from tornado.httpclient import HTTPRequest

from crawler_utils.utils import chunks, read_prop
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class Laforet(AbstractService):

    def __init__(self, f: Filter) -> None:
        super().__init__(f)

    def get_service_name(self) -> str:
        return "Laforet"

    def get_candidate_native_id(self, candidate):
        return candidate.get('propertyId')

    async def candidate_to_notification(self, c) -> Notification:
        url = "http://www.laforet.com/" + c['ui_el'].find('a')['href']
        res = await self.client.patient_fetch(HTTPRequest(method="GET", url=url), connect_timeout=2, request_timeout=6)
        soup = BeautifulSoup(res.body.decode(), 'lxml')
        return Notification(
            area=read_prop(c, 'surface'),
            location=read_prop(c, 'city', fallback=soup.find(attrs={'class': 'page-header'}).text.strip()),
            price=read_prop(c, 'price'),
            url=url,
            pics_urls=[e['src'] for e in soup.find(attrs={'class': 'cycle-slideshow'}).find_all('img')]
        )

    async def run(self):
        for chunk in chunks(self.filter.arrondissements, 7):
            await self.run_for_arrondissements(chunk)

    async def run_for_arrondissements(self, arrs):
        arr_part = '%2C+'.join([f"Paris+{str(e)[-2:]}+%28{str(e)}%29" for e in arrs])
        url = "http://www.laforet.com/louer/rechercher?slug=&ajaxValue=0" \
              "&localisation=" + arr_part + "&rayon=00" \
                                            "&price_min=0&price_max=" + str(
            self.filter.max_price) + "&surface_min=" + str(
            self.filter.min_area) + "&surface_max=Max&ground_surface=" \
                                    "&maison=on&appartement=on&terrain=on&immeuble=on&bureau=on&local=on" \
                                    "&commerce=on&parkinggaragebox=on&floor_min=&floor_max=&reference=" \
                                    "&type_rech=&url_rech_elargie=&nb_rech_elargie=&est_groupement=&page="

        for page in range(9999):
            current_url = url + str(page)
            get = await self.client.patient_fetch(HTTPRequest(method='GET', url=current_url),
                                                  connect_timeout=2, request_timeout=6)
            soup = BeautifulSoup(get.body.decode(), 'lxml')

            find_all = soup.find_all(attrs={'class', 'js-stats-property-roll'})
            for chunk in chunks(find_all, 10):
                candidates = []
                for c in chunk:
                    cand = json.loads(c['data-json']) if c.has_attr('data-json') else {'propertyId': c['data-id']}
                    cand['ui_el'] = c
                    candidates.append(cand)

                await asyncio.wait([
                    self.push_candidate(c) for c in candidates
                ])

            if soup.find(attrs={'class': 'pagination'}) is None or 'dernière' not in soup.find(
                    attrs={'class': 'pagination'}).text.lower():
                break


if __name__ == '__main__':
    import asyncio

    f = Filter(arrondissements=[75001, 75002, 75003, 75004, 75005, 75010, 75011, 75008, 75009], max_price=1300,
               min_area=25)
    laforet = Laforet(f)
    res = asyncio.get_event_loop().run_until_complete(laforet.run())
    logging.info(res)
