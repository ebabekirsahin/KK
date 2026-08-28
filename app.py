"""
Kosmos Vize - Randevu Müsaitlik İzleyici
==========================================

NE YAPAR:
- Belirli aralıklarla randevu sayfasını kontrol eder
- Sayfa içeriğinde bir değişiklik (örn. "müsait değil" -> "müsait" gibi)
  tespit ederse size bildirim gönderir (e-posta / masaüstü bildirimi)

NE YAPMAZ:
- Formu otomatik doldurmaz
- "Robot değilim" kutucuğunu işaretlemez
- Randevuyu sizin adınıza almaz / submit etmez

Randevu almayı YALNIZCA siz, bildirim geldikten sonra elle yaparsınız.

KURULUM ADIMLARI
-----------------
1) Tarayıcıda randevu sayfasını açın, F12 ile Geliştirici Araçları'nı açın,
   "Network" (Ağ) sekmesine geçin.
2) Randevu formunda tarih/saat seçim adımına kadar ilerleyin (mümkünse elle).
3) Network sekmesinde, tarih/saat listesini getiren isteği bulun
   (genelde XHR/Fetch türünde, "date", "slot", "appointment", "calendar"
   gibi kelimeler geçen bir URL olur).
4) O isteğin URL'sini ve varsa gövdesini (headers/body) aşağıdaki
   CHECK_URL, CHECK_METHOD, CHECK_HEADERS, CHECK_PAYLOAD alanlarına girin.
5) AVAILABLE_KEYWORDS listesine, "müsait slot var" anlamına gelen
   kelime/işaretleri girin (örn. belirli bir tarih formatı, "available"
   kelimesi, ya da JSON'da boş olmayan bir "slots" listesi).

Eğer API isteğini bulamazsanız, alternatif olarak sayfanın HTML'ini
periyodik çekip belirli bir metnin (örn. "Uygun randevu bulunmamaktadır")
kaybolup kaybolmadığını kontrol edebiliriz (aşağıda HTML_MODE ile).
"""

import time
import smtplib
from email.mime.text import MIMEText
import requests

# ============ AYARLAR (buraları kendinize göre doldurun) ============

# Kontrol sıklığı (saniye). Not: 300'ün altına inmek siteyi daha sık yorar
# ve bot tespiti/IP engeli riskini artırır; 120 sn makul bir orta nokta.
CHECK_INTERVAL_SECONDS = 120

# --- Yöntem 1: API isteğini biliyorsanız (önerilen) ---
USE_API_MODE = False
CHECK_URL = "https://basvuru.kosmosvize.com.tr/..."  # bulduğunuz gerçek endpoint
CHECK_METHOD = "GET"  # veya "POST"
CHECK_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    # gerekiyorsa Cookie, Referer, X-Requested-With vb. ekleyin
}
CHECK_PAYLOAD = {}  # POST ise gövde parametreleri

# Yanıt içinde "müsait randevu var" anlamına gelen anahtar kelime(ler)
AVAILABLE_KEYWORDS = ["available", "musait", "boş"]
# Yanıt içinde "müsait değil" anlamına gelen kelime(ler) (varsa)
UNAVAILABLE_KEYWORDS = ["uygun randevu bulunmamaktadır", "no appointment"]

# --- Yöntem 2: Sadece HTML sayfasını izlemek isterseniz ---
HTML_MODE = True
PAGE_URL = "https://basvuru.kosmosvize.com.tr/appointmentform"
# Bu metin sayfada varsa "müsait değil" demektir; kaybolursa bildirim gider.
NO_SLOT_TEXT = "Uygun randevu bulunmamaktadır"

# --- Bildirim ayarları (e-posta ile) ---
SEND_EMAIL = True
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "kayra4kara8@gmail.com"  # gönderen hesap (aynı adres olabilir)
SMTP_PASS = "uygulama_sifresi"  # Gmail "Uygulama Şifresi" ile değiştirin, normal şifre çalışmaz
NOTIFY_TO = "kayra4kara8@gmail.com"

# ======================================================================


def send_email_notification(subject: str, body: str) -> None:
    if not SEND_EMAIL:
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_TO
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [NOTIFY_TO], msg.as_string())
        print("Bildirim e-postası gönderildi.")
    except Exception as e:
        print(f"E-posta gönderilemedi: {e}")


def notify(message: str) -> None:
    print(f"\n*** {message} ***\n")
    # Basit masaüstü bip sesi (bazı terminallerde çalışır)
    print("\a")
    send_email_notification("Kosmos Vize - Randevu Müsait Olabilir!", message)


def check_via_api() -> bool:
    """API isteğinden müsaitlik kontrolü. True dönerse müsait olabilir."""
    resp = requests.request(
        CHECK_METHOD, CHECK_URL, headers=CHECK_HEADERS, data=CHECK_PAYLOAD, timeout=15
    )
    resp.raise_for_status()
    text = resp.text.lower()

    if any(k.lower() in text for k in UNAVAILABLE_KEYWORDS):
        return False
    if any(k.lower() in text for k in AVAILABLE_KEYWORDS):
        return True
    # Hiçbir anahtar kelime eşleşmezse emin olunamaz; loglayıp devam edin.
    return False


def check_via_html() -> bool:
    """HTML sayfasında 'müsait değil' metni yoksa muhtemelen slot açılmıştır."""
    resp = requests.get(PAGE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    resp.raise_for_status()
    return NO_SLOT_TEXT not in resp.text


def main() -> None:
    print("İzleme başladı. Durdurmak için Ctrl+C.")
    while True:
        try:
            if USE_API_MODE:
                available = check_via_api()
            elif HTML_MODE:
                available = check_via_html()
            else:
                print("Lütfen USE_API_MODE veya HTML_MODE ayarlarından birini seçin.")
                return

            if available:
                notify("Randevu sayfasında müsaitlik olabilir! Hemen elle kontrol edin: " + PAGE_URL)
                # İsterseniz bulunca döngüyü durdurmak için:
                # break
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Müsaitlik yok, tekrar denenecek.")

        except Exception as e:
            print(f"Kontrol sırasında hata: {e}")

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
