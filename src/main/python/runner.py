import asyncio
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import List, Union

from dataclasses import dataclass
from dataclasses_json import dataclass_json
from prometheus_client import start_http_server, Gauge, Counter


@dataclass_json
@dataclass
class Filter:
    arrondissements: List[Union[str, int]]
    max_price: float
    min_area: float
    furnished: bool = None


SCRAPE_INTERVAL_MIN = os.environ.get('HS_SCRAPE_INTERVAL_MINS', 10)


def init_services():
    from services.bienici import BienIci
    from services.pap import Pap
    from services.seloger import Seloger
    from services.laforet import Laforet
    from services.leboncoin import LeBonCoin
    from services.figaro import Figaro
    from services.avendre_alouer import AvendreAlouer
    from services.century21 import Century21
    from services.orpi import Orpi
    from services.logicimmo import LogicImmo
    service_classes = [
        Orpi,
        AvendreAlouer,
        BienIci,
        Century21,
        Figaro,
        Laforet,
        LeBonCoin,
        LogicImmo,
        Pap,
        Seloger,
        # DummyService
    ]
    METRIC_NB_SERVICES.set(len(service_classes))
    return [s(current_filter, False) for s in service_classes]


if __name__ == '__main__':
    METRIC_NB_SERVICES = Gauge('nb_available_services', 'Description of gauge')
    METRICS_RUN_COUNT = Counter('nb_runs', 'Number of global runs')

    # Start prometheus exporter
    start_http_server(5000)

    assert len(sys.argv) > 1, 'Path to filter.json is required'
    filter_path = Path(os.getcwd()).joinpath(sys.argv[1])

    if not os.environ.get('HS_TELEGRAM_BOT_TOKEN'):
        raise Exception('Environment variable HS_TELEGRAM_BOT_TOKEN should be set to telegram bot token')

    if not os.environ.get('HS_TELEGRAM_CHAT_ID'):
        raise Exception('Environment variable HS_TELEGRAM_CHAT_ID should be set to destination chat id')

    from notification_sender import NotificationSender

    notification_sender = NotificationSender()
    loop = asyncio.get_event_loop()

    last_filter = None
    while True:
        last_run = time.time()

        with open(filter_path, 'r') as f:
            current_filter = Filter.from_json(f.read())
            if not last_filter or last_filter.to_json() != current_filter.to_json():
                logging.info("Detected filter change")
                services = init_services()
                last_filter = current_filter

        for service in services:
            try:
                loop.run_until_complete(service.main_run())
            except Exception as e:
                logging.error(e, traceback.format_exc())
            for (i, n) in enumerate(service.notifications):
                if not n.pics_urls or not len(n.pics_urls):
                    continue
                logging.info(
                    f"Sending notification {i + 1} of {len(service.notifications)} for {service.get_service_name()} : {n.id}")
                notification_sender.send_to_chat(n)
                service.seen_ids.add(n.id, None)
                time.sleep(0.5)
        sleep_until_next_run_sec = max(int(60 * SCRAPE_INTERVAL_MIN - (time.time() - last_run)), 0)

        logging.info(f"Done loop, next run in {sleep_until_next_run_sec} sec")
        METRICS_RUN_COUNT.inc()
        time.sleep(sleep_until_next_run_sec)
