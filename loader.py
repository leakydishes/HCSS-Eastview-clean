import yaml
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time

import warnings

warnings.filterwarnings("ignore")


def yaml_loader(filepath):
    with open(filepath, 'r') as file_descriptor:
        data = yaml.load(file_descriptor)
    return data


def find_data_in_td(rows_in_table, filename):

    data = []
    for row in rows_in_table:
        td_elements = row.find_elements_by_tag_name('td')
        if td_elements:
            td_text_list = []
            for td in td_elements:
                td_text_list.append(td.text)
                try:
                    link = td.find_element_by_tag_name('a').get_attribute('href')
                    td_text_list.append(link)
                except:
                    pass

            data.append(td_text_list)
    data = [d[2:] for d in data]
    df = pd.DataFrame(data,
                      columns=['Article', 'ArticleLink', 'Author', 'SourceName', 'SourceLink', 'Date', 'Words', 'Score'])

    filename = filename + '.xlsx'
    return df['ArticleLink'].tolist()
    #df.to_excel(filename, index=False)


def get_info():
    #Create empty pandas dataframe

    #Read settings
    website_data = yaml_loader('settings.yaml')
    url = website_data['settings']['url']
    website_email = website_data['settings']['email']
    website_password = website_data['settings']['password']
    content_for_search = website_data['settings']['content']
    options = Options()
    #options.add_argument('--no-sandbox')
    #options.add_argument("--headless")
    #chrome_options.add_argument('--disable-dev-shm-usage')

    try:
        driver = webdriver.Chrome(
            executable_path=r'/usr/lib/chromium-browser/chromedriver',
            chrome_options=options)  # /usr/lib/chromium-browser
        #driver.set_window_size(1000, 320)
        driver.get(url)
        time.sleep(5)
        if url.endswith('/login'):
            emails = driver.find_elements_by_xpath(
                "//input[@class='form-control']")
            emails[0].send_keys(website_email)
            emails[1].send_keys(website_password)
            emails[1].send_keys(Keys.ENTER)

        search_bar = driver.find_element_by_xpath("//input[@name='searchForOriginal']")
        search_bar.send_keys(content_for_search)
        search_bar.send_keys(Keys.ENTER)

        time.sleep(8)
        tbody = driver.find_element_by_xpath("//table[@id='table-searchResultsArticles']")

        rows_in_table = tbody.find_elements_by_tag_name('tr')
        article_links = find_data_in_td(rows_in_table, content_for_search)

        for link in article_links:
            driver.get(link)
            time.sleep(2.5)
            link_button = driver.find_element_by_link_text('Full Image')
            link_button.click()
            time.sleep(25)
            print('Sleep ended')

            driver.switch_to.frame(driver.find_element_by_tag_name("iframe"))
            print(0.5)
            etc_button = driver.find_element_by_xpath("//div[@data-element='menuButton']")
            print(etc_button.get_attribute('innerHTML'))
            etc_button.click()
            print('Clicked')
            time.sleep(0.5)
            download_button = driver.find_element_by_xpath("//div[@data-element='downloadButton']")
            download_button.click()
            """<div class="Button ActionButton" =""><p>Download</p></div>"""
    except Exception as e:
        print(e)


if __name__ == '__main__':
    get_info()
"""
< data-element="menuButton"><div class="Icon "><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="m0 0h24v24h-24z" fill="none"></path><path d="m12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"></path></svg></div></div>
"""