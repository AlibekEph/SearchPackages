import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import requests
from selenium.webdriver import ActionChains
import subprocess
import shutil
import base64
import re
from io import BytesIO

def send_image_to_detector(image_data, object_name):
    if image_data.startswith('data:image'):
        image_data = image_data.split(',')[1]
    image_bytes = base64.b64decode(image_data)
    url = "http://dino-detector:8008/detect_object"
    files = {
        'file': ('image.jpg', BytesIO(image_bytes), 'image/jpeg')
    }
    params = {
        'object_name': object_name
    }
    response = requests.post(url, files=files, params=params)
    if response.status_code == 200:
        result = response.json()
        sim = result['results']['clip'][0]['probability']
        print(sim)
        return sim
    else:
        print(f"Ошибка при отправке изображения: {response.status_code}")
        print(response.text)

def open_pkgs_search(query):
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    try:
        driver = webdriver.Remote(
            command_executor='http://158.160.101.255:4441',
            options=chrome_options
        )
        url = f"https://pkgs.org/search/?q={query}"
        print(f"Открываю страницу: {url}")
        driver.get(url)
        time.sleep(5)
        driver.find_element(By.ID, "consent_notice_agree").click()
        print("\nРезультаты поиска:")
        results = driver.find_elements("css selector", ".package-list-item")
        for result in results[:5]:
            try:
                name = result.find_element("css selector", ".package-name").text
                version = result.find_element("css selector", ".package-version").text
                print(f"Пакет: {name}, Версия: {version}")
            except:
                continue
        print("\nПоиск изображений...")
        while True:
            images = driver.find_elements(By.CSS_SELECTOR, "img.img-fluid")
            print(f"Найдено изображений: {len(images)}")
            sim_results = []
            for idx, img in enumerate(images, 0):
                try:
                    src = img.get_attribute('src')
                    if src and src.startswith('data:image'):
                        try:
                            label_element = driver.find_element(By.CSS_SELECTOR, ".text-bg-danger")
                            object_name = label_element.text.strip()
                        except:
                            print(f"Не найден элемент с меткой для изображения {idx}")
                            continue
                        print(f"\nОбработка изображения {idx} с меткой '{object_name}':")
                        pred = send_image_to_detector(src, object_name)
                        sim_results.append({
                            'filename': idx,
                            'probability': pred,
                        })
                except Exception as e:
                    print(f"Ошибка при обработке изображения {idx}: {str(e)}")
            if len(images) != 0:
                actions = ActionChains(driver)
                actions.move_to_element(images[-1]).perform()
                time.sleep(10)
                sim_results.sort(key=lambda x: x['probability'], reverse=True)
                for i in range(3):
                    images[sim_results[i]['filename']].click()
            time.sleep(5)
            img = driver.find_elements(By.CSS_SELECTOR, "img.img-fluid")
            if len(img) == 0:
                break
        links = driver.find_elements(By.CSS_SELECTOR, 'a[href^="https://fedora.pkgs.org/"]')
        for i in range(len(links)):
            print(f"{i}) ", links[i].get_attribute('href'))
        choose = int(input())
        driver.get(links[choose].get_attribute('href'))
        print('Открываю страницу с пакетом')
        time.sleep(5)
        html = driver.page_source
        match = re.search(r"https://dl\.fedoraproject\.org/pub/fedora/linux/updates/[^\s\"']+", html)
        if match:
            try:
                print(match.group(0))
            except IndexError:
                print("Не удалось найти URL для скачивания пакета")
        while True:
            img = driver.find_elements(By.CSS_SELECTOR, "img.img-fluid")
            if len(img) == 0:
                break
            sim_results = []            
            for idx, img in enumerate(images, 0):
                try:
                    src = img.get_attribute('src')
                    if src and src.startswith('data:image'):
                        try:
                            label_element = driver.find_element(By.CSS_SELECTOR, ".text-bg-danger")
                            object_name = label_element.text.strip()
                        except:
                            print(f"Не найден элемент с меткой для изображения {idx}")
                            continue
                        print(f"\nОбработка изображения {idx} с меткой '{object_name}':")
                        pred = send_image_to_detector(src, object_name)
                        sim_results.append({
                            'filename': idx,
                            'probability': pred,
                        })
                except Exception as e:
                    print(f"Ошибка при обработке изображения {idx}: {str(e)}")
            sim_results.sort(key=lambda x: x['probability'], reverse=True)
            for i in range(3):
                images[sim_results[i]['filename']].click()
            time.sleep(5)
        rpm_url = driver.find_element(
            By.XPATH,
            "//tr[th[normalize-space(text())='Binary Package']]/td"
        ).text
        print(rpm_url)
        driver.quit()
        return rpm_url
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")
        if 'driver' in locals():
            driver.quit()

def run_cmd(cmd, capture_output=False, check=False):
    if capture_output:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if check and proc.returncode != 0:
            proc.check_returncode()
        return proc.returncode, proc.stdout.strip()
    else:
        proc = subprocess.run(cmd)
        if check and proc.returncode != 0:
            proc.check_returncode()
        return proc.returncode

def get_package_basename(url_or_path):
    fname = os.path.basename(url_or_path)
    if fname.endswith('.rpm'):
        return fname[:-4]
    return fname

def check_installed(pkg_name):
    code = subprocess.run(["rpm", "-q", pkg_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    return code == 0

def remove_package(pkg_name):
    print(f"Removing installed package '{pkg_name}'...")
    code = run_cmd(["rpm", "-e", pkg_name])
    if code != 0:
        print(f"Error removing package '{pkg_name}'. Exit code: {code}")
        sys.exit(1)
    print("Removal succeeded.")

def download_rpm(url):
    fname = os.path.basename(url)
    if os.path.exists(fname):
        os.remove(fname)
    downloader = shutil.which('curl') or shutil.which('wget')
    if downloader is None:
        print("Neither curl nor wget found. Install one to proceed.")
        sys.exit(1)
    if downloader.endswith('curl'):
        cmd = ['curl', '-LO', url]
    else:
        cmd = ['wget', url]
    print(f"Downloading RPM: {' '.join(cmd)}")
    code = run_cmd(cmd)
    if code != 0 or not os.path.exists(fname):
        print(f"Failed to download {url} (exit {code}).")
        sys.exit(1)
    return fname

def install_rpm(file_path):
    print(f"Installing {file_path} via dnf...")
    code = run_cmd(['dnf', 'install', '-y', file_path])
    if code != 0:
        print(f"Installation failed (exit {code}).")
        sys.exit(1)
    print("Installation completed successfully.")

def RnB(rpm_url):
    pkg_base = get_package_basename(rpm_url)
    pkg_name = pkg_base.split('-', 1)[0]
    if check_installed(pkg_name):
        ans = input(f"Package '{pkg_name}' is already installed. Remove it? [y/N]: ").strip().lower()
        if ans == 'y':
            remove_package(pkg_name)
        else:
            print("Aborting.")
            sys.exit(0)
    rpm_file = download_rpm(rpm_url)
    install_rpm(rpm_file)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Re-running with sudo to gain root privileges...")
        os.execvp("sudo", ["sudo", sys.executable] + sys.argv)
    if len(sys.argv) != 2:
        print("Использование: python search_packages.py <поисковый_запрос>")
        sys.exit(1)
    query = sys.argv[1]
    rpm_url = open_pkgs_search(query) 
    RnB(rpm_url)
