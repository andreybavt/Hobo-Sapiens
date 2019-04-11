from bs4 import BeautifulSoup
from tornado.httpclient import HTTPRequest

from crawler_utils.utils import *
from notification_sender import Notification
from runner import Filter
from services.abstract_service import AbstractService


class Seloger(AbstractService):
    url = "https://lifemap.seloger.com/lm-api/v2/search/optimalsearch"
    announce_url = 'https://lifemap.seloger.com/lm-api/v2/announces?id='
    # payload = "{\"searchParams\":{\"types\":\"1,2\",\"projects\":\"1\",\"enterprise\":\"0\",\"furnished\":\"1\",\"price\":\"NaN/1300\",\"surface\":\"23/NaN\",\"places\":\"[{ci:750101}|{ci:750102}|{ci:750103}|{ci:750104}]\",\"qsVersion\":\"1.0\"},\"filters\":{\"encodedPolyline\":\"{nhiHe{wL?mca@tlD??lca@ulD?\",\"itemsNumberLimit\":35}}"
    headers = {
        'Origin': "https://www.seloger.com",
        'Accept-Encoding': "gzip, deflate, br",
        'Accept-Language': "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,fr;q=0.6",
        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
        'Content-Type': "application/json",
        'Accept': "*/*",
        'Referer': "https://www.seloger.com/map.htm?types=1%2C2&projects=1&enterprise=0&price=NaN%2F1300&surface=23%2FNaN&places=%5B%7Bci%3A750101%7D%7C%7Bci%3A750102%7D%7C%7Bci%3A750103%7D%7C%7Bci%3A750104%7D%5D&qsVersion=1.0&bd=ListToCarto_SL",
        'Connection': "keep-alive",
        'cache-control': "no-cache"
    }

    def __init__(self, filter: Filter, enable_proxy=None) -> None:
        super().__init__(filter, enable_proxy=None)

        def penalty_fn(e):
            return 5

        self.client.proxy_manager.penalty_fn = penalty_fn

        arr_part = '|'.join(['{ci:' + "7501" + str(e)[-2:] + '}' for e in filter.arrondissements])
        self.list_url = 'https://www.seloger.com/list.htm?types=1,2&projects=1&enterprise=0' \
                        '&furnished=' + ('1' if filter.furnished else '0') + '&price=NaN/' + str(filter.max_price) + \
                        '&surface=' + str(filter.min_area) + '/NaN' \
                                                             '&places=[' + arr_part + ']&qsVersion=1.0&LISTING-LISTpg='

    def get_service_name(self) -> str:
        return "Seloger"

    def get_candidate_native_id(self, pub):
        return pub.get('idannonce')

    async def candidate_to_notification(self, c) -> Notification:
        native_id = self.get_candidate_native_id(c)
        if not native_id:
            return None
        candidate = await self.fetch_by_id(native_id)
        return Notification(
            price=int(read_prop(candidate, 'prixnormal')),
            location=read_prop(candidate, 'ville'),
            area=read_prop(candidate, 'surface'),
            url=self.get_url(candidate),
            pics_urls=read_prop(candidate, 'image'))

    async def run(self):
        res = await self.client.patient_fetch(HTTPRequest(method='GET', url=self.list_url, headers=self.headers),
                                              connect_timeout=4, request_timeout=8)
        resp_text = res.body.decode()
        pages = set([e.text for e in BeautifulSoup(resp_text, 'lxml').select('.pagination-number span')])
        if not len(pages):
            logging.warn("Page list is empty, exiting")
            return
        pages_lists = await asyncio.wait(
            [self.get_page_list(p) for p in pages]
        )
        candidates = [j for e in pages_lists[0] for j in e.result()]
        unseen = await self.filter_out_seen(candidates)
        unseen = [u for u in unseen if self.get_candidate_native_id(u)]
        logging.info(f'found {len(candidates)} items, {len(unseen)} unseen')
        for chunk in chunks(unseen, 10):
            await asyncio.wait(
                [self.push_candidate(c) for c in chunk]
            )

    @nofail_async(retries=50, failback_result={})
    async def fetch_by_id(self, pub_id):
        det_resp = await self.client.patient_fetch(
            HTTPRequest(method='GET', url=self.announce_url + str(pub_id)), connect_timeout=4, request_timeout=8)
        det = json.loads(det_resp.body.decode())
        retries = 10
        images = []
        while retries > 0 and len(images) == 0:
            retries -= 1
            item_page = (
                await self.client.patient_fetch(
                    HTTPRequest(method='GET', url=self.get_url(det), headers=self.headers),
                    connect_timeout=4, request_timeout=8)).body.decode()
            img_els = BeautifulSoup(item_page, 'lxml').select('.carrousel_slide')
            if not len(BeautifulSoup(item_page, 'lxml').select('.photo_form')):
                logging.warning(f'didn\'t find any carrousel_slide: {pub_id}')
                images = []
            else:
                images = ['http://' + json.loads(e['data-lazy'])['url'].strip('/') for e in
                          img_els if 'data-lazy' in e.attrs]
                det['image'] = [f'http://v.seloger.com/s/height/800/visuels{i}' for i in det['imgs']] + images
                break
        return det

    @staticmethod
    def get_url(det):
        return (det['urlann'] if 'seloger.com' in det['urlann'] else 'https://www.seloger.com/' + det[
            'urlann'])

    @nofail_async(retries=10)
    async def get_page_list(self, p):
        res = await self.client.patient_fetch(HTTPRequest(method='GET', url=self.list_url + p, headers=self.headers),
                                              connect_timeout=4, request_timeout=8)
        resp_text = res.body.decode()
        script = [e for e in BeautifulSoup(resp_text, 'lxml').select('script') if '"products" : [' in e.text][
            0].text
        page_list = json.loads(script[script.index('{'):script.rindex('}') + 1])['products']
        return page_list


if __name__ == '__main__':
    pub_filter = Filter(arrondissements=[75001, 75002, 75003, 75004, 75005, 75010, 75011, 75008, 75009],
                        max_price=1300,
                        min_area=25)
    seloger = Seloger(pub_filter)
    asyncio.get_event_loop().run_until_complete(seloger.run())
    print(len(seloger.notifications))
