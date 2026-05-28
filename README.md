<div align="center">

```
███████╗██╗██████╗ ███████╗██████╗  █████╗ ███████╗████████╗███████╗
██╔════╝██║██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝╚══██╔══╝██╔════╝
█████╗  ██║██████╔╝█████╗  ██████╔╝███████║███████╗   ██║   █████╗  
██╔══╝  ██║██╔══██╗██╔══╝  ██╔═══╝ ██╔══██║╚════██║   ██║   ██╔══╝  
██║     ██║██║  ██║███████╗██║     ██║  ██║███████║   ██║   ███████╗
╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝
                                                                      
██████╗  ██████╗ ████████╗                                            
██╔══██╗██╔═══██╗╚══██╔══╝                                            
██████╔╝██║   ██║   ██║                                               
██╔══██╗██║   ██║   ██║                                               
██████╔╝╚██████╔╝   ██║                                               
╚═════╝  ╚═════╝    ╚═╝                                               
```

### 🔥 Coded with ☕ coffee & 🌿 good vibes

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyWebView](https://img.shields.io/badge/PyWebView-Desktop-FF6B35?style=for-the-badge&logo=windowsterminal&logoColor=white)](https://pywebview.flowrl.com)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium-45BA4B?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev)
[![GitHub](https://img.shields.io/badge/GitHub-K--A--Y--R--U-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/K-A-Y-R-U)

> *Hecho a las 2am con café cargado y buena música 🎵*  
> *Automatiza tus posts en Firepaste mientras te relajas 😎*

</div>

---

## 🌿 ¿Qué hace este bicho?

**Firepaste Bot** es una app de escritorio que te permite:

- 🕷️ **Scrapear** cualquier sitio de ROMs y extraer la lista de archivos automáticamente
- ☁️ **Re-subir** los archivos a GoFile, MediaFire, Mega o Google Drive
- 📝 **Publicar** posts en Firepaste con tabla HTML formateada y todo
- 🧠 **Aprender** tus patrones de catálogos y sitios favoritos
- 📜 **Historial** de todo lo que has publicado

Todo desde una ventana de escritorio. Sin terminal. Sin drama. ✌️

---

## 🏗️ Cómo está armado

```
firepaste-pywebview/
│
├── 🐍 main.py          → Backend Python (scraper + API para el JS)
├── ☁️  uploader.py      → Descarga archivos y los sube a la nube
│
└── 🎨 ui/
    └── index.html      → Frontend completo (HTML + CSS + JS vanilla)
```

**PyWebView** abre una ventana nativa que renderiza `index.html`.  
El JS llama métodos Python directamente via `window.pywebview.api` — sin servidor, sin complicaciones.

```
[HTML/JS UI]  ←→  pywebview.api  ←→  [Python]
                                         ├── requests + BeautifulSoup  (sitios estáticos)
                                         ├── Playwright + Chromium      (sitios con JS)
                                         └── GoFile / MediaFire / Mega / Drive
```

---

## ⚙️ Requisitos

- 🐍 Python 3.10+
- 🌐 Conexión a internet
- ☕ Un café (opcional pero recomendado)

| Paquete | Para qué |
|---|---|
| `pywebview` | Ventana de escritorio |
| `requests` | HTTP y APIs |
| `beautifulsoup4` | Parsear HTML |
| `playwright` | Sitios con JavaScript |
| `mediafire` | Subida a MediaFire *(opcional)* |
| `mega.py` | Subida a Mega.nz *(opcional)* |
| `google-api-python-client` | Subida a Google Drive *(opcional)* |

---

## 🚀 Instalación

### 🐧 Linux — Fedora/RHEL (instalación rápida)

```bash
git clone https://github.com/K-A-Y-R-U/firepaste-pywebview.git
cd firepaste-pywebview
chmod +x instalar.sh
./instalar.sh
```

El script instala todo solo: dependencias del sistema, paquetes Python y Chromium para Playwright.

### 🐧 Linux — Ubuntu/Debian

```bash
sudo apt install -y python3-pip python3-dev libwebkit2gtk-4.0-dev libgtk-3-dev

pip3 install --user pywebview requests beautifulsoup4 playwright
python3 -m playwright install chromium
```

### 🪟 Windows

> La app fue desarrollada en Linux pero corre bien en Windows.

**1.** Instala Python 3.10+ desde → https://www.python.org/downloads/windows/  
*(marca ✅ "Add Python to PATH" durante la instalación)*

**2.** Abre PowerShell y ejecuta:

```powershell
pip install pywebview requests beautifulsoup4 playwright
python -m playwright install chromium
```

**3.** Instala el runtime **Edge WebView2** (necesario para PyWebView en Windows):  
→ https://developer.microsoft.com/en-us/microsoft-edge/webview2/

**4.** Lanza la app:

```powershell
cd C:\ruta\a\firepaste-pywebview
python main.py
```

> Los scripts `instalar.sh` y `abrir.sh` son solo para Linux. En Windows usa los comandos de arriba.

---

## ▶️ Uso

```bash
# Linux
./abrir.sh

# O directamente
python3 main.py
```

### Flujo básico

```
1. 🔧 Configuración  →  URL del panel + BOT_API_TOKEN
2. 🔗 Pega la URL   →  del sitio que quieres scrapear
3. 🕷️ Escanear      →  extrae lista de archivos automáticamente
4. ✏️  Completar     →  título, catálogo, pestaña (o usa el autocompletado)
5. ☁️  Subir         →  a cloud o publicar links directos
6. 🚀 Publicar      →  el post aparece en Firepaste al instante
```

---

## 🌐 Sitios soportados

| Sitio | Método | Notas |
|---|---|---|
| 🔥 **firepaste.com** | requests + BS4 | HTML estático, rápido |
| 🎮 **romsfun.com** | requests + BS4 + Playwright | Soporta páginas de juego, listas y countdowns |
| 🌍 **Sitios genéricos** | Playwright headless | Detecta tablas y links por extensión |

---

## ☁️ Plataformas cloud

| Plataforma | Cuenta requerida | Config |
|---|---|---|
| 🟠 **GoFile** | No (guest) / Opcional | Token para carpetas organizadas |
| 🔵 **MediaFire** | Sí | Email + contraseña |
| 🔴 **Mega.nz** | Sí | Email + contraseña |
| 🟢 **Google Drive** | Sí | `credentials.json` de Google Cloud Console |

---

## 🔧 Configuración

Los datos se guardan en JSON en el home del usuario:

| Archivo | Contenido |
|---|---|
| `~/.firepaste_config.json` | URL del panel, tokens, credenciales cloud |
| `~/.firepaste_history.json` | Historial de posts (máx. 200) |
| `~/.firepaste_patterns.json` | Patrones aprendidos |

```json
{
  "url_panel": "https://firepaste.com/admin",
  "bot_api_token": "TU_TOKEN_AQUI"
}
```

El `bot_api_token` se configura en el `.env` de tu Firepaste con `BOT_API_TOKEN`.

---

## 🔌 API interna (JS ↔ Python)

| Método | Qué hace |
|---|---|
| `get_config()` | Carga la config guardada |
| `save_config(cfg)` | Guarda la config |
| `escanear_url(url)` | Escanea URL → devuelve `{archivos, titulo}` |
| `generar_ia(titulo, catalogo)` | Genera título limpio + pestaña automáticamente |
| `generar_tabla_directa(archivos)` | HTML con links originales |
| `publicar_post(datos)` | Publica en Firepaste via API REST |
| `get_historial()` | Historial de publicaciones |
| `limpiar_historial()` | Borra el historial |

---

## 🐛 Problemas conocidos

| Problema | Causa probable | Solución |
|---|---|---|
| Ventana no abre / error WebKit | Falta webkit2gtk en Linux | `sudo dnf install webkit2gtk4.1` |
| Error WebView2 en Windows | Runtime no instalado | Instala Edge WebView2 desde el link de arriba |
| Playwright no encuentra Chromium | No se instaló el browser | `python3 -m playwright install chromium` |
| `ksshaskpass` pide contraseña en KDE | KDE intercepta git | `unset SSH_ASKPASS GIT_ASKPASS` antes del push |
| Token inválido en git push | Token expirado o mal pegado | Crea uno nuevo en github.com/settings/tokens |
| Scraper no encuentra archivos | Sitio cambió su HTML | Abre un issue en el repo |
| GoFile no agrupa archivos | Sin cuenta guest reutilizada | Los archivos del mismo juego van juntos automáticamente |

---

## 📁 Estructura detallada

```
main.py
├── _es_firepaste()          # Detecta URLs de firepaste.com
├── _scrape_firepaste()      # Scraper liviano (requests)
├── scrape_url()             # Unifica scraping por sitio
├── bot_publicar()           # Publica via API REST
└── API (clase)
    ├── escanear_url()
    ├── generar_ia()
    ├── publicar_post()
    └── get/save config, historial, patrones

uploader.py
├── descargar_archivo()      # Descarga con progreso
├── subir_gofile()           # Con/sin cuenta
├── subir_mediafire()
├── subir_mega()
├── subir_drive()
├── procesar_archivos()      # Orquesta todo
├── build_tabla_resultados() # HTML con links de cloud
└── build_tabla_directa()    # HTML con links originales
```

---

<div align="center">

**Hecho con** ☕ **café** y 🌿 **buena vibra**

*Si te sirvió, dale una ⭐ al repo*

[![GitHub stars](https://img.shields.io/github/stars/K-A-Y-R-U/firepaste-pywebview?style=social)](https://github.com/K-A-Y-R-U/firepaste-pywebview/stargazers)

</div>