import ctypes
import datetime
import os
import random
import time
import zipfile
from loguru import logger
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options



class NoContentException(Exception):
    pass

def is_file_content_exist(file_path):
    return os.stat(os.path.abspath(file_path)).st_size != 0

def get_file_content(file_path):
    content = []

    with open(file_path) as file:
        content = file.readlines()

    return content

def edit_link(link):
    o = urlparse(link)
    return f'{o.scheme}://{o.netloc}{o.path}'

def get_random_item_from_file(file_path):
    return random.choice(get_file_content(file_path)).strip().replace('\n', '')

def parse_page_content(driver):
    title = driver.find_element(By.CSS_SELECTOR, 'h1.article__title').text
    preview_link = driver.find_element(By.CSS_SELECTOR, '.article-image-item__image').get_attribute('src')
    text_blocks = driver.find_elements(By.CSS_SELECTOR, '.article-render__block span')
    text_blocks_content = []

    for text_block in text_blocks:
        if not text_block.get_attribute('class') or len(text_block.get_attribute('class')) == 0:
            text_blocks_content.append(text_block.text)

    return {
        'title': title,
        'preview_link': preview_link,
        'text_blocks_content': text_blocks_content
    }


def save_text_into_file(file_path, text):
    with open(file_path, 'a') as file:
        file.write(text)

def remove_dates_from_list(list):
    edited_list = []

    for st in list:
        try:
            try:
                datetime.datetime.strptime(st, '%d %B')
            except:
                datetime.datetime.strptime(st, '%d %B %Y')
        except:
            edited_list.append(st)

    return edited_list

def load_page_content(driver, link):
    driver.delete_all_cookies()
    time.sleep(random.randint(10, 15))
    driver.get(link)
    time.sleep(random.randint(10, 15))
    parsed_content = parse_page_content(driver)
    list_without_dates = remove_dates_from_list(parsed_content['text_blocks_content'])
    parsed_content['text_blocks_content'] = list(filter(None, list_without_dates))
    title, preview_link, text_blocks_content = parsed_content.values()
    text_content = '\n'.join(text_blocks_content)
    parsed_text = f'{title}\n{preview_link}\n{text_content}'
    save_text_into_file(f'articles/{title}.txt', parsed_text)

def get_extension_data(proxy):
    ip, port, login, password = proxy

    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {
            mode: "fixed_servers",
            rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
            },
            bypassList: ["localhost"]
            }
        };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {urls: ["<all_urls>"]},
                ['blocking']
    );
    """ % (ip, port, login, password)

    return (manifest_json, background_js)

def get_chromedriver(anonymity):
    path = os.path.dirname(os.path.abspath(__file__))
    manifest_json, background_js = get_extension_data(anonymity['proxy'])
    options = Options()

    if 'proxy' in anonymity:
        pluginfile = 'proxy_auth_plugin.zip'

        with zipfile.ZipFile(pluginfile, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)

        options.add_extension(pluginfile)

    if 'user_agent' in anonymity:
        user_agent = anonymity['user_agent']
        options.add_argument(f'user-agent={user_agent}')

    driver = webdriver.Chrome(
        service=Service(os.path.join(path, 'chromedriver')),
        options=options
    )

    return driver

def main():
    logger.info('Начало работы скрипта')

    try:
        dir = os.path.dirname(os.path.abspath(__file__))
        anonymity = {}
        should_use_user_agent = is_file_content_exist('user-agents.txt')
        should_use_proxy = is_file_content_exist('proxies.txt')

        if is_file_content_exist('links.txt') is False:
            raise NoContentException('Пожалуйства добавьте ссылки в файл links.txt')

        if should_use_user_agent:
            anonymity['user_agent'] = get_random_item_from_file('user-agents.txt')
        

        if should_use_proxy:
            anonymity['proxy'] = tuple(get_random_item_from_file('proxies.txt').split(':'))

        links = map(edit_link, open('links.txt', 'r').readlines())

        if not should_use_user_agent and not should_use_proxy:
            driver = webdriver.Chrome(service=Service(f'{dir}/chromedriver'))

            for link in links:
                load_page_content(driver, link)

        else:
            for link in links:
                driver = get_chromedriver(anonymity)
                load_page_content(driver, link)
                

    except Exception as ex:
        logger.error(ex)
    finally:
        driver.close()
        driver.quit()
        logger.info('Конец работы скрипта')



if __name__ == '__main__':
    main()
