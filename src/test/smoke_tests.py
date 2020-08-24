import asyncio

import pytest

from runner import Filter
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


@pytest.fixture
def filter_stub():
    return Filter(arrondissements=[75018], max_price=1500, min_area=27)


def test_logicimmo(filter_stub):
    smoke_test(LogicImmo(filter_stub, False))


def test_century21(filter_stub):
    smoke_test(Century21(filter_stub, False))


def test_avendre_alouer(filter_stub):
    smoke_test(AvendreAlouer(filter_stub, False))


def test_bienici(filter_stub):
    smoke_test(BienIci(filter_stub, False))


def test_figaro(filter_stub):
    smoke_test(Figaro(filter_stub, False))


def test_leboncoin(filter_stub):
    smoke_test(LeBonCoin(filter_stub, False))


# HARD - maybe also Seloger?
# def test_meilleursagents(filter_stub):
#     from services.meilleursagents import MeilleursAgents
#     smoke_test(MeilleursAgents(filter_stub, False))


def test_pap(filter_stub):
    smoke_test(Pap(filter_stub, False))


def test_orpi(filter_stub):
    smoke_test(Orpi(filter_stub, False))


def test_seloger(filter_stub):
    smoke_test(Seloger(filter_stub, False))


def test_laforet(filter_stub):
    smoke_test(Laforet(filter_stub, False))


def smoke_test(service):
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
