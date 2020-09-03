import logging
import traceback
from io import BytesIO
from os import environ
from typing import List

from attr import dataclass
from prometheus_client.metrics import Counter, Histogram
from telegram import InputMediaPhoto
from telegram.ext import Updater

from crawler_utils.utils import chunks, nofail
from image_manager import ImageManager

@dataclass(eq=False)
class Notification(object):
    price: float
    location: str
    area: float
    url: str
    pics_urls: List[str]
    floor: int = None
    description: str = None
    rooms: int = None
    id: str = None
    source: str = None

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, o: object) -> bool:
        return isinstance(o, Notification) and o.id == self.id


class NotificationSender:
    logger = logging.getLogger(__name__)
    METRICS_NOTIFICATION_TIME = Histogram("notification_send_time_sec", "Time to send notification", ['type'])
    METRICS_NOTIFICATION_COUNT = Counter("notification_counter", "Number of sent notifications", ['service'])

    def __init__(self) -> None:
        self.image_manager = ImageManager()
        self.updater = Updater(token=environ.get('HS_TELEGRAM_BOT_TOKEN'),
                               request_kwargs={"connect_timeout": 60., "read_timeout": 60.}, use_context=True)

    def send_to_chat(self, notif: Notification):
        try:
            price_per_m = int(notif.price / notif.area)
        except Exception:
            price_per_m = None

        desc = f'{notif.id}\nPrice: {notif.price} ({price_per_m}/m2)\nArea: {notif.area}\nWhere: {notif.location}\nURL: {notif.url}\n{notif.description}'
        desc = desc[:4090]
        self.METRICS_NOTIFICATION_COUNT.labels(notif.source).inc()
        chat_id = environ.get('HS_TELEGRAM_CHAT_ID')
        reference_message = None
        if not notif.pics_urls:
            return
        new_images = []
        try:
            for c in chunks(notif.pics_urls, 10):
                new_images, seen_in_messages = self.image_manager.check_all(notif, c)
                seen_in = None if not len(seen_in_messages) else seen_in_messages.pop()
                reference_message = None if not seen_in else seen_in.get('message_id')
                if reference_message:
                    self.logger.info(f"Found photo duplicates: {notif.url} vs. {seen_in['notif'].url}")
                if len(new_images):
                    self.logger.info(f"Sending {len(new_images)} images")
                    send_pic_res = self._send_pics(new_images, chat_id, desc,
                                                   reply_to_message_id=reference_message)
                    if send_pic_res and hasattr(send_pic_res[0], 'message_id'):
                        self.image_manager.set_message_ids([v['hash'] for v in new_images.values()],
                                                           send_pic_res[0].message_id)

        except Exception as e:
            self.logger.error(e, traceback.format_exc())

        if len(new_images):
            self._send_message(chat_id, desc, reference_message=reference_message)
        else:
            self.logger.info("No new images found, not sending the message")  # TODO: check if price has changed

    @nofail(retries=20, sleep=1, failback_result=None)
    def _send_message(self, chat_id, desc, reference_message=None):
        with self.METRICS_NOTIFICATION_TIME.labels('message').time():
            log_msg = desc.replace('\n', '; ')
            self.logger.info(f"Sending message: {chat_id} {log_msg} {reference_message} ")

            self.updater.bot.send_message(chat_id, desc, timeout=20 * 60, disable_web_page_preview=True,
                                          reply_to_message_id=reference_message,
                                          disable_notification=reference_message is not None)

    @nofail(retries=20, sleep=1, failback_result=None)
    def _send_pics(self, c, chat_id, desc, **kwargs):
        with self.METRICS_NOTIFICATION_TIME.labels('pics').time():
            return self.updater.bot.send_media_group(chat_id,
                                                     [InputMediaPhoto(BytesIO(i['image']), caption=desc) for i in
                                                      c.values()],
                                                     timeout=20 * 60, disable_notification=True, **kwargs)
