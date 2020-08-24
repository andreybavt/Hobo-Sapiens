import asyncio
import tempfile

import pytest

from image_manager import ImageManager


@pytest.fixture
def instance():
    return ImageManager(tempfile.mkdtemp(prefix='hobo-sapiens__image-hash'))


def test_hash_function(instance: ImageManager):
    _test_hash(instance,
               url="https://i.picsum.photos/id/943/200/300.jpg?hmac=l_-sJ_gPk5DPHAo8YKbzTQnfS3H3H5EXzH3oDsa4bts",
               expected_hash='ffffffff1f060000')
    _test_hash(instance,
               url="https://i.picsum.photos/id/369/200/300.jpg?hmac=ZM5SPtUsEjxc4HjsZXj3DAHeKWSaZV6r8sJMGiLYIJ8",
               expected_hash='ffff2b438f678007')


def test_storage(instance: ImageManager):
    instance.image_hashes['asd'] = '123'
    assert instance.image_hashes['asd'] == '123'
    assert ImageManager(instance.image_hashes.directory).image_hashes['asd'] == '123'


def _test_hash(instance, url, expected_hash):
    returned_url, hash = asyncio.get_event_loop().run_until_complete(instance.get_image_hash(url))
    assert returned_url == url
    assert str(hash) == expected_hash
