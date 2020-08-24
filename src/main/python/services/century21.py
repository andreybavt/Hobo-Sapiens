import asyncio
import math
import re

from bs4 import BeautifulSoup
from tornado.httpclient import HTTPRequest

from crawler_utils.utils import chunks
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class Century21(AbstractService):

    def get_candidate_native_id(self, candidate) -> str:
        return candidate['data-uid']

    async def candidate_to_notification(self, candidate) -> Notification:
        url = f"https://www.century21.fr/trouver_logement/detail/{self.get_candidate_native_id(candidate)}"
        resp = await self.client.patient_fetch(HTTPRequest(method="GET", url=url))
        soup = BeautifulSoup(resp.body.decode(), 'lxml')

        return Notification(
            price=soup.select_one('.tarif b').text.strip(),
            area=re.search('(\d|,)*? m²', candidate.select('.tw-text-sm')[1].text.strip()).group(0),
            location=candidate.select('.tw-text-sm')[0].text.strip(),
            url=f"https://www.century21.fr{candidate.select_one('a')['href']}",
            pics_urls=[f"https://www.century21.fr{i['href']}" for i in soup.select('.zone-galerie a[href]')]
        )

    async def run(self):
        candidates, first_page = await self.get_page()
        nb_els = int(re.findall('\d+',first_page.select_one('#bloc_liste_biens .titreSeparation').text)[0])
        page_cnt = math.ceil(nb_els / 30)
        if page_cnt > 1:
            kk = [z for i in range(2, page_cnt + 1) for z in (await self.get_page(i))[0]]
            candidates.extend(kk)

        for chunk in chunks(candidates, 10):
            await asyncio.wait([self.push_candidate(c) for c in chunk])

    async def get_page(self, page=1):
        url = "https://www.century21.fr/annonces/location-appartement/cp-" + '-'.join(
            [str(i) for i in
             self.filter.arrondissements]) + f"/s-{self.filter.min_area}-/st-0-/b-0-{self.filter.max_price}/page-{page}/"
        r = await self.client.patient_fetch(HTTPRequest(method="GET", url=url))
        page = BeautifulSoup(r.body.decode(), 'lxml')
        announces = page.select('#blocANNONCES .annoncesListeBien')[0].select('.annonce .contentAnnonce')
        return announces, page


if __name__ == '__main__':
    f = Filter(arrondissements=[75013], max_price=2000,
               min_area=25)
    service = Century21(f, False)
    asyncio.get_event_loop().run_until_complete(service.run())