import serial
import time
import threading
import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk
import io
from bs4 import BeautifulSoup

# ==== KONFIG ====
PORT = "COM14"
BAUD = 9600
APN = "internet"
SIM_PIN = "8942"

# Inicjalizacja portu z większym timeoutem dla stabilności
ser = serial.Serial(PORT, BAUD, timeout=1)

# ===== KOMUNIKACJA AT =====

def send(cmd, wait=1):
    ser.write((cmd + "\r\n").encode())
    time.sleep(wait)
    res = ser.read_all()
    print(f"CMD: {cmd} -> RESP: {res[:50]}...") # Debug w konsoli
    return res

# ===== INICJALIZACJA MODEMU =====

def init_modem():
    send("AT")
    send("ATE0") # Wyłącz echo, żeby nie śmieciło w odpowiedziach
    resp = send("AT+CPIN?")
    if b"SIM PIN" in resp:
        send(f"AT+CPIN={SIM_PIN}", 3)
    
    send("AT+SAPBR=3,1,\"Contype\",\"GPRS\"")
    send(f"AT+SAPBR=3,1,\"APN\",\"{APN}\"")
    send("AT+SAPBR=1,1", 3) # Otwarcie kontekstu GPRS

# ===== POBIERANIE DANYCH (NAPRAWIONE) =====

def http_get_full(url):
    # Czyścimy wszystko, co mogło zostać w buforze
    ser.read_all()
    
    send("AT+HTTPTERM")
    send("AT+HTTPINIT")
    send("AT+HTTPPARA=\"CID\",1")
    send("AT+HTTPPARA=\"URL\",\"{0}\"".format(url))

    ser.write(b"AT+HTTPACTION=0\r\n")
    
    content_len = 0
    timeout = time.time() + 30 # Czekamy na odpowiedź serwera
    
    while time.time() < timeout:
        line = ser.readline()
        if b"+HTTPACTION:" in line:
            parts = line.split(b",")
            if len(parts) >= 3:
                content_len = int(parts[2].strip())
            break
    
    if content_len <= 0:
        print(f"Błąd: Brak danych (len={content_len})")
        return b""

    print(f"Pobieranie {content_len} bajtów... (to potrwa przy 9600 baud)")
    ser.write(f"AT+HTTPREAD=0,{content_len}\r\n".encode())
    
    raw_data = b""
    # Obliczamy realny czas potrzebny na pobranie (1 sekunda na ok. 800 bajtów + zapas)
    download_timeout = time.time() + (content_len / 500) + 5
    
    # Pętla czytająca dokładnie tyle bajtów, ile trzeba
    while len(raw_data) < content_len + 20 and time.time() < download_timeout:
        if ser.in_waiting:
            raw_data += ser.read(ser.in_waiting)
        else:
            time.sleep(0.05)

    send("AT+HTTPTERM")

    # Wycinanie danych
    try:
        marker = b"+HTTPREAD:"
        if marker in raw_data:
            start_pos = raw_data.find(marker)
            # Dane zaczynają się po pierwszej linii (nagłówku READ)
            data_start = raw_data.find(b"\r\n", start_pos) + 2
            final_data = raw_data[data_start : data_start + content_len]
            
            print(f"DEBUG: Odebrano {len(final_data)}/{content_len} bajtów.")
            return final_data
    except:
        pass
        
    return b""
# ===== PARSOWANIE I GUI =====

def fix_images(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src")
        if src and not src.startswith("http"):
            # Prosta obsługa ścieżek względnych
            img["src"] = base_url.rstrip("/") + "/" + src.lstrip("/")
    return str(soup)

from urllib.parse import urljoin, urlparse

from urllib.parse import urljoin

def worker(url):
    global all_photos
    # Naprawa adresu URL
    if not url.startswith("http"):
        url = "http://" + url

    # Pobranie HTML
    raw_body = http_get_full(url)
    if not raw_body:
        output.after(0, lambda: output.insert(tk.END, "\n[Błąd: Brak odpowiedzi]"))
        return

    # Czyszczenie okna i starych obrazów
    output.after(0, lambda: output.delete(1.0, tk.END))
    all_photos.clear() 

    try:
        html_content = raw_body.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html_content, "html.parser")
        body = soup.find('body') if soup.find('body') else soup

        # Przetwarzamy elementy sekwencyjnie
        # Dodaliśmy 'li' (lista) oraz 'a' (link)
        for element in body.find_all(['p', 'h1', 'h2', 'h3', 'img', 'br', 'li', 'a']):
            
            # --- OBSŁUGA LINKÓW ---
            if element.name == 'a':
                href = element.get('href')
                link_text = element.get_text().strip()
                
                if href and link_text:
                    full_link = urljoin(url, href)
                    # Wstawiamy link z unikalnym tagiem
                    def insert_link(t=link_text, l=full_link):
                        start_index = output.index(tk.END)
                        output.insert(tk.END, t)
                        end_index = output.index(tk.END)
                        
                        # Tworzymy unikalną nazwę tagu dla tego konkretnego linku
                        tag_name = f"link_{start_index.replace('.', '_')}"
                        output.tag_add(tag_name, start_index, end_index)
                        
                        # Stylizacja: niebieski i podkreślenie
                        output.tag_config(tag_name, foreground="blue", underline=True)
                        
                        # Bindowanie kliknięcia
                        output.tag_bind(tag_name, "<Button-1>", lambda e, url=l: open_url(url))
                        
                        # Zmiana kursora na rączkę po najechaniu
                        output.tag_bind(tag_name, "<Enter>", lambda e: output.config(cursor="hand2"))
                        output.tag_bind(tag_name, "<Leave>", lambda e: output.config(cursor=""))
                        
                        output.insert(tk.END, " ") # Spacja po linku

                    output.after(0, insert_link)

            # --- OBSŁUGA ELEMENTÓW LISTY ---
            # --- OBSŁUGA LINKÓW ---
