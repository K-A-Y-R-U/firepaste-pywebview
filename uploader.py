#!/usr/bin/env python3
"""
uploader.py — Descarga archivos y genera tabla HTML
"""
import os, time, re, requests
from pathlib import Path

DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


# ════════════════════════════════════════════
#  DESCARGA
# ════════════════════════════════════════════
def _resolver_url_real(url: str, log) -> str:
    """
    Si la URL es página con countdown de romsfun (/download/game/N),
    usa Playwright para esperar el link real y lo devuelve inmediatamente.
    El link tiene token de corta duración, así que hay que usarlo rápido.
    """
    ext_re = re.compile(
        r'\.(zip|rar|7z|rom|gba|gbc|nes|sfc|smc|n64|nds|iso|bin|z64|v64|xci|nsp|pkg|apk)(\?.*)?$',
        re.I
    )
    if ext_re.search(url.split("?")[0]):
        return url  # Ya es link directo

    partes = url.rstrip("/").split("/")
    es_countdown = (
        "romsfun.com" in url and
        partes and partes[-1].isdigit()
    )

    if not es_countdown:
        return url

    log(f"⏳ Esperando link real (countdown 7s): {url}")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
            except:
                pass

            link_real = None
            for _ in range(30):
                try:
                    el = page.query_selector("#download-link[href]")
                    if el:
                        link_real = el.get_attribute("href")
                        if link_real and ("statics.romsfun" in link_real or ext_re.search(link_real)):
                            log(f"✅ Link real obtenido: {link_real[:80]}...")
                            break
                    btn_div = page.query_selector("#download-button")
                    if btn_div:
                        style = btn_div.get_attribute("class") or ""
                        if "hidden" not in style:
                            el2 = btn_div.query_selector("a[href]")
                            if el2:
                                link_real = el2.get_attribute("href")
                                if link_real and "statics.romsfun" in link_real:
                                    log(f"✅ Link del botón: {link_real[:80]}...")
                                    break
                except:
                    pass
                time.sleep(1)

            browser.close()

            if link_real:
                return link_real
    except Exception as e:
        log(f"⚠️ Error countdown: {e}")

    return url


def _descargar_con_token(url: str, destino: Path, log) -> bool:
    """
    Descarga una URL con token de corta duración (statics.romsfun.com).
    Usa requests con el Referer correcto y reintenta si el token falla.
    """
    HEADERS_ROMSFUN = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer":    "https://romsfun.com/",
        "Accept":     "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(url, headers=HEADERS_ROMSFUN, stream=True,
                         timeout=120, allow_redirects=True)
        r.raise_for_status()

        content_type = r.headers.get("Content-Type", "").lower()
        if "text/html" in content_type:
            log(f"❌ Token expirado o link inválido (devolvió HTML)")
            return False

        total = int(r.headers.get("content-length", 0))
        descargado = 0
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=512 * 1024):
                if chunk:
                    f.write(chunk)
                    descargado += len(chunk)
                    if total:
                        log(f"⬇️  {destino.name}: {int(descargado/total*100)}% ({_fmt_size(descargado)}/{_fmt_size(total)})")
                    else:
                        log(f"⬇️  {destino.name}: {_fmt_size(descargado)}...")

        size_final = destino.stat().st_size
        if size_final < 1024:
            contenido = destino.read_bytes()
            if b"<!DOCTYPE" in contenido[:200] or b"<html" in contenido[:200]:
                log(f"❌ Archivo es HTML (error del servidor). Eliminando.")
                destino.unlink()
                return False

        log(f"✅ Descargado: {destino.name} ({_fmt_size(size_final)})")
        return True

    except Exception as e:
        log(f"❌ Error descargando: {e}")
        if destino.exists():
            destino.unlink()
        return False


def _limpiar_nombre(nombre) -> str:
    """Limpia un nombre para usarlo como carpeta o archivo."""
    # FIX: proteger contra None y tipos no-string
    if not nombre:
        return "sin_nombre"
    nombre = str(nombre).strip()
    if not nombre:
        return "sin_nombre"
    limpio = "".join(c for c in nombre if c.isalnum() or c in " .-_()[]").strip()
    return limpio or "sin_nombre"


