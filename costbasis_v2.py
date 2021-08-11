from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import locale

sleep_time = 2

locale.setlocale(locale.LC_NUMERIC, "en_US.UTF-8")

driver = webdriver.Chrome()
driver.get("https://www.tdameritrade.com/home.html")
enter_unsettled_closed_postion = False
while not enter_unsettled_closed_postion:
    time.sleep(1)
    global unsettled_url
    unsettled_url = driver.current_url
    if unsettled_url.find(r'gainlosstype=unsettledclosed') == -1:
        time.sleep(1)
    else:
        enter_unsettled_closed_postion = True
        print("enter unsettled closed position page")
print(unsettled_url)
time.sleep(sleep_time)
finished = False
while not finished:
    finished = True
    main_page = driver.find_element_by_xpath(xpath='/html/body/div[1]/div[1]/div[2]/div/div/iframe[1]')
    main_frame_y = main_page.location['y']
    print("main:", main_page.id)
    driver.switch_to.frame(main_page)
    line = driver.find_elements_by_xpath(xpath='/html/body/div[2]/div[3]/div[2]/form[2]/div[4]/div/table/tbody/*')
    dev_tag = 4
    if len(line)==0:
        line = driver.find_elements_by_xpath(xpath='/html/body/div[2]/div[3]/div[2]/form[2]/div[3]/div/table/tbody/*')
        dev_tag = 3
    print(len(line))

    line_count = 1
    for eid in line:
        tmp = eid.text.split()
        tax_lot_method = tmp[len(tmp)-1]
        str_count = 0
        if tax_lot_method == "ID":
            tax_lot_method = tmp[len(tmp)-2]+" "+tmp[len(tmp)-1]
            str_count = 1
        total_proceeds = locale.atof(tmp[len(tmp)-str_count-5])
        quantity = 0 - locale.atoi(tmp[len(tmp)-str_count-6])
        sell_cost_per_share = total_proceeds / quantity
        security = ''
        for a in range(len(tmp)-6):
            security = security+" "+tmp[a]
        print('tax_lot_method:', tax_lot_method, '    line_count:', line_count)

        if tax_lot_method != "By ID":
            if dev_tag == 4:
                click_button_xpath = "/html/body/div[2]/div[3]/div[2]/form[2]/div[4]/div/table/tbody/tr["+str(line_count)+"]/td[13]/span"
            elif dev_tag == 3:
                click_button_xpath = "/html/body/div[2]/div[3]/div[2]/form[2]/div[3]/div/table/tbody/tr[" + str(
                    line_count) + "]/td[13]/span"
            print("xpath1:   ", click_button_xpath)
            b1 = driver.find_element_by_xpath(xpath=click_button_xpath)

            desired_y = (b1.size['height'] / 2) + b1.location['y'] + main_frame_y
            driver.switch_to.default_content()
            window_h = driver.execute_script('return window.innerHeight')
            window_y = driver.execute_script('return window.pageYOffset')
            current_y = (window_h / 2) + window_y
            scroll_y_by = desired_y - current_y
            driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)
            driver.switch_to.frame(main_page)

            b1.click()
            time.sleep(sleep_time)
            driver.find_element_by_xpath(xpath='/html/body/div[1]/table/tbody/tr/td/table[2]/tbody/tr[2]/td/table/tbody/tr[3]/td/ul/li/a').click()
            time.sleep(sleep_time)
            s1 = Select(driver.find_element_by_xpath(xpath='/html/body/div[1]/div[3]/div[2]/form/table[2]/tbody/tr/td[2]/select'))
            s1.select_by_index(5)
            time.sleep(sleep_time)
            price_lots = driver.find_elements_by_xpath(xpath="/html/body/div[1]/div[3]/div[2]/form/table[3]/tbody/*")
            price_lots_length = len(price_lots) - 1
            print("price_lots length:", price_lots_length)
            data = []               #[lot for i in range(price_lots_length)]

            for l_count in range(0, price_lots_length):
                lot = {"Date": "", "Qty": 0, "Amount": 0.0, "CostPerShare": 0.0, "tr_count": 0}
                tmp_xpath = "/html/body/div[1]/div[3]/div[2]/form/table[3]/tbody/tr[" + str(l_count+1) + "]/td[1]"
                #/html/body/div[1]/div[3]/div[2]/form/table[3]/tbody/tr[297]/td[1]
                lot["Date"] = driver.find_element_by_xpath(xpath=tmp_xpath).text
                tmp_xpath = "/html/body/div[1]/div[3]/div[2]/form/table[3]/tbody/tr[" + str(l_count+1) + "]/td[2]"
                lot["Qty"] = locale.atoi(driver.find_element_by_xpath(xpath=tmp_xpath).text)
                tmp_xpath = "/html/body/div[1]/div[3]/div[2]/form/table[3]/tbody/tr[" + str(l_count + 1) + "]/td[4]"
                lot["Amount"] = locale.atof(driver.find_element_by_xpath(xpath=tmp_xpath).text)
                lot["CostPerShare"] = lot["Amount"]/lot["Qty"]
                lot["tr_count"] = l_count+1
                data.append(lot)

            def take_cost(elem):
                return elem["CostPerShare"]
            data.sort(key=take_cost, reverse=True)
            print(data)

            remaining_qty = quantity
            for l_data in data:
                if l_data["CostPerShare"] < sell_cost_per_share:
                    if l_data["Qty"] >= remaining_qty:
                        #fill_qty = remaining_qty
                        #-------------------scroll-----------------
                        fill_data_1_xpath = "/html/body/div[1]/div[3]/div[2]/form/table[3]/tbody/tr["+str(l_data["tr_count"])+"]/td[5]/input"
                        fill_data_1 = driver.find_element_by_xpath(xpath=fill_data_1_xpath)
                        desired_y = (fill_data_1.size['height'] / 2) + fill_data_1.location['y'] + main_frame_y
                        driver.switch_to.default_content()
                        window_h = driver.execute_script('return window.innerHeight')
                        window_y = driver.execute_script('return window.pageYOffset')
                        current_y = (window_h / 2) + window_y
                        scroll_y_by = desired_y - current_y
                        driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)
                        driver.switch_to.frame(main_page)
                        #-------------------scroll end-------------
                        fill_data_1.send_keys(str(remaining_qty))

                        time.sleep(sleep_time)

                        # -------------------scroll-----------------
                        submit_bt = driver.find_element_by_xpath(xpath="/html/body/div[1]/div[3]/div[2]/form/table[4]/tbody/tr/td[2]/a")
                        desired_y = (submit_bt.size['height'] / 2) + submit_bt.location['y'] + main_frame_y
                        driver.switch_to.default_content()
                        window_h = driver.execute_script('return window.innerHeight')
                        window_y = driver.execute_script('return window.pageYOffset')
                        current_y = (window_h / 2) + window_y
                        scroll_y_by = desired_y - current_y
                        driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)
                        driver.switch_to.frame(main_page)
                        # -------------------scroll end-------------
                        submit_bt.click()

                        time.sleep(sleep_time)

                        break
                    else:
                        #fill_qty = l_data["Qty"]
                        remaining_qty = remaining_qty - l_data["Qty"]
                        #-------------------scroll-----------------
                        fill_data_1_xpath = "/html/body/div[1]/div[3]/div[2]/form/table[3]/tbody/tr["+str(l_data["tr_count"])+"]/td[5]/input"
                        fill_data_1 = driver.find_element_by_xpath(xpath=fill_data_1_xpath)
                        desired_y = (fill_data_1.size['height'] / 2) + fill_data_1.location['y'] + main_frame_y
                        driver.switch_to.default_content()
                        window_h = driver.execute_script('return window.innerHeight')
                        window_y = driver.execute_script('return window.pageYOffset')
                        current_y = (window_h / 2) + window_y
                        scroll_y_by = desired_y - current_y
                        driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)
                        driver.switch_to.frame(main_page)
                        #-------------------scroll end-------------
                        fill_data_1.send_keys(str(l_data["Qty"]))

                        time.sleep(sleep_time)

            driver.get(unsettled_url)
            time.sleep(sleep_time)
            finished = False
            break

        line_count = line_count+1
print("success")


