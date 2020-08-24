import asyncio
import tempfile
from pathlib import Path

from runner import Filter
from services.abstract_service import AbstractService
from services.avendre_alouer import AvendreAlouer
from services.bienici import BienIci
from services.century21 import Century21
from services.figaro import Figaro
from services.laforet import Laforet
from services.leboncoin import LeBonCoin
from services.logicimmo import LogicImmo
from services.orpi import Orpi
from services.pap import Pap
from services.seloger import Seloger


def test_logicimmo():
    smoke_test(LogicImmo)


def test_century21():
    smoke_test(Century21)


def test_avendre_alouer():
    smoke_test(AvendreAlouer)


def test_bienici():
    smoke_test(BienIci)


def test_figaro():
    smoke_test(Figaro)


def test_leboncoin():
    smoke_test(LeBonCoin)


def test_pap():
    smoke_test(Pap)


def test_orpi():
    smoke_test(Orpi)


def test_seloger():
    smoke_test(Seloger)


def test_laforet():
    smoke_test(Laforet)


from typing import Type


def smoke_test(service_class: Type[AbstractService]):
    filter = Filter(arrondissements=[75018], max_price=1500, min_area=27)
    service = service_class(filter, False, Path(tempfile.mkdtemp(prefix='hobo-sapiens-listings')))

    asyncio.get_event_loop().run_until_complete(service.main_run())
    assert len(service.notifications) > 0
    has_area = False
    has_id = False
    has_location = False
    has_pics_urls = False
    has_price = False
    has_source = False
    has_url = False

    for n in service.notifications:
        has_area = has_area or (n.area is not None)
        has_id = has_id or (n.id is not None)
        has_location = has_location or (n.location is not None)
        has_pics_urls = has_pics_urls or (n.pics_urls is not None)
        has_price = has_price or (n.price is not None)
        has_source = has_source or (n.source is not None)
        has_url = has_url or (n.url is not None)

    assert has_area
    assert has_id
    assert has_location
    assert has_pics_urls
    assert has_price
    assert has_source
    assert has_url