def descargar_archivo(url: str, nombre: str, log,
                      titulo_juego: str = "", catalogo: str = "") -> Path | None:
    """
    Descarga un archivo organizándolo en:
      <DOWNLOAD_DIR>/<catalogo>/<titulo_juego>/<archivo>
    """
    # Resolver countdown ANTES de construir la ruta
    url_real = _resolver_url_real(url, log)

    nombre_limpio = _limpiar_nombre(nombre)
    if nombre_limpio == "sin_nombre":
        nombre_limpio = url_real.split("/")[-1].split("?")[0] or "archivo"

    # Construir ruta con subcarpetas
    carpeta = DOWNLOAD_DIR
    if catalogo:
        carpeta = carpeta / _limpiar_nombre(catalogo)
    if titulo_juego:
        carpeta = carpeta / _limpiar_nombre(titulo_juego)

    try:
        carpeta.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log(f"❌ No se pudo crear carpeta '{carpeta}': {e}")
        return None

    destino = carpeta / nombre_limpio
    if destino.exists():
        log(f"⚡ Ya existe: {carpeta.name}/{nombre_limpio}")
        return destino

    log(f"⬇️  Descargando: {nombre_limpio}")

    # Usar helper especial para links con token (statics.romsfun.com, etc.)
    if "statics.romsfun" in url_real or ("romsfun.com" not in url_real and url_real != url):
        ok = _descargar_con_token(url_real, destino, log)
        return destino if ok and destino.exists() else None

    # Descarga estándar para otros sitios
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://romsfun.com/",
        }
        r = requests.get(url_real, headers=headers, stream=True, timeout=120, allow_redirects=True)
        r.raise_for_status()

        content_type = r.headers.get("Content-Type", "").lower()
        if "text/html" in content_type:
            log(f"❌ La URL devolvió HTML (token expirado o requiere autenticación)")
            return None

        total = int(r.headers.get("content-length", 0))
        descargado = 0
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=512 * 1024):
                if chunk:
                    f.write(chunk)
                    descargado += len(chunk)
                    if total:
                        log(f"⬇️  {nombre_limpio}: {int(descargado/total*100)}% ({_fmt_size(descargado)}/{_fmt_size(total)})")
                    else:
                        log(f"⬇️  {nombre_limpio}: {_fmt_size(descargado)}...")

        size_final = destino.stat().st_size
        if size_final < 1024:
            contenido = destino.read_bytes()
            if b"<!DOCTYPE" in contenido[:200] or b"<html" in contenido[:200]:
                log(f"❌ Archivo descargado es HTML (error). Eliminando.")
                destino.unlink()
                return None

        log(f"✅ Descargado: {nombre_limpio} ({_fmt_size(size_final)})")
        return destino

    except requests.exceptions.HTTPError as e:
        log(f"❌ HTTP {e.response.status_code}: {nombre_limpio}")
    except requests.exceptions.Timeout:
        log(f"❌ Timeout (120s): {nombre_limpio}")
    except Exception as e:
        log(f"❌ Error: {e}")

    if destino.exists():
        destino.unlink()
    return None


def _fmt_size(b: int) -> str:
    for u in ["B","KB","MB","GB"]:
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


# ════════════════════════════════════════════
#  GENERAR TABLA HTML con links directos
# ════════════════════════════════════════════
def build_tabla_directa(archivos: list) -> str:
    th_first = 'style="box-sizing:border-box;vertical-align:middle;font-size:16px;font-weight:bold;padding:11px 15px;color:rgb(255,255,255);background:rgb(41,46,59);border-right:1px solid rgb(30,33,42);text-align:center;border-radius:16px 0px 0px 0px;"'
    th_last  = 'style="box-sizing:border-box;vertical-align:middle;font-size:16px;font-weight:bold;padding:11px 15px;color:rgb(255,255,255);background:rgb(41,46,59);border-right:none;text-align:center;border-radius:0px 16px 0px 0px;"'
    td_name  = 'style="box-sizing:border-box;vertical-align:middle;font-size:14px;font-weight:bold;padding:10px 15px;position:relative;text-align:left;border-right:1px solid rgb(223,223,223);background:transparent;"'
    td_size  = 'style="box-sizing:border-box;vertical-align:middle;font-size:14px;font-weight:bold;padding:10px 15px;position:relative;color:rgb(108,117,125);text-align:left;border-right:none;background:transparent;"'

    filas = ""
    for a in archivos:
        nombre = a.get("nombre", "")
        size   = a.get("size", "—")
        url    = a.get("url", "")
        if url:
            celda_nombre = f'<a href="{url}" target="_blank" rel="nofollow"><strong>{nombre}</strong></a>'
        else:
            celda_nombre = f"<strong>{nombre}</strong>"
        filas += f"<tr><td {td_name}><p>{celda_nombre}</p></td><td {td_size}><p>{size}</p></td></tr>\n"

    return f"""<table class="table table-striped mb-4" style="box-sizing:border-box;border-collapse:separate;border-spacing:0px;width:100%;border:1px solid rgb(223,223,223);border-radius:16px;overflow:hidden;margin:0px 0px 24px;flex:1 1 0%;font-family:Rubik,Arial,Helvetica,sans-serif;">
<colgroup><col style="min-width:25px"><col style="min-width:25px"></colgroup>
<tbody>
<tr>
  <th {th_first}><p><strong>File Name</strong></p></th>
  <th {th_last}><p><strong>Size</strong></p></th>
</tr>
{filas}</tbody>
</table>"""