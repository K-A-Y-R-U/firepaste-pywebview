#!/usr/bin/env python3
"""
Firepaste Bot — PyWebView backend con Scraping real (Playwright)
"""
import os, sys, json, time, threading, re, subprocess
from datetime import datetime
from pathlib import Path
import requests

# ── Auto-instalar dependencias ──
def instalar(pkg):
    subprocess.run([sys.executable, "-m", "pip", "install", "--user", pkg], check=True)

try:
    import webview
except ImportError:
    print("Instalando pywebview..."); instalar("pywebview"); import webview

# ── Archivos de datos ──
CONFIG_FILE   = Path.home() / ".firepaste_config.json"
HISTORY_FILE  = Path.home() / ".firepaste_history.json"
PATTERNS_FILE = Path.home() / ".firepaste_patterns.json"

DEFAULT_CONFIG = {
    "url_panel": "", "email": "", "password": "",
    "bot_api_token": "", "headless": False, "configurado": False
}

# ════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════
def load_json(path, default):
    if path.exists():
        try: return json.loads(path.read_text())
        except: pass
    return default.copy() if isinstance(default, dict) else default

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

# ════════════════════════════════════════════
#  SCRAPER — con soporte nativo para firepaste.com
# ════════════════════════════════════════════

def _es_firepaste(url: str) -> bool:
    """Detecta si la URL pertenece a firepaste.com (posts o vip)."""
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower().lstrip("www.")
    return host == "firepaste.com"


def _scrape_firepaste(url: str, progreso=None) -> dict:
    """
    Scrapea una página de firepaste.com usando requests + BeautifulSoup.
    No necesita Playwright porque el contenido es HTML estático (server-side).
    Devuelve {"titulo": str, "archivos": [{"nombre", "url", "size"}]}
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "beautifulsoup4"], check=True)
        from bs4 import BeautifulSoup

    def log(msg):
        if progreso: progreso(msg)
        else: print(msg)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    log(f"🌐 Scraping Firepaste: {url}")
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Título: <h3> dentro de .paste-content o primer <h3> de la página ──
    titulo = ""
    h3 = soup.select_one(".paste-content h3, .card-body h3, h3")
    if h3:
        titulo = h3.get_text(strip=True)
    log(f"📌 Título detectado: {titulo!r}")

    # ── Archivos: tabla con links ──
    archivos = []
    for fila in soup.select("table tbody tr"):
        celdas = fila.find_all("td")
        if len(celdas) < 1:
            continue
        enlace = celdas[0].find("a")
        if not enlace:
            continue
        nombre = enlace.get_text(strip=True)
        nombre = re.sub(r'\s+', ' ', nombre).strip()
        href   = enlace.get("href", "").strip()
        size   = celdas[-1].get_text(strip=True) if len(celdas) > 1 else ""
        if not nombre or not href:
            continue
        archivos.append({"nombre": nombre, "url": href, "size": size})

    log(f"✅ {len(archivos)} archivos encontrados")
    return {"titulo": titulo, "archivos": archivos}


def scrape_url(url: str, progreso=None) -> list:
    """
    Punto de entrada unificado para scraping.
    - URLs de firepaste.com → scraper liviano con requests (sin Playwright)
    - Otros sitios → scraper con Playwright (comportamiento original)
    """
    from urllib.parse import urljoin, urlparse

    def log(msg):
        if progreso: progreso(msg)
        else: print(msg)

    # ── Ruta rápida para firepaste.com ──
    if _es_firepaste(url):
        resultado = _scrape_firepaste(url, progreso)
        return resultado["archivos"]

    # ── Scraper genérico con Playwright (sitios externos) ──
    from playwright.sync_api import sync_playwright

    archivos = []
    ext_re = re.compile(
        r'\.(zip|rar|7z|rom|gba|gbc|nes|sfc|smc|n64|nds|iso|bin|z64|v64|xci|nsp|pkg|apk)(\?.*)?$',
        re.I
    )

    def _navegar(page, dest, espera=2):
        """Navega a una URL tolerando timeouts — usa domcontentloaded, nunca networkidle."""
        for modo in ("domcontentloaded", "load", "commit"):
            try:
                page.goto(dest, wait_until=modo, timeout=25000)
                time.sleep(espera)
                return True
            except Exception as e:
                log(f"⚠️ retry ({modo}): {e}")
        return False

    def _extraer_tabla(page):
        """Extrae archivos desde tabla HTML estándar (Filename | Type | Size)."""
        resultado = []
        for fila in page.query_selector_all("table tbody tr, table tr"):
            celdas = fila.query_selector_all("td")
            if len(celdas) < 2:
                continue
            enlace = celdas[0].query_selector("a")
            if not enlace:
                continue
            nombre = re.sub(r'\s+', ' ', enlace.inner_text()).strip()
            href   = enlace.get_attribute("href") or ""
            size   = celdas[-1].inner_text().strip()
            if nombre and href:
                resultado.append({"nombre": nombre, "url": urljoin(page.url, href), "size": size})
        return resultado

    def _extraer_titulo(page):
        """Extrae el título del juego desde h1/h2/h3."""
        for sel in ["h1", "h2", ".game-title", ".title", "h3"]:
            try:
                el = page.query_selector(sel)
                if el:
                    t = re.sub(r'\s+', ' ', el.inner_text()).strip()
                    if t and len(t) > 3:
                        return t
            except:
                pass
        return ""

    def _es_romsfun(url):
        from urllib.parse import urlparse
        return "romsfun.com" in urlparse(url).netloc

    def _scrape_romsfun(page, url, log):
        """
        Romsfun tiene 3 tipos de URL que el usuario puede pegar:

        A) /roms/.../pac-man-world.html     → página del juego
        B) /download/pac-man-world-5529     → página de lista de archivos
        C) /download/pac-man-world-5529/1   → página individual (con countdown)

        Para A: extraer título del h1, encontrar el href del botón "Download ROM",
                luego tratar como B.
        Para B: leer la tabla directamente con requests+BS4 (HTML estático).
        Para C: ya tenemos el link directo, guardarlo como único archivo.
        """
        import requests as req_lib
        try:
            from bs4 import BeautifulSoup as BS
        except ImportError:
            import subprocess, sys
            subprocess.run([sys.executable, "-m", "pip", "install", "--user", "beautifulsoup4"], check=True)
            from bs4 import BeautifulSoup as BS

        HEADERS = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        log(f"🎮 Modo romsfun: {url}")

        # ── Detectar tipo de URL ───────────────────────────────────────
        path = url.rstrip("/").split("romsfun.com")[-1]   # e.g. /roms/.../game.html
        partes_path = [p for p in path.split("/") if p]   # ['roms','gba','game.html']

        # Tipo C: /download/game-XXXX/N  (termina en número)
        if partes_path and partes_path[-1].isdigit():
            log(f"📂 URL directa de archivo individual: {url}")
            # Extraer nombre desde la página con Playwright (tiene countdown JS)
            _navegar(page, url, espera=1)
            nombre = ""
            try:
                h1 = page.query_selector("h1")
                if h1:
                    nombre = re.sub(r'\s+', ' ', h1.inner_text()).strip()
                    nombre = re.sub(r'(?i)^(you are downloading|download)\s+', '', nombre).strip()
            except:
                pass
            if not nombre:
                nombre = url.split("/")[-2].replace("-", " ").title()
            return [{"nombre": nombre, "url": url, "size": ""}], nombre

        # ── Tipo A: página del juego → obtener URL de lista ───────────
        url_lista = url  # por defecto asumimos que es tipo B
        titulo = ""

        if "/roms/" in url:
            # Leer página del juego con requests (es HTML estático)
            log(f"📖 Leyendo página del juego...")
            try:
                r = req_lib.get(url, headers=HEADERS, timeout=15)
                r.raise_for_status()
                soup = BS(r.text, "html.parser")

                # Título: <h1 class="...text-romfun-pink...">Pac-Man World</h1>
                for h in soup.find_all(["h1", "h2"]):
                    t = h.get_text(strip=True)
                    if t and len(t) > 2 and "ROMSFUN" not in t.upper() and "Download" not in t:
                        titulo = t
                        break
                if titulo:
                    log(f"📌 Título: {titulo!r}")

                # Botón Download ROM: <a href="/download/pac-man-world-5529">Download ROM</a>
                for a in soup.find_all("a", href=True):
                    txt = a.get_text(strip=True)
                    href = a["href"]
                    if "Download ROM" in txt and "/download/" in href:
                        # Asegurar URL absoluta
                        if href.startswith("/"):
                            href = "https://romsfun.com" + href
                        url_lista = href
                        log(f"🖱️ URL lista: {url_lista}")
                        break

                if url_lista == url:
                    log("⚠️ No se encontró botón 'Download ROM', intentando con Playwright...")
                    raise ValueError("fallback playwright")

            except Exception as e:
                if "fallback playwright" in str(e) or "requests" in str(type(e).__name__).lower():
                    # Fallback con Playwright
                    _navegar(page, url, espera=2)
                    try:
                        h1 = page.query_selector("h1")
                        if h1:
                            t = re.sub(r'\s+', ' ', h1.inner_text()).strip()
                            if t and "ROMSFUN" not in t.upper():
                                titulo = t
                    except: pass
                    try:
                        btn = page.query_selector('a:has-text("Download ROM")')
                        if btn:
                            href = btn.get_attribute("href") or ""
                            if href and "/download/" in href:
                                url_lista = urljoin(page.url, href)
                                log(f"🖱️ URL lista (playwright): {url_lista}")
                    except: pass

        # ── Tipo B / resultado de A: leer tabla con requests ──────────
        log(f"📋 Leyendo lista de archivos: {url_lista}")
        archivos = []
        try:
            r = req_lib.get(url_lista, headers=HEADERS, timeout=15)
            r.raise_for_status()
            soup = BS(r.text, "html.parser")

            # Si no tenemos título aún, buscarlo aquí
            if not titulo:
                for h in soup.find_all(["h1", "h2"]):
                    t = h.get_text(strip=True)
                    if t and len(t) > 2 and "ROMSFUN" not in t.upper() and "Download" not in t.split()[0:1]:
                        titulo = t
                        break

            # Tabla: thead con Filename | Type | Size
            for tabla in soup.find_all("table"):
                for fila in tabla.find_all("tr"):
                    celdas = fila.find_all("td")
                    if len(celdas) < 2:
                        continue
                    enlace = celdas[0].find("a")
                    if not enlace:
                        continue
                    nombre = enlace.get_text(strip=True)
                    nombre = re.sub(r'\s+', ' ', nombre).strip()
                    href   = enlace.get("href", "")
                    if href.startswith("/"):
                        href = "https://romsfun.com" + href
                    size   = celdas[-1].get_text(strip=True)
                    if nombre and href:
                        archivos.append({"nombre": nombre, "url": href, "size": size})

            log(f"✅ {len(archivos)} archivos encontrados")

        except Exception as e:
            log(f"⚠️ Error requests: {e}")
            # Último fallback con Playwright
            _navegar(page, url_lista, espera=3)
            for _ in range(5):
                filas = page.query_selector_all("table tbody tr")
                if filas:
                    break
                time.sleep(1)
            for fila in page.query_selector_all("table tbody tr"):
                celdas = fila.query_selector_all("td")
                if len(celdas) < 2: continue
                enlace = celdas[0].query_selector("a")
                if not enlace: continue
                nombre = re.sub(r'\s+', ' ', enlace.inner_text()).strip()
                href   = enlace.get_attribute("href") or ""
                if href.startswith("/"): href = "https://romsfun.com" + href
                size   = celdas[-1].inner_text().strip()
                if nombre and href:
                    archivos.append({"nombre": nombre, "url": href, "size": size})

        return archivos, titulo

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page = ctx.new_page()

        # ── Despachar por sitio conocido ──
        titulo_detectado = ""
        if _es_romsfun(url):
            archivos, titulo_detectado = _scrape_romsfun(page, url, log)
        else:
            # ── Scraper genérico: abrir → buscar botón download → extraer tabla ──
            log(f"🌐 Abriendo: {url}")
            _navegar(page, url, espera=2)

            titulo_detectado = _extraer_titulo(page)
            if titulo_detectado:
                log(f"📌 Título: {titulo_detectado!r}")

            # Buscar botón/enlace de descarga
            for selector in [
                'a:has-text("Download ROM")', 'a:has-text("Download Game")',
                'a:has-text("Download")', 'button:has-text("Download")',
                '[class*="download"]:has-text("Download")',
            ]:
                try:
                    btn = page.locator(selector).first
                    if btn.count() > 0:
                        href = btn.get_attribute("href")
                        if href and href != "#":
                            dest = urljoin(page.url, href)
                            log(f"🖱️ Página de descarga: {dest}")
                            _navegar(page, dest, espera=2)
                        else:
                            btn.click()
                            time.sleep(2)
                        break
                except:
                    continue

            log(f"🔍 Extrayendo de: {page.url}")
            archivos = _extraer_tabla(page)

        # ── Fallback universal: buscar links por extensión ──
        if not archivos:
            log("🔄 Fallback: buscando links por extensión...")
            for a in page.query_selector_all("a[href]"):
                try:
                    href = a.get_attribute("href") or ""
                    if ext_re.search(href):
                        nombre = a.inner_text().strip() or href.split("/")[-1].split("?")[0]
                        archivos.append({"nombre": nombre, "url": urljoin(page.url, href), "size": ""})
                except:
                    pass

        browser.close()

    # Deduplicar
    vistos = set()
    unicos = []
    for a in archivos:
        if a["url"] not in vistos:
            vistos.add(a["url"])
            unicos.append(a)

    log(f"✅ {len(unicos)} archivos encontrados")
    return {"archivos": unicos, "titulo": titulo_detectado}

# ════════════════════════════════════════════
#  BOT PLAYWRIGHT
# ════════════════════════════════════════════
def bot_publicar(config: dict, datos: dict, progreso) -> bool:
    """
    Publica un post en Firepaste usando la API REST del bot.
    Requiere que en el .env de firepaste esté configurado BOT_API_TOKEN.
    config debe incluir:
      - url_panel   (ej: https://firepaste.com/admin)
      - bot_api_token
    datos debe incluir:
      - titulo, catalogo, pestana, contenido_html, is_vip (opcional)
    """
    import requests as _req

    # La base de la API se deriva de url_panel quitando /admin
    panel = config.get("url_panel", "").rstrip("/")
    # Intentar deducir la raíz: si termina en /admin, quitar eso
    if panel.endswith("/admin"):
        api_base = panel[:-6].rstrip("/") + "/api/bot"
    else:
        api_base = panel + "/api/bot"

    token = config.get("bot_api_token", "").strip()
    if not token:
        progreso(0, "❌ bot_api_token no configurado en Config → Plataformas"); return False

    headers = {
        "X-Bot-Token": token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        # 1. Verificar conexión listando catálogos
        progreso(20, "🔌 Conectando con la API de Firepaste...")
        r = _req.get(f"{api_base}/catalogs", headers=headers, timeout=10)
        if r.status_code == 401:
            progreso(0, "❌ Token inválido — revisa BOT_API_TOKEN en el .env de Firepaste"); return False
        if r.status_code == 404:
            progreso(0, "❌ API no encontrada — ¿instalaste el api.php y ApiPostController?"); return False
        r.raise_for_status()

        # 2. Verificar / crear catálogo
        cat = datos.get("catalogo", "").strip()
        if cat:
            progreso(40, f"📁 Verificando catálogo '{cat}'...")
            r2 = _req.post(f"{api_base}/catalogs", json={"nombre": cat}, headers=headers, timeout=10)
            r2.raise_for_status()
            resp2 = r2.json()
            accion = "creado" if resp2.get("created") else "encontrado"
            progreso(50, f"✅ Catálogo {accion}: {resp2.get('catalog', {}).get('nombre', cat)}")
        else:
            progreso(50, "⚠️ Sin catálogo asignado")

        # 3. Crear el post
        progreso(70, "📝 Publicando post...")
        payload = {
            "titulo":        datos.get("titulo", "").strip(),
            "catalogo":      cat,
            "pestana":       datos.get("pestana", "").strip(),
            "contenido":     datos.get("contenido_html", ""),
            "is_vip":        bool(datos.get("is_vip", False)),
            "is_published":  bool(datos.get("is_published", True)),
        }
        r3 = _req.post(f"{api_base}/posts", json=payload, headers=headers, timeout=15)
        if r3.status_code == 422:
            err = r3.json().get("error", "datos inválidos")
            progreso(0, f"❌ Error de validación: {err}"); return False
        r3.raise_for_status()
        resp3 = r3.json()

        url_post = resp3.get("url", "")
        progreso(100, f"🎉 ¡Publicado! → {url_post}")
        return True

    except _req.exceptions.ConnectionError:
        progreso(0, "❌ No se pudo conectar con Firepaste — verifica la URL"); return False
    except _req.exceptions.Timeout:
        progreso(0, "❌ Timeout — Firepaste tardó demasiado"); return False
    except Exception as e:
        progreso(0, f"❌ Error: {e}"); return False

# ════════════════════════════════════════════
#  API EXPUESTA AL JS
# ════════════════════════════════════════════
class API:
    def __init__(self):
        self._window = None  # se setea después

    # ── Config ──────────────────────────────
    def get_config(self):
        return load_json(CONFIG_FILE, DEFAULT_CONFIG)

    def save_config(self, cfg: dict):
        save_json(CONFIG_FILE, cfg)
        return {"ok": True}

    # ── Patrones ────────────────────────────
    def get_patrones(self):
        return load_json(PATTERNS_FILE, {"catalogos":{}, "sitios":{}, "total":0})

    def _aprender(self, post: dict):
        p = load_json(PATTERNS_FILE, {"catalogos":{}, "sitios":{}, "total":0})
        p["total"] = p.get("total", 0) + 1
        cat = post.get("catalogo","")
        if cat: p["catalogos"][cat] = p["catalogos"].get(cat,0) + 1
        sitio = post.get("sitio","")
        if sitio: p["sitios"][sitio] = p["sitios"].get(sitio,0) + 1
        save_json(PATTERNS_FILE, p)

    # ── Historial ───────────────────────────
    def get_historial(self):
        return load_json(HISTORY_FILE, [])

    def _guardar_historial(self, entry: dict):
        h = load_json(HISTORY_FILE, [])
        h.insert(0, entry)
        save_json(HISTORY_FILE, h[:200])

    def limpiar_historial(self):
        save_json(HISTORY_FILE, [])
        return {"ok": True}

    def limpiar_patrones(self):
        save_json(PATTERNS_FILE, {"catalogos": {}, "sitios": {}, "total": 0})
        return {"ok": True}

    # ── Config Cloud ────────────────────────


    def generar_tabla_directa(self, archivos: list) -> dict:
        """
        Genera tabla HTML con los links originales SIN descargar archivos.
        Ideal para publicar links de romsfun directamente en firepaste.
        """
        from uploader import build_tabla_directa
        try:
            tabla_html = build_tabla_directa(archivos)
            return {"ok": True, "tabla_html": tabla_html}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Descargar archivos con estructura de carpetas ──
    def descargar_juego(self, archivos: list, titulo: str, catalogo: str) -> dict:
        """
        Descarga los archivos organizándolos en:
          ~/firepaste_downloads/<catalogo>/<titulo>/<archivo>
        """
        from uploader import descargar_archivo

        def log(msg):
            try:
                if self._window:
                    self._window.evaluate_js(
                        f"window._logScrape && window._logScrape({json.dumps(msg)})"
                    )
            except: pass

        resultados = []
        def tarea():
            for i, archivo in enumerate(archivos):
                log(f"📦 [{i+1}/{len(archivos)}] {archivo['nombre']}")
                ruta = descargar_archivo(
                    archivo["url"], archivo["nombre"], log,
                    titulo_juego=titulo,
                    catalogo=catalogo
                )
                resultados.append({
                    "nombre": archivo["nombre"],
                    "ok": ruta is not None,
                    "ruta": str(ruta) if ruta else ""
                })
            log(f"✅ Descarga completa — {sum(1 for r in resultados if r['ok'])}/{len(resultados)} archivos")

        import threading
        t = threading.Thread(target=tarea)
        t.start(); t.join()
        return {"ok": True, "resultados": resultados}

    # ── Escanear URL ────────────────────────
    def escanear_url(self, url: str):
        try:
            def progreso(msg):
                try:
                    if self._window:
                        self._window.evaluate_js(
                            f"window._logScrape && window._logScrape({json.dumps(msg)})"
                        )
                except: pass

            # Para firepaste.com usamos el scraper especializado que también
            # extrae el título real de la página (h3).
            if _es_firepaste(url):
                resultado = _scrape_firepaste(url, progreso)
                return {
                    "archivos": resultado["archivos"],
                    "titulo":   resultado.get("titulo", ""),
                }

            resultado = scrape_url(url, progreso)
            return {
                "archivos": resultado["archivos"],
                "titulo":   resultado.get("titulo", ""),
            }
        except Exception as e:
            return {"error": str(e), "archivos": [], "titulo": ""}

    # ── Generar título automático (sin IA) ──
    def generar_ia(self, titulo: str, catalogo: str):
        """Genera título y pestaña automáticamente del nombre del archivo."""
        import re

        # Limpiar el nombre: quitar extensiones, guiones, corchetes típicos de ROMs
        limpio = titulo
        limpio = re.sub(r'\.(zip|rar|7z|rom|gba|gbc|nes|iso|bin|nds|sfc|smc|n64)$', '', limpio, flags=re.I)
        limpio = re.sub(r'\s*\(.*?\)', '', limpio)   # quitar (USA), (Europe), (Rev 1)...
        limpio = re.sub(r'\s*\[.*?\]', '', limpio)   # quitar [!], [T+Esp]...
        limpio = re.sub(r'[-_]', ' ', limpio)        # guiones → espacios
        limpio = re.sub(r'\s+', ' ', limpio).strip() # espacios dobles

        # Title case
        titulo_limpio = limpio.title() if limpio else titulo.title()

        # Pestaña según catálogo
        cat_lower = catalogo.lower()
        if any(x in cat_lower for x in ["gba","nes","snes","n64","nds","psx","ps2","rom"]):
            pestana = "ROM Download"
        elif any(x in cat_lower for x in ["pc","windows","steam"]):
            pestana = "PC Download"
        elif any(x in cat_lower for x in ["android","apk"]):
            pestana = "APK Download"
        else:
            pestana = "Free Download"

        return {
            "titulo": titulo_limpio,
            "pestana": pestana
        }

    # ── Publicar ────────────────────────────
    def publicar_post(self, datos: dict):
        cfg = self.get_config()
        if not cfg.get("bot_api_token", "").strip() or not cfg.get("url_panel", "").strip():
            return {"ok": False, "error": "Configura URL del panel y Bot API Token en Configuración"}

        resultado = {"ok": False, "error": ""}

        def progreso(pct, msg):
            # Enviar progreso al JS
            try:
                if self._window:
                    self._window.evaluate_js(
                        f"window._progreso && window._progreso({pct}, {json.dumps(msg)})"
                    )
            except: pass

        def tarea():
            ok = bot_publicar(cfg, datos, progreso)
            resultado["ok"] = ok
            if ok:
                entry = {**datos, "fecha": datetime.now().isoformat(),
                         "n_archivos": len(datos.get("contenido_html","").split("<tr>")) - 1}
                self._guardar_historial(entry)
                self._aprender(entry)
            else:
                if not resultado.get("error"):
                    resultado["error"] = "Error al publicar. Revisa la consola o verifica tu token."

        t = threading.Thread(target=tarea)
        t.start(); t.join()  # bloqueante para que JS espere el resultado
        return resultado

# ════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════
if __name__ == "__main__":
    api = API()
    ui_path = Path(__file__).parent / "ui" / "index.html"

    window = webview.create_window(
        title="🔥 Firepaste Bot",
        url=str(ui_path),
        js_api=api,
        width=1100,
        height=740,
        min_size=(900, 600),
        background_color="#0d1117",
    )
    api._window = window
    webview.start(debug=False)