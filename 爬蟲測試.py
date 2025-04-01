import time
import random
import string
import os
import cv2
import numpy as np
import copy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import pytesseract
import requests

# 設定 Tesseract OCR 的路徑（Windows 用戶需要這行）
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# 去除圖片雜訊
def del_noise(img, number):
    height = img.shape[0]
    width = img.shape[1]
    img_new = copy.deepcopy(img)
    for i in range(1, height - 1):
        for j in range(1, width - 1):
            point = [[], [], []]
            count = 0
            point[0].append(img[i - 1][j - 1])
            point[0].append(img[i - 1][j])
            point[0].append(img[i - 1][j + 1])
            point[1].append(img[i][j - 1])
            point[1].append(img[i][j])
            point[1].append(img[i][j + 1])
            point[2].append(img[i + 1][j - 1])
            point[2].append(img[i + 1][j])
            point[2].append(img[i + 1][j + 1])
            for k in range(3):
                for z in range(3):
                    if point[k][z] == 0:
                        count += 1
            if count <= number:
                img_new[i, j] = 255
    return img_new

# 產生隨機密碼
def random_password(length=10):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for _ in range(length))

# 設定 WebDriver
driver = webdriver.Chrome()
driver.get("https://sso.nutc.edu.tw/eportal/")  # 目標網站

# 找到帳號輸入框並輸入帳號
account_input = driver.find_element(By.ID, "ContentPlaceHolder1_Account")
account_input.send_keys("s1111032016")

# 找到密碼輸入框並輸入亂碼密碼
password_input = driver.find_element(By.ID, "ContentPlaceHolder1_Password")
password_input.send_keys(random_password())

time.sleep(2)

# 等待驗證碼圖片載入
try:
    captcha_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//img[@alt="驗證碼"]'))
    )
    print("✅ 驗證碼圖片已找到")
except:
    print("❌ 無法找到驗證碼圖片，請確認 ID 或 XPATH 是否正確")
    driver.quit()
    exit()

# 取得驗證碼圖片的 URL
captcha_url = captcha_element.get_attribute("src")

# 檢查 URL 是否是相對路徑，如果是，補上完整的網域
if not captcha_url.startswith("http"):
    captcha_url = "https://sso.nutc.edu.tw" + captcha_url  # 補上網域

# 使用 requests 下載圖片
response = requests.get(captcha_url)

# 儲存圖片為本地檔案
with open("captcha.png", "wb") as f:
    f.write(response.content)

# 讀取驗證碼圖片
image = cv2.imread("captcha.png")

# 灰度化處理
gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# 自適應二值化
result = cv2.adaptiveThreshold(gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 1)

# 去噪聲處理
cleaned_image = del_noise(result, 4)

# 使用雙邊濾波進行進一步去噪
filtered_image = cv2.bilateralFilter(src=cleaned_image, d=6, sigmaColor=75, sigmaSpace=75)

# 裁剪邊緣，移除可能的無用區域
filtered_image = filtered_image[1:-1, 1:-1]

# 添加邊框以防止邊界處理的影響
filtered_image = cv2.copyMakeBorder(filtered_image, 13, 13, 13, 13, cv2.BORDER_CONSTANT, value=[255])

# 儲存處理後的圖片
cv2.imwrite("processed_captcha.png", filtered_image)

# 使用 pytesseract 進行 OCR 辨識
captcha_text = pytesseract.image_to_string(Image.fromarray(filtered_image), config="--psm 8 --oem 3").strip()

# 檢查是否成功辨識到驗證碼
if captcha_text:
    print("有辨識到:", captcha_text)
else:
    print("無法辨識，請檢查驗證碼圖片品質")
    driver.quit()
    exit()

# 找到驗證碼輸入框並輸入辨識結果
captcha_input = driver.find_element(By.ID, "ContentPlaceHolder1_ValidationCode")
captcha_input.send_keys(captcha_text)
time.sleep(5)

# 按下 Enter 鍵或找到登入按鈕點擊
captcha_input.send_keys(Keys.RETURN)

# 等待登入完成
time.sleep(5)

# 關閉瀏覽器
driver.quit()