# --- OBSŁUGA LINKÓW ---
            if element.name == 'a':
                href = element.get('href')
                link_text = element.get_text(strip=True)
                
                if href and link_text:
                    full_link = urljoin(url, href)
                    
                    def add_link_gui(t=link_text, l=full_link):
                        # 1. Pobierz precyzyjny indeks startowy
                        start = output.index("end-1c")
                        
                        # 2. Wstaw tekst linku
                        output.insert(tk.END, t)
                        
                        # 3. Pobierz indeks końcowy
                        end = output.index("end-1c")
                        
                        # 4. Stwórz unikalny tag (np. link_5_10)
                        tag_name = f"link_{start.replace('.', '_')}_{end.replace('.', '_')}"
                        
                        output.tag_add(tag_name, start, end)
                        
                        # 5. Konfiguracja (MUSI być Normal, żeby kolory działały)
                        output.tag_config(tag_name, foreground="blue", underline=True)
                        
                        # 6. Zdarzenia
                        output.tag_bind(tag_name, "<Button-1>", lambda e, url_val=l: open_url(url_val))
                        output.tag_bind(tag_name, "<Enter>", lambda e: output.config(cursor="hand2"))
                        output.tag_bind(tag_name, "<Leave>", lambda e: output.config(cursor=""))
                        
                        output.insert(tk.END, " ") # Spacja separatora
                        output.update_idletasks() # Odśwież widok tagów

                    output.after(0, add_link_gui)

            # --- OBSŁUGA OBRAZÓW (z poprzedniej poprawki) ---
            elif element.name == 'img':
                src = element.get("src")
                if src:
                    full_img_url = urljoin(url, src)
                    output.after(0, lambda: output.insert(tk.END, f"\n[Obraz: {full_img_url.split('/')[-1]}] "))
                    img_data = http_get_full(full_img_url)
                    if img_data:
                        display_image(img_data)

            elif element.name in ['p', 'h1', 'h2', 'h3', 'li']:
                # Pobieramy tekst bezpośrednio z elementu
                txt = element.get_text(strip=True)
                
                if txt:
                    # Jeśli to element listy, dodajmy kropkę na początku
                    if element.name == 'li':
                        prefix = "\n • "
                        suffix = ""
                    elif element.name.startswith('h'):
                        prefix = "\n\n--- "
                        suffix = " ---\n"
                        txt = txt.upper()
                    else:
                        prefix = "\n"
                        suffix = "\n"

                    full_text = f"{prefix}{txt}{suffix}"
                    output.after(0, lambda t=full_text: output.insert(tk.END, t))

    except Exception as e:
        print(f"Błąd renderowania: {e}")

# Pomocnicza funkcja do obsługi kliknięcia
def open_url(new_url):
    url_entry.delete(0, tk.END)
    url_entry.insert(0, new_url)
    fetch() # Ponowne wywołanie pobierania dla nowego adresu
# Dodaj tę listę na początku kodu (poza funkcjami)
all_photos = []

def display_image(data):
    global all_photos
    try:
        img_io = io.BytesIO(data)
        image = Image.open(img_io)
        
        # Proporcjonalne skalowanie
        image.thumbnail((300, 300))
        photo = ImageTk.PhotoImage(image)
        
        # ZAPAMIĘTAJ REFERENCJĘ! To najważniejszy krok.
        all_photos.append(photo) 
        
        def update_ui():
            output.image_create(tk.END, image=photo)
            output.insert(tk.END, "\n")
            output.see(tk.END) # Przesuń widok na dół
            
        output.after(0, update_ui)
        print("Obrazek dodany do GUI.")
    except Exception as e:
        print(f"Błąd PIL/Tkinter: {e}")
# ===== GUI SETUP =====

def fetch():
    url = url_entry.get()
    output.delete(1.0, tk.END)
    output.insert(tk.END, "Inicjowanie połączenia GPRS i pobieranie...\n")
    threading.Thread(target=worker, args=(url,), daemon=True).start()

app = tk.Tk()
app.title("SIM900 Mini Browser")
app.geometry("800x600")

top = tk.Frame(app)
top.pack(fill=tk.X, padx=5, pady=5)

url_entry = tk.Entry(top)
url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
url_entry.insert(0, "http://example.com") # Testowy adres (czysty tekst)

btn = tk.Button(top, text="POBIERZ", command=fetch)
btn.pack(side=tk.RIGHT, padx=5)

output = scrolledtext.ScrolledText(app, wrap=tk.WORD)
output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

# Start
threading.Thread(target=init_modem, daemon=True).start()
app.mainloop()
