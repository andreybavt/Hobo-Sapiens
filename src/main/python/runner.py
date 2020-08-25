import asyncio
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import List

from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Filter:
    arrondissements: List[str]
    max_price: float
    min_area: float
    furnished: bool


if __name__ == '__main__':
    assert len(sys.argv) > 1, 'Path to filter.json is required'
    filter_path = Path(os.getcwd()).joinpath(sys.argv[1])

    if not os.environ.get('HS_TELEGRAM_BOT_TOKEN'):
        raise Exception('Environment variable HS_TELEGRAM_BOT_TOKEN should be set to telegram bot token')

    if not os.environ.get('HS_TELEGRAM_CHAT_ID'):
        raise Exception('Environment variable HS_TELEGRAM_CHAT_ID should be set to destination chat id')

    from services.bienici import BienIci
    from services.pap import Pap
    from notification_sender import NotificationSender
    from services.seloger import Seloger
    from services.laforet import Laforet
    from services.leboncoin import LeBonCoin
    from services.figaro import Figaro
    from services.avendre_alouer import AvendreAlouer
    from services.century21 import Century21
    from services.orpi import Orpi

    from services.logicimmo import LogicImmo

    notification_sender = NotificationSender()

    with open(filter_path, 'r') as f:
        pub_filter = Filter.from_json(f.read())

    service_classes = [
        Seloger,
        Orpi,
        AvendreAlouer,
        BienIci,
        Century21,
        Figaro,
        Laforet,
        LeBonCoin,
        LogicImmo,
        Pap
    ]
    services = [s(pub_filter, False) for s in service_classes]
    loop = asyncio.get_event_loop()
    while True:
        last_run = time.time()
        for service in services:
            try:
                loop.run_until_complete(service.main_run())
            except Exception as e:
                logging.error(e, traceback.format_exc())
            for (i, n) in enumerate(service.notifications):
                if not n.pics_urls or not len(n.pics_urls):
                    continue
                logging.info(
                    f"Sending notification {i + 1} of {len(service.notifications)} for {service.get_service_name()}")
                notification_sender.send_to_chat(n)
                service.seen_ids.add(n.id, None)
                time.sleep(0.5)
        logging.info("Done loop, next run in 20 min")
        time.sleep(60*10)
