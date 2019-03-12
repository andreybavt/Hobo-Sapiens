# apart_facile

## Prerequisite
```
Python 3
```

## Installation
```
pip install -r requirements.txt
```

## Run
```
AF_TELEGRAM_BOT_TOKEN="XXX" AF_TELEGRAM_CHAT_ID="XXX" python3 runner.py
```

where `AF_TELEGRAM_BOT_TOKEN` - is the environment variable containing telegram bot token

and   `AF_TELEGRAM_CHAT_ID` - is the environment variable containing telegram chat id where the notifications will be posted

## Contribution
To contribute it's possible to add a new proxy retriever or an agency website scrapper.

### New proxy retriever:
  Proxy management is done in `crawler_utils.async_proxy.ProxyManager#fetch_proxies`
  In order to add another proxy provider you can add another function like `fetch_a2u` that returns a list of `crawler_utils.async_proxy.Proxy`
  and call this new function below like:
  `all_found_proxies_result += fetch_clarketm()`
  
### New agency scrapper:
  All agency scrappers have the same tructure inheriting `services.abstract_service.AbstractService`
