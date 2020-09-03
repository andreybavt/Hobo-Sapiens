import asyncio
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from tornado.httpclient import HTTPRequest

from crawler_utils.utils import chunks
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class Figaro(AbstractService):
    headers = {
        'Accept': 'application/vnd.com.explorimmo.iclassifieds-v2+xml',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.1; Android SDK built for x86 Build/NYC)',
        'Connection': 'Keep-Alive'
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        with self.METRICS_INIT_TIME.time():
            self.locations = self.search_locations()

    def get_candidate_native_id(self, cid) -> str:
        return cid

    async def candidate_to_notification(self, cid):
        url = f"https://immobilier.lefigaro.fr/annonces/annonce-{cid}.html"
        resp = await self.client.patient_fetch(
            HTTPRequest(method="GET",
                        url=f"https://immobilier.lefigaro.fr/rest/iClassified?id={cid}"))
        info = BeautifulSoup(resp.body.decode(), 'lxml')
        price = info.select_one('price').text
        if float(price) > self.filter.max_price:
            return
        return Notification(price=price,
                            location=info.select_one('localisation postalcode').text,
                            area=info.select_one('characteristics surface').text,
                            url=url,
                            pics_urls=[i['url'].replace('img/l', 'img/xxl') for i in info.select('photos photo')],
                            description=info.select_one('description').text.strip(),
                            rooms=int(info.select_one('nbrooms').text),
                            floor=info.select_one('floor').text)

    async def run(self):
        for page in range(1, 50):
            nb_notif_before = len(self.notifications)
            candidates_ids = await self.fetch_ids_from_page(page)
            for c in chunks(candidates_ids, 2):
                await asyncio.wait([
                    self.push_candidate(i) for i in c
                ])

            nb_notif_after = len(self.notifications)
            if nb_notif_before == nb_notif_after:
                break

    async def fetch_ids_from_page(self, page=1):
        results_per_page = 50
        data = {'excludeNew': 'false',
                'localisation': self.locations,
                'newOnly': 'false',
                'orderBy': 'dateDesc',
                'propertyType': 'APPARTEMENT,CHAMBRE,MAISON',
                'page': page,
                'priceMax': self.filter.max_price,
                'resultNumber': results_per_page,
                'roomMin': '1',
                'surfaceMin': self.filter.min_area,
                'transaction': 'LOCATION',
                'withPictures': 'true'}
        if self.filter.furnished:
            data['furnished'] = True

        url = "https://immobilier.lefigaro.fr/rest/iClassifieds?"

        url_with_params = url + urlencode(data)
        import requests
        get = requests.get(url_with_params)

        response = await self.client.patient_fetch(
            HTTPRequest(method="GET", url=url_with_params, headers=self.headers))
        soup = BeautifulSoup(response.body.decode('latin-1'), 'lxml')
        return [i.select_one('id').text for i in soup.select('classified')]

    def search_locations(self):
        return ','.join([f'PARIS {int(str(i)[-2:])}{"ER" if str(i) == "75001" else "EME"} ({i})' for i in
                         self.filter.arrondissements])

    def create_candidate(self, i):
        return Notification(id=i['data-classified-id'],
                            location=i['data-agency-postal-code'],
                            price=i.select('.price-label')[0].text.strip().split('\n')[0])


if __name__ == '__main__':
    f = Filter(arrondissements=[75018], max_price=1500, min_area=27)
    figaro = Figaro(f, False)
    asyncio.get_event_loop().run_until_complete(figaro.run())
