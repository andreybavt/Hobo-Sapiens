import asyncio
import time

import os


class Filter:
    def __init__(self, arrondissements, max_price, min_area, furnished=None) -> None:
        super().__init__()
        self.arrondissements = arrondissements
        self.max_price = max_price
        self.min_area = min_area
        self.furnished = furnished


if __name__ == '__main__':
    if not os.environ.get('AF_TELEGRAM_BOT_TOKEN'):
        raise Exception('Environment variable AF_TELEGRAM_BOT_TOKEN should be set to telegram bot token')

    if not os.environ.get('AF_TELEGRAM_CHAT_ID'):
        raise Exception('Environment variable AF_TELEGRAM_CHAT_ID should be set to destination chat id')

    from services.pap import Pap
    from notification_sender import NotificationSender
    from services.seloger import Seloger
    from services.laforet import Laforet
    from services.leboncoin import LeBonCoin

    notification_sender = NotificationSender()

    pub_filter = Filter(arrondissements=[75001, 75002, 75003, 75004, 75005, 75010, 75011, 75008, 75009],
                        max_price=1300,
                        min_area=25)

    services = [Seloger(pub_filter), Laforet(pub_filter), LeBonCoin(pub_filter), Pap(pub_filter)]
    loop = asyncio.get_event_loop()
    while True:
        last_run = time.time()
        for service in services:
            loop.run_until_complete(service.main_run())
            for n in service.notifications:
                notification_sender.send_to_chat(n)
                time.sleep(1)
                loop.run_until_complete(service.seen_ids.add(n.id))
        time.sleep(max(60 * 5 - (time.time() - last_run), 0))
