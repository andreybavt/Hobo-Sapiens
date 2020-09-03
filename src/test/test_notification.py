from notification_sender import Notification


def test_notification():
    n1 = Notification(
        id="one",
        source="source_one",
        price=1.23,
        location="loc_one",
        area=3.21,
        url="url_one",
        pics_urls=["pic_one"]
    )
    n2 = Notification(
        id="one",
        source="source_two",
        price=2.23,
        location="loc_two",
        area=1.21,
        url="url_two",
        pics_urls=["pic_two"]
    )

    assert n1 == n2, "Assert equals"
    assert hash(n1) == hash(n2), "Assert hash"