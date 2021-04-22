from selenium import webdriver

PATH = "C:\Program Files (x86)\chromedriver.exe"
URL = "http://developer.opto22.com/static/generated/manage-rest-api/swagger-ui/index.html#/"
driver = webdriver.Chrome(PATH)

driver.get(URL)