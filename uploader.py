#!/usr/bin/env python3
"""
uploader.py — Descarga archivos y los sube a la nube
Soporta: GoFile (sin cuenta), MediaFire, Google Drive, Mega
"""
import os, time, json, re, requests
from pathlib import Path

DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


# ════════════════════════════════════════════
#  DESCARGA
# ════════════════════════════════════════════
def _resolver_url_real(url: str, log) -> str:
    """
    Si la URL es una página intermedia con countdown (ej. romsfun /download/game/1),
    usa Playwright para esperar a que aparezca el link real del .zip y lo devuelve.
    Si ya es un link directo a un archivo, lo devuelve tal cual.
    """
    ext_re = re.compile(
        r'\.(zip|rar|7z|rom|gba|gbc|nes|sfc|smc|n64|nds|iso|bin|z64|v64|xci|nsp|pkg|apk)(\?.*)?$',
        re.I
    )
    if ext_re.search(url.split("?")[0]):
        return url  # Ya es un link directo

    partes = url.rstrip("/").split("/")
    es_countdown = (
        "romsfun.com" in url and
        partes and partes[-1].isdigit()
    )

    if not es_countdown:
        return url

    log(f"⏳ Página con countdown, esperando link real: {url}")
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
                                    log(f"✅ Link obtenido del botón: {link_real[:80]}...")
                                    break
                except:
                    pass
                time.sleep(1)

            browser.close()

            if link_real:
                return link_real
    except Exception as e:
        log(f"⚠️ Error resolviendo countdown: {e}")

    return url


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
      ~/firepaste_downloads/<catalogo>/<titulo_juego>/<archivo>
    Si no se pasan catalogo/titulo_juego, va directo a firepaste_downloads/.
    """
    # Si la URL es una página con countdown, resolver el link real primero
    url = _resolver_url_real(url, log)

    # Limpiar nombre de archivo
    nombre_limpio = _limpiar_nombre(nombre)
    if nombre_limpio == "sin_nombre":
        nombre_limpio = url.split("/")[-1].split("?")[0] or "archivo"

    # Construir ruta con subcarpetas catalogo/titulo_juego
    carpeta = DOWNLOAD_DIR
    if catalogo:
        carpeta = carpeta / _limpiar_nombre(catalogo)
    if titulo_juego:
        carpeta = carpeta / _limpiar_nombre(titulo_juego)

    # FIX: crear carpeta con manejo explícito de errores
    try:
        carpeta.mkdir(parents=True, exist_ok=True)
        log(f"📁 Carpeta lista: {carpeta}")
    except Exception as e:
        log(f"❌ No se pudo crear la carpeta '{carpeta}': {e}")
        return None

    destino = carpeta / nombre_limpio
    if destino.exists():
        log(f"⚡ Ya existe localmente: {destino}")
        return destino

    log(f"⬇️  Descargando: {nombre_limpio} → {carpeta}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://romsfun.com/",
        }
        r = requests.get(url, headers=headers, stream=True, timeout=60, allow_redirects=True)
        r.raise_for_status()

        # FIX: detectar si nos devolvieron HTML en lugar de un archivo binario
        content_type = r.headers.get("Content-Type", "").lower()
        if "text/html" in content_type:
            log(f"❌ La URL devolvió una página HTML (no un archivo). Puede requerir autenticación o el link expiró.")
            log(f"   URL: {url}")
            return None

        # FIX: detectar redirección a página de error o login
        final_url = r.url
        if final_url != url and any(x in final_url for x in ["login", "error", "404", "expired"]):
            log(f"❌ Redirigido a página no válida: {final_url}")
            return None

        total = int(r.headers.get("content-length", 0))
        descargado = 0

        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
                    descargado += len(chunk)
                    if total:
                        pct = int(descargado / total * 100)
                        log(f"⬇️  {nombre_limpio}: {pct}% ({_fmt_size(descargado)}/{_fmt_size(total)})")
                    else:
                        # FIX: mostrar progreso aunque no haya content-length
                        log(f"⬇️  {nombre_limpio}: {_fmt_size(descargado)} descargados...")

        # FIX: verificar que el archivo descargado tiene tamaño razonable (>1KB)
        size_final = destino.stat().st_size
        if size_final < 1024:
            # Puede ser un HTML de error guardado como archivo
            try:
                contenido = destino.read_bytes()
                if b"<!DOCTYPE" in contenido[:200] or b"<html" in contenido[:200]:
                    log(f"❌ El archivo descargado es HTML (posible página de error). Eliminando.")
                    destino.unlink()
                    return None
            except:
                pass

        log(f"✅ Descargado: {nombre_limpio} ({_fmt_size(size_final)})")
        return destino

    except requests.exceptions.HTTPError as e:
        log(f"❌ Error HTTP {e.response.status_code} descargando {nombre_limpio}: {e}")
        if destino.exists():
            destino.unlink()
        return None
    except requests.exceptions.ConnectionError as e:
        log(f"❌ Error de conexión descargando {nombre_limpio}: {e}")
        if destino.exists():
            destino.unlink()
        return None
    except requests.exceptions.Timeout:
        log(f"❌ Timeout descargando {nombre_limpio} (60s). El archivo puede ser muy grande o el servidor lento.")
        if destino.exists():
            destino.unlink()
        return None
    except Exception as e:
        log(f"❌ Error descargando {nombre_limpio}: {e}")
        if destino.exists():
            destino.unlink()
        return None


def _fmt_size(b: int) -> str:
    for u in ["B","KB","MB","GB"]:
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


# ════════════════════════════════════════════
#  GOFILE — sin cuenta, gratis
# ════════════════════════════════════════════
def subir_gofile(ruta: Path, log, carpeta_nombre: str = "", api_token: str = "",
                 _estado: dict = None) -> dict | None:
    """
    Sube a GoFile usando la API 2025.
    - _estado: dict compartido entre llamadas del mismo juego para reutilizar
                guestToken y folderId (así todos los archivos van a la misma carpeta).
    - Con api_token: usa tu cuenta real y crea carpetas por nombre de juego.
    - Sin api_token: usa cuenta guest, agrupa por folderId en _estado.
    """
    log(f"☁️  Subiendo a GoFile: {ruta.name}")
    size = ruta.stat().st_size

    if _estado is None:
        _estado = {}

    try:
        upload_data = {}
        upload_headers = {}

        if api_token:
            upload_headers["Authorization"] = f"Bearer {api_token}"

            if "folder_id" not in _estado and carpeta_nombre:
                try:
                    r_id = requests.get(
                        "https://api.gofile.io/accounts/getid",
                        headers=upload_headers, timeout=10
                    )
                    account_id = r_id.json().get("data", {}).get("id", "")

                    if account_id:
                        r_info = requests.get(
                            f"https://api.gofile.io/accounts/{account_id}",
                            headers=upload_headers, timeout=10
                        )
                        root_id = r_info.json().get("data", {}).get("rootFolder", "")

                        if root_id:
                            r_folder = requests.post(
                                "https://api.gofile.io/contents/createFolder",
                                headers={**upload_headers, "Content-Type": "application/json"},
                                json={"parentFolderId": root_id, "folderName": carpeta_nombre},
                                timeout=10
                            )
                            fid = r_folder.json().get("data", {}).get("id", "")
                            if fid:
                                _estado["folder_id"] = fid
                                log(f"📁 Carpeta creada: {carpeta_nombre}")
                except Exception as e:
                    log(f"⚠️ No se pudo crear carpeta: {e}")

            if "folder_id" in _estado:
                upload_data["folderId"] = _estado["folder_id"]

        else:
            if "guest_token" in _estado:
                upload_data["token"] = _estado["guest_token"]
            if "folder_id" in _estado:
                upload_data["folderId"] = _estado["folder_id"]

        with open(ruta, "rb") as f:
            resp = requests.post(
                "https://upload.gofile.io/uploadfile",
                headers=upload_headers,
                data=upload_data,
                files={"file": (ruta.name, f)},
                timeout=300
            )

        result = resp.json()

        if result.get("status") == "ok":
            data = result["data"]

            if not api_token:
                if "guestToken" in data and "guest_token" not in _estado:
                    _estado["guest_token"] = data["guestToken"]
                    log(f"🎫 Guest token obtenido")
                if "parentFolder" in data:
                    parent = data["parentFolder"]
                    fid = parent.get("id") or parent.get("folderId", "")
                    if fid and "folder_id" not in _estado:
                        _estado["folder_id"] = fid

            link = data.get("downloadPage", "")
            if not link:
                fid = (data.get("parentFolder") or {}).get("id") or _estado.get("folder_id", "")
                if fid:
                    link = f"https://gofile.io/d/{fid}"

            log(f"✅ GoFile: {link}")
            return {"url": link, "nombre": ruta.name, "size": _fmt_size(size), "plataforma": "GoFile"}

        else:
            log(f"⚠️ GoFile error: {result}")
            return None

    except Exception as e:
        log(f"❌ GoFile falló: {e}")
        return None


# ════════════════════════════════════════════
#  MEDIAFIRE — necesita email + password
# ════════════════════════════════════════════
def subir_mediafire(ruta: Path, email: str, password: str, log) -> dict | None:
    log(f"☁️  Subiendo a MediaFire: {ruta.name}")
    try:
        from mediafire import MediaFireClient
        client = MediaFireClient()
        client.login(email=email, password=password, app_id="42511")

        destino_remoto = f"firepaste/{ruta.name}"
        client.upload_file(str(ruta), destino_remoto)

        result = client.get_links(destino_remoto, link_type="direct_download")
        links = result.get("links", [])
        if links:
            url = links[0].get("direct_download", links[0].get("normal_download",""))
            log(f"✅ MediaFire: {url}")
            return {"url": url, "nombre": ruta.name, "size": _fmt_size(ruta.stat().st_size), "plataforma": "MediaFire"}
        return None
    except ImportError:
        log("❌ Instala: pip install mediafire")
        return None
    except Exception as e:
        log(f"❌ MediaFire falló: {e}")
        return None


# ════════════════════════════════════════════
#  GOOGLE DRIVE — necesita credenciales OAuth
# ════════════════════════════════════════════
def subir_drive(ruta: Path, token_file: str, log) -> dict | None:
    log(f"☁️  Subiendo a Google Drive: {ruta.name}")
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import pickle

        SCOPES = ["https://www.googleapis.com/auth/drive.file"]
        creds = None
        token_path = Path(token_file)

        if token_path.exists():
            with open(token_path, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, "wb") as f:
                pickle.dump(creds, f)

        service = build("drive", "v3", credentials=creds)
        meta = {"name": ruta.name}
        media = MediaFileUpload(str(ruta), resumable=True)
        archivo = service.files().create(body=meta, media_body=media, fields="id").execute()
        file_id = archivo.get("id")

        service.permissions().create(fileId=file_id, body={"type":"anyone","role":"reader"}).execute()
        url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        log(f"✅ Drive: {url}")
        return {"url": url, "nombre": ruta.name, "size": _fmt_size(ruta.stat().st_size), "plataforma": "Google Drive"}

    except ImportError:
        log("❌ Instala: pip install google-api-python-client google-auth-oauthlib")
        return None
    except Exception as e:
        log(f"❌ Google Drive falló: {e}")
        return None


# ════════════════════════════════════════════
#  MEGA — necesita email + password
# ════════════════════════════════════════════
def subir_mega(ruta: Path, email: str, password: str, log) -> dict | None:
    log(f"☁️  Subiendo a Mega: {ruta.name}")
    try:
        from mega import Mega
        mega = Mega()
        m = mega.login(email, password)
        archivo = m.upload(str(ruta))
        url = m.get_upload_link(archivo)
        log(f"✅ Mega: {url}")
        return {"url": url, "nombre": ruta.name, "size": _fmt_size(ruta.stat().st_size), "plataforma": "Mega"}
    except ImportError:
        log("❌ Instala: pip install mega.py")
        return None
    except Exception as e:
        log(f"❌ Mega falló: {e}")
        return None


# ════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL — descarga + sube todo
# ════════════════════════════════════════════
def procesar_archivos(archivos: list, config_cloud: dict, log) -> list:
    plataformas = config_cloud.get("plataformas", ["gofile"])
    resultados = []
    gofile_estado = {}

    for i, archivo in enumerate(archivos):
        log(f"\n📦 [{i+1}/{len(archivos)}] {archivo['nombre']}")

        ruta_local = descargar_archivo(
            archivo["url"], archivo["nombre"], log,
            titulo_juego=config_cloud.get("titulo_juego", ""),
            catalogo=config_cloud.get("catalogo", "")
        )
        if not ruta_local:
            resultados.append({
                "nombre": archivo["nombre"],
                "size": archivo.get("size", ""),
                "links": [],
                "error": "Fallo la descarga"
            })
            continue

        links_subidos = []

        if "gofile" in plataformas:
            carpeta = config_cloud.get("titulo_juego", "") or archivo.get("nombre", "")
            token   = config_cloud.get("gofile_token", "")
            r = subir_gofile(ruta_local, log, carpeta_nombre=carpeta,
                             api_token=token, _estado=gofile_estado)
            if r: links_subidos.append(r)

        if "mediafire" in plataformas:
            r = subir_mediafire(
                ruta_local,
                config_cloud.get("mediafire_email",""),
                config_cloud.get("mediafire_pass",""),
                log
            )
            if r: links_subidos.append(r)

        if "mega" in plataformas:
            r = subir_mega(
                ruta_local,
                config_cloud.get("mega_email",""),
                config_cloud.get("mega_pass",""),
                log
            )
            if r: links_subidos.append(r)

        if "drive" in plataformas:
            r = subir_drive(
                ruta_local,
                config_cloud.get("drive_token", str(Path.home() / ".firepaste_drive.pkl")),
                log
            )
            if r: links_subidos.append(r)

        resultados.append({
            "nombre": archivo["nombre"],
            "size": archivo.get("size","") or _fmt_size(ruta_local.stat().st_size),
            "links": links_subidos
        })

        log(f"✅ {archivo['nombre']} → {len(links_subidos)} links generados")

    return resultados


# ════════════════════════════════════════════
#  GENERAR TABLA HTML con múltiples links
# ════════════════════════════════════════════
def build_tabla_resultados(resultados: list) -> str:
    plataformas = []
    for r in resultados:
        for l in r.get("links", []):
            p = l.get("plataforma","")
            if p and p not in plataformas:
                plataformas.append(p)

    iconos = {
        "GoFile": "🟠 GoFile",
        "MediaFire": "🔵 MediaFire",
        "Mega": "🔴 Mega",
        "Google Drive": "🟢 Drive"
    }

    th_first = 'style="box-sizing:border-box;vertical-align:middle;font-size:16px;font-weight:bold;padding:11px 15px;color:rgb(255,255,255);background:rgb(41,46,59);border-right:1px solid rgb(30,33,42);text-align:center;border-radius:16px 0px 0px 0px;"'
    th_mid   = 'style="box-sizing:border-box;vertical-align:middle;font-size:16px;font-weight:bold;padding:11px 15px;color:rgb(255,255,255);background:rgb(41,46,59);border-right:1px solid rgb(30,33,42);text-align:center;"'
    th_last  = 'style="box-sizing:border-box;vertical-align:middle;font-size:16px;font-weight:bold;padding:11px 15px;color:rgb(255,255,255);background:rgb(41,46,59);border-right:none;text-align:center;border-radius:0px 16px 0px 0px;"'

    all_cols = ["File Name", "Size"] + [iconos.get(p, p) for p in plataformas]
    header_cells = ""
    for idx, col in enumerate(all_cols):
        if idx == 0:
            header_cells += f"<th {th_first}><p><strong>{col}</strong></p></th>"
        elif idx == len(all_cols) - 1:
            header_cells += f"<th {th_last}><p><strong>{col}</strong></p></th>"
        else:
            header_cells += f"<th {th_mid}><p><strong>{col}</strong></p></th>"

    td_name = 'style="box-sizing:border-box;vertical-align:middle;font-size:14px;font-weight:bold;padding:10px 15px;position:relative;text-align:left;border-right:1px solid rgb(223,223,223);background:transparent;"'
    td_muted = 'style="box-sizing:border-box;vertical-align:middle;font-size:14px;font-weight:bold;padding:10px 15px;position:relative;color:rgb(108,117,125);text-align:left;border-right:1px solid rgb(223,223,223);background:transparent;"'
    td_link_last = 'style="box-sizing:border-box;vertical-align:middle;font-size:14px;font-weight:bold;padding:10px 15px;position:relative;text-align:center;border-right:none;background:transparent;"'

    filas = ""
    for r in resultados:
        links_map = {l["plataforma"]: l["url"] for l in r.get("links", [])}
        celdas_links = ""
        for idx_p, p in enumerate(plataformas):
            url = links_map.get(p, "")
            is_last = (idx_p == len(plataformas) - 1)
            cell_style = td_link_last if is_last else td_muted
            if url:
                celdas_links += f'<td {cell_style}><p><a href="{url}" target="_blank" rel="nofollow"><strong>⬇ Descargar</strong></a></p></td>'
            else:
                celdas_links += f"<td {cell_style}><p>—</p></td>"

        filas += f"""
        <tr>
          <td {td_name}><p><strong>{r['nombre']}</strong></p></td>
          <td {td_muted}><p>{r.get('size','—')}</p></td>
          {celdas_links}
        </tr>"""

    return f"""<table class="table table-striped mb-4" style="box-sizing:border-box;border-collapse:separate;border-spacing:0px;width:100%;border:1px solid rgb(223,223,223);border-radius:16px;overflow:hidden;margin:0px 0px 24px;flex:1 1 0%;font-family:Rubik,Arial,Helvetica,sans-serif;">
  <colgroup><col style="min-width:25px"><col style="min-width:25px"></colgroup>
  <tbody>
    <tr>{header_cells}</tr>
    {filas}
  </tbody>
</table>"""


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