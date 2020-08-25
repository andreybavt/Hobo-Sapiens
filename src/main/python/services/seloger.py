from tornado.httpclient import HTTPRequest

from crawler_utils.utils import *
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class Seloger(AbstractService):
    url = "https://api-seloger.svc.groupe-seloger.com/api/v1/listings/search"

    headers = {
        'apptoken': None,
        'appguid': '63ee714d-a62a-4a27-9fbe-40b7a2c318e4',
        'accept': 'application/json',
        'content-type': 'application/json',
        'user-agent': 'okhttp/4.2.2',
    }

    def get_service_name(self) -> str:
        return "Seloger"

    def get_candidate_native_id(self, pub):
        return pub.get('id')

    async def candidate_to_notification(self, c) -> Notification:
        return Notification(
            price=c.get('price'),
            location=c.get('zipCode'),
            area=c.get('livingArea'),
            url=c.get('permalink'),
            pics_urls=c.get('photos'))

    def arr_to_searr(self, arr):
        return 750100 + arr - 75000

    def init_auth_token(self):
        import requests
        seloger_token_host = os.environ.get('HS_SELOGER_TOKEN_HOST', 'localhost')
        seloger_token_port = os.environ.get('HS_SELOGER_TOKEN_PORT', '8001')
        token = requests.get(f'http://{seloger_token_host}:{seloger_token_port}/seloger-auth').text
        self.headers['apptoken'] = token
        token = requests.get('https://api-seloger.svc.groupe-seloger.com/api/v1/security/authenticate',
                             headers=self.headers).text
        self.headers['apptoken'] = token[1:-1]
        self.logger.info(f"Initialized token: {token}")

    def data(self, page):
        res = {"pageSize": 50,
               "pageIndex": page,
               "query": {"realtyTypes": 3,
                         "minimumLivingArea": self.filter.min_area,
                         "sortBy": 0,
                         "maximumPrice": self.filter.max_price,
                         "transactionType": 1,
                         "inseeCodes": [str(self.arr_to_searr(i)) for i in self.filter.arrondissements]},
               }
        if self.filter.furnished:
            res['query']["furnishing"] = 1
        return res

    async def run(self):
        self.init_auth_token()

        for page in range(1, 10):
            res = await self.client.patient_fetch(
                HTTPRequest(method="POST", url=self.url, body=json.dumps(self.data(page)), headers=self.headers))
            res_json = res.json()
            for c in res_json['items']:
                await self.push_candidate(c)
            if page == res_json['pageCount']:
                break


if __name__ == '__main__':
    pub_filter = Filter(arrondissements=[75001],
                        furnished=True,
                        max_price=1300,
                        min_area=25)
    seloger = Seloger(pub_filter, False)
    asyncio.get_event_loop().run_until_complete(seloger.run())