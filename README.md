# 🔥 Firepaste Bot — PyWebView

> Herramienta de escritorio para automatizar la publicación de posts en [Firepaste.com](https://firepaste.com), con scraping inteligente de sitios de ROMs y subida automática a múltiples plataformas cloud.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![PyWebView](https://img.shields.io/badge/PyWebView-5.x-orange)
![Playwright](https://img.shields.io/badge/Playwright-Chromium-green?logo=playwright)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 📋 Tabla de Contenidos

- [¿Qué hace?](#-qué-hace)
- [Arquitectura](#-arquitectura)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Configuración](#-configuración)
- [Sitios soportados](#-sitios-soportados)
- [Plataformas cloud](#-plataformas-cloud)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [API interna (JS ↔ Python)](#-api-interna-js--python)

---

## ✨ ¿Qué hace?

**Firepaste Bot** es una aplicación de escritorio que combina una interfaz web (HTML/JS) con un backend Python. Permite:

1. **Escanear** una URL de un sitio de ROMs o de firepaste.com y extraer automáticamente la lista de archivos disponibles (nombre, URL, tamaño).
2. **Descargar** esos archivos localmente.
3. **Re-subir** los archivos a servicios cloud (GoFile, MediaFire, Mega, Google Drive).
4. **Generar** una tabla HTML con los links formateada según el estilo de Firepaste.
5. **Publicar** el post directamente en Firepaste vía la API REST del bot, con título, catálogo y pestaña.
6. **Llevar un historial** de todos los posts publicados y aprender patrones de catálogos/sitios usados frecuentemente.

---

## 🏗 Arquitectura

```
firepaste-pywebview/
│
├── main.py          # Backend Python: scraper + API expuesta al JS
├── uploader.py      # Descarga de archivos + subida a plataformas cloud
│
└── ui/
    └── index.html   # Frontend completo (HTML + CSS + JS vanilla)
```

La aplicación usa **PyWebView** para abrir una ventana nativa del SO que renderiza `index.html`. El JavaScript del frontend llama a métodos Python directamente a través del objeto `window.pywebview.api`, sin servidor HTTP de por medio.

```
[HTML/JS UI]  ←→  pywebview.api.*  ←→  [Python backend]
                                              ├── requests / BeautifulSoup  (scraping liviano)
                                              ├── Playwright + Chromium      (scraping JS-heavy)
                                              └── GoFile / MediaFire / Mega / Drive API
```

---

## ⚙️ Requisitos

- Python 3.10 o superior
- Fedora Linux (el script `instalar.sh` usa `dnf`) — adaptable a Debian/Ubuntu con `apt`
- Conexión a internet

### Dependencias Python

| Paquete | Uso |
|---|---|
| `pywebview` | Ventana de escritorio con WebKit |
| `requests` | HTTP liviano para scraping y APIs |
| `beautifulsoup4` | Parsing de HTML estático |
| `playwright` | Scraping de sitios con JavaScript |
| `mediafire` | Subida a MediaFire *(opcional)* |
| `mega.py` | Subida a Mega.nz *(opcional)* |
| `google-api-python-client` | Subida a Google Drive *(opcional)* |

---

## 🚀 Instalación

### Instalación rápida (Fedora/RHEL)

```bash
git clone https://github.com/TU_USUARIO/firepaste-pywebview.git
cd firepaste-pywebview
chmod +x instalar.sh
./instalar.sh
```

El script `instalar.sh` instala automáticamente todas las dependencias del sistema y de Python, incluyendo el binario de Chromium para Playwright.

### Instalación manual

```bash
# Dependencias del sistema (Fedora)
sudo dnf install -y python3-pip python3-devel \
  webkit2gtk4.1 webkit2gtk4.1-devel \
  gobject-introspection gobject-introspection-devel \
  gtk3 gtk3-devel cairo-devel

# Dependencias Python
pip3 install --user pywebview requests beautifulsoup4 playwright

# Chromium para Playwright
python3 -m playwright install chromium
```

### Instalación en Windows

> La app fue desarrollada en Linux, pero puede correr en Windows con algunas dependencias adicionales.

**1. Instala Python 3.10+**
Descarga desde → https://www.python.org/downloads/windows/
Durante la instalación marca ✅ **"Add Python to PATH"**

**2. Instala las dependencias**
Abre **PowerShell** o **CMD** y ejecuta:

```powershell
pip install pywebview requests beautifulsoup4 playwright
python -m playwright install chromium
```

**3. Instala el runtime de WebKit para PyWebView**
PyWebView en Windows usa Edge WebView2. Descárgalo desde:
→ https://developer.microsoft.com/en-us/microsoft-edge/webview2/

**4. Ejecuta la app**
```powershell
cd C:\ruta\a\firepaste-pywebview
python main.py
```

> **Nota:** Los scripts `instalar.sh` y `abrir.sh` son solo para Linux. En Windows usa los comandos de arriba directamente.

---

### Instalación manual (Ubuntu/Debian)

```bash
sudo apt install -y python3-pip python3-dev \
  libwebkit2gtk-4.0-dev libgtk-3-dev

pip3 install --user pywebview requests beautifulsoup4 playwright
python3 -m playwright install chromium
```

---

## ▶️ Uso

```bash
./abrir.sh
# o directamente:
python3 main.py
```

Se abrirá una ventana de escritorio con la interfaz del bot.

### Flujo básico

1. Ve a **Configuración** e ingresa la URL de tu panel de Firepaste y el `BOT_API_TOKEN`.
2. En la pantalla principal, pega la URL del sitio que quieres escanear.
3. El bot extrae la lista de archivos automáticamente.
4. Completa el título, catálogo y pestaña (o usa el **autocompletado inteligente**).
5. Elige si publicar los links directamente o descargar y re-subir a cloud primero.
6. Haz clic en **Publicar** — el post aparecerá en Firepaste en segundos.

---

## 🔧 Configuración

Los datos se guardan en archivos JSON en el directorio home del usuario:

| Archivo | Contenido |
|---|---|
| `~/.firepaste_config.json` | URL del panel, credenciales de cloud, token del bot |
| `~/.firepaste_history.json` | Historial de posts publicados (máx. 200) |
| `~/.firepaste_patterns.json` | Patrones aprendidos de catálogos y sitios |

### Parámetros de configuración principales

```json
{
  "url_panel": "https://firepaste.com/admin",
  "bot_api_token": "TU_TOKEN_AQUI",
  "headless": false
}
```

El `bot_api_token` se configura en el archivo `.env` de tu instalación de Firepaste con la variable `BOT_API_TOKEN`.

---

## 🌐 Sitios soportados

| Sitio | Método | Notas |
|---|---|---|
| **firepaste.com** | `requests` + BeautifulSoup | Scraping directo de HTML estático |
| **romsfun.com** | `requests` + BeautifulSoup + Playwright | Soporta páginas de juego, listas y countdowns |
| **Sitios genéricos** | Playwright (Chromium headless) | Detecta tablas de archivos y links por extensión |

El scraper detecta automáticamente el sitio y usa la estrategia más eficiente. Para sitios con JavaScript (countdowns, carga dinámica), recurre a Playwright con Chromium.

---

## ☁️ Plataformas cloud

| Plataforma | Requiere cuenta | Configuración |
|---|---|---|
| **GoFile** | No (guest) / Opcional | Token GoFile para carpetas organizadas |
| **MediaFire** | Sí | Email + contraseña |
| **Mega.nz** | Sí | Email + contraseña |
| **Google Drive** | Sí | `credentials.json` de Google Cloud Console |

Los archivos subidos a GoFile sin cuenta se agrupan en la misma carpeta usando el `guestToken` y `folderId` compartidos entre archivos del mismo juego.

---

## 📁 Estructura del proyecto

```
firepaste-pywebview/
├── main.py              # Backend principal
│   ├── _es_firepaste()      # Detecta URLs de firepaste.com
│   ├── _scrape_firepaste()  # Scraper liviano para firepaste.com
│   ├── scrape_url()         # Scraper unificado (despacha por sitio)
│   ├── bot_publicar()       # Publica post via API REST
│   └── API (clase)          # Métodos expuestos al frontend JS
│
├── uploader.py          # Módulo de descarga y subida
│   ├── descargar_archivo()  # Descarga con barra de progreso
│   ├── subir_gofile()       # Upload a GoFile (con/sin cuenta)
│   ├── subir_mediafire()    # Upload a MediaFire
│   ├── subir_mega()         # Upload a Mega.nz
│   ├── subir_drive()        # Upload a Google Drive
│   ├── procesar_archivos()  # Orquesta descarga + subida de toda la lista
│   ├── build_tabla_resultados()  # HTML con links de cloud
│   └── build_tabla_directa()    # HTML con links originales
│
├── ui/
│   └── index.html       # Interfaz completa (SPA vanilla JS)
│
├── instalar.sh          # Instalador para Fedora/RHEL
└── abrir.sh             # Lanzador rápido
```

---

## 🔌 API interna (JS ↔ Python)

El frontend llama a estos métodos Python via `window.pywebview.api.*`:

| Método | Descripción |
|---|---|
| `get_config()` | Carga la configuración guardada |
| `save_config(cfg)` | Guarda la configuración |
| `escanear_url(url)` | Escanea una URL y devuelve `{archivos, titulo}` |
| `generar_ia(titulo, catalogo)` | Genera título limpio y pestaña automáticamente |
| `generar_tabla_directa(archivos)` | Genera tabla HTML con links originales |
| `publicar_post(datos)` | Publica el post en Firepaste via API REST |
| `get_historial()` | Devuelve el historial de publicaciones |
| `limpiar_historial()` | Borra el historial |
| `get_patrones()` | Devuelve los patrones aprendidos |
| `limpiar_patrones()` | Reinicia los patrones |

El progreso en tiempo real se envía al JS via `window.evaluate_js()` llamando a callbacks globales (`window._logScrape`, `window._progreso`).

---

## 📝 Notas

- Los archivos descargados se guardan en `~/firepaste_downloads/`. Si un archivo ya existe, se reutiliza (caché local).
- El historial guarda los últimos 200 posts publicados.
- La generación de título/pestaña limpia nombres de ROMs: elimina extensiones, códigos de región `(USA)`, tags `[!]`, y aplica Title Case.
- El modo **tabla directa** (sin descargar) es útil para publicar links externos de romsfun directamente en Firepaste sin pasar por cloud.

---

## 📄 Licencia

MIT © 2025
