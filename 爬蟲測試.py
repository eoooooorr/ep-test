import time
import random
import string
import os
import requests
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
            for k in range(3):
                for z in range(3):
                    point[k].append(img[i - 1 + k][j - 1 + z])
                    if point[k][z] == 0:
                        count += 1
            if count <= number:
                img_new[i, j] = 255  # 若黑色像素少於指定閾值，則將其視為雜訊並轉為白色
    return img_new

# 產生隨機密碼
def random_password(length=10):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for _ in range(length))

# 預處理驗證碼圖片
def preprocess_captcha(image_path):
    image = cv2.imread(image_path)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # 過濾藍色範圍（驗證碼主要顏色為 R62 G99 B240）
    lower_blue = np.array([100, 100, 100])
    upper_blue = np.array([140, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    mask_inv = cv2.bitwise_not(mask)
    
    # 轉換為灰階
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 透過遮罩過濾非驗證碼區域
    result = cv2.bitwise_and(gray, gray, mask=mask_inv)
    
    # 二值化處理
    _, binary = cv2.threshold(result, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 去除雜訊
    binary = del_noise(binary, 3)
    
    # 進一步清理小型噪點
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    # 儲存處理後的圖片
    processed_path = "processed_captcha.png"
    cv2.imwrite(processed_path, cleaned)
    return processed_path

# 主要流程
def main():
    driver = webdriver.Chrome()
    driver.get("https://sso.nutc.edu.tw/eportal/")
    
    # 填入帳號
    account_input = driver.find_element(By.ID, "ContentPlaceHolder1_Account")
    account_input.send_keys("s1111032016")
    
    # 填入隨機密碼
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
    
    # 檢查 URL 是否完整，若為相對路徑則補上網域
    if not captcha_url.startswith("http"):
        captcha_url = "https://sso.nutc.edu.tw" + captcha_url
    
    # 下載驗證碼圖片
    response = requests.get(captcha_url)
    with open("captcha.png", "wb") as f:
        f.write(response.content)
    
    # 預處理驗證碼圖片
    processed_image = preprocess_captcha("captcha.png")
    
    # 使用 OCR 解析驗證碼
    captcha_text = pytesseract.image_to_string(Image.open(processed_image), config="--psm 8 --oem 3").strip()
    
    # 檢查是否成功辨識驗證碼
    if captcha_text:
        print("有辨識到:", captcha_text)
    else:
        print("無法辨識，請檢查驗證碼圖片品質")
        driver.quit()
        exit()
    
    # 填入驗證碼
    captcha_input = driver.find_element(By.ID, "ContentPlaceHolder1_ValidationCode")
    captcha_input.send_keys(captcha_text)
    time.sleep(5)
    
    # 按下 Enter 提交
    captcha_input.send_keys(Keys.RETURN)
    
    # 等待登入完成
    time.sleep(5)
    
    # 關閉瀏覽器
    driver.quit()

if __name__ == "__main__":
    main()
