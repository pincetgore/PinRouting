# 🛡️ PinRouting

[![Build and Update Routing](https://github.com/pincetgore/PinRouting/actions/workflows/build-and-update.yml/badge.svg)](https://github.com/pincetgore/PinRouting/actions/workflows/build-and-update.yml)
[![GitHub Release](https://img.shields.io/github/v/release/pincetgore/PinRouting?style=flat-square&color=blue)](https://github.com/pincetgore/PinRouting/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Clients](https://img.shields.io/badge/Clients-Happ%20%7C%20INCY%20%7C%20Shadowrocket-blueviolet?style=flat-square)](#-быстрая-установка)

Оптимизированные конфигурации маршрутизации (роутинга) для клиентов **Happ**, **INCY** и **Shadowrocket** на базе кастомных легковесных баз GeoIP и Geosite.

Проект автоматически собирает компактные бинарные базы правил (`geoip.dat` и `geosite.dat`), исключает рекламу, телеметрию, трекеры и обеспечивает прямое соединение (Direct) с российскими сервисами без задержек VPN, направляя заблокированные и зарубежные ресурсы в прокси-туннель.

---

## 📱 Быстрая установка

### Для Happ

<table width="100%">
<thead><tr><th align="left">Профиль</th><th align="left">Файл диплинка (.DEEPLINK)</th><th align="left">JSON-конфиг (для подписки)</th><th align="left">Описание</th></tr></thead>
<tbody>
<tr>
  <td><b>DEFAULT</b></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/HAPP/DEFAULT.DEEPLINK">DEFAULT.DEEPLINK</a></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/HAPP/DEFAULT.JSON">DEFAULT.JSON</a></td>
  <td><b>Основной профиль:</b> RU/BY, банки, гос. сервисы, Steam, Twitch напрямую. YouTube, Telegram, GitHub и зарубежный интернет — через прокси. Реклама и телеметрия заблокированы.</td>
</tr>
<tr>
  <td><b>WHITELIST</b></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/HAPP/WHITELIST.DEEPLINK">WHITELIST.DEEPLINK</a></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/HAPP/WHITELIST.JSON">WHITELIST.JSON</a></td>
  <td><b>Белый список:</b> Напрямую идут <i>только</i> проверенные ресурсы из <code>geosite:whitelist</code> и <code>geoip:whitelist</code> (банки, Госуслуги и др.). Весь остальной интернет — через прокси.</td>
</tr>
<tr>
  <td><b>BASIC</b></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/HAPP/BASIC.DEEPLINK">BASIC.DEEPLINK</a></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/HAPP/BASIC.JSON">BASIC.JSON</a></td>
  <td><b>Базовый профиль:</b> Настроены DoH DNS, ссылки на кастомные базы geodata и прямой доступ для системных пуш-уведомлений (<code>geosite:apple-push</code>, <code>geosite:android-push</code>), без других правил (для ручной настройки).</td>
</tr>
</tbody>
</table>

### Для INCY

<table width="100%">
<thead><tr><th align="left">Профиль</th><th align="left">Файл диплинка (.DEEPLINK)</th><th align="left">JSON-конфиг (для подписки)</th><th align="left">Описание</th></tr></thead>
<tbody>
<tr>
  <td><b>DEFAULT</b></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/DEFAULT.DEEPLINK">DEFAULT.DEEPLINK</a></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/DEFAULT.JSON">DEFAULT.JSON</a></td>
  <td><b>Основной профиль:</b> Полная маршрутизация с разделением RU-трафика и зарубежных ресурсов.</td>
</tr>
<tr>
  <td><b>WHITELIST</b></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/WHITELIST.DEEPLINK">WHITELIST.DEEPLINK</a></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/WHITELIST.JSON">WHITELIST.JSON</a></td>
  <td><b>Белый список:</b> Прямой доступ только к доверенным белым спискам РФ, остальное через прокси.</td>
</tr>
<tr>
  <td><b>BASIC</b></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/BASIC.DEEPLINK">BASIC.DEEPLINK</a></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/BASIC.JSON">BASIC.JSON</a></td>
  <td><b>Базовый профиль:</b> DNS + базы геоданных + прямой доступ для системных пуш-уведомлений (<code>geosite:apple-push</code>, <code>geosite:android-push</code>).</td>
</tr>
</tbody>
</table>

### Для Shadowrocket

<table width="100%">
<thead><tr><th align="left">Профиль</th><th align="left">Конфигурационный файл (.CONF)</th><th align="left">Ссылка для импорта в один клик</th><th align="left">Описание</th></tr></thead>
<tbody>
<tr>
  <td><b>DEFAULT</b></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/SHADOWROCKET/DEFAULT.CONF">DEFAULT.CONF</a></td>
  <td><a href="shadowrocket://config/add/https://raw.githubusercontent.com/pincetgore/PinRouting/main/SHADOWROCKET/DEFAULT.CONF">Импорт в Shadowrocket</a></td>
  <td><b>Основной профиль:</b> Полный аналог DEFAULT.JSON. Российский трафик (RU/BY, банки, Госуслуги, Steam, Twitch) напрямую. Заблокированные ресурсы и остальной интернет — через прокси. Реклама и телеметрия заблокированы.</td>
</tr>
<tr>
  <td><b>WHITELIST</b></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/SHADOWROCKET/WHITELIST.CONF">WHITELIST.CONF</a></td>
  <td><a href="shadowrocket://config/add/https://raw.githubusercontent.com/pincetgore/PinRouting/main/SHADOWROCKET/WHITELIST.CONF">Импорт в Shadowrocket</a></td>
  <td><b>Белый список:</b> Полный аналог WHITELIST.JSON. Напрямую идут <i>только</i> проверенные ресурсы РФ и 17 900+ банковских IP. Весь остальной трафик — через прокси.</td>
</tr>
<tr>
  <td><b>BASIC</b></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/SHADOWROCKET/BASIC.CONF">BASIC.CONF</a></td>
  <td><a href="shadowrocket://config/add/https://raw.githubusercontent.com/pincetgore/PinRouting/main/SHADOWROCKET/BASIC.CONF">Импорт в Shadowrocket</a></td>
  <td><b>Базовый профиль:</b> DoH DNS + прямой доступ для системных пуш-уведомлений (Apple APNs/iCloud). Остальной трафик через прокси.</td>
</tr>
<tr>
  <td><b>EXTENDED</b></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/SHADOWROCKET/EXTENDED.CONF">EXTENDED.CONF</a></td>
  <td>—</td>
  <td><b>Пользовательский файл:</b> Подключается через <code>include = EXTENDED.CONF</code>. Добавленные в него личные правила имеют наивысший приоритет и не затираются при автообновлении.</td>
</tr>
</tbody>
</table>

> [!TIP]
> **Как подключить в приложении:**
> 1. **Через диплинк:** откройте ссылку на файл `.DEEPLINK`, скопируйте текстовую строку схемы (`happ://routing/onadd/...` или `incy://routing/onadd/...`) и откройте её в адресной строке браузера на устройстве (браузер предложит открыть клиент).
> 2. **Через URL подписки:** скопируйте прямую ссылку на `.JSON` файл и укажите её в клиенте как внешний URL правил маршрутизации (с поддержкой автообновления).
> 3. **В Shadowrocket:** нажмите «Импорт в Shadowrocket» или скопируйте URL `.CONF` файла, перейдите в **Config** ➔ **«+»**, вставьте ссылку и нажмите **Download**. Включите автообновление: **Settings** ➔ **Update** ➔ **Config** (или через параметр `update-url`).

---

## 🗺 Маршрутизация в профиле DEFAULT

Порядок применения правил (`RouteOrder`): **`block-proxy-direct`**.

### 🔴 BLOCK (блокировка)
<table width="100%">
<thead><tr><th align="left">Категория</th><th align="left">Зачем</th></tr></thead>
<tbody>
<tr><td>🚫 <code>geosite:win-spy</code></td><td>Отключение телеметрии и слежки компонентов ОС Windows</td></tr>
<tr><td>🚫 <code>geosite:torrent</code></td><td>Блокировка публичных BitTorrent DHT-серверов и трекеров (защита VPS от абуз хостера)</td></tr>
<tr><td>🚫 <code>geosite:category-ads</code></td><td>Блокировка рекламы (Mail.ru, VK Видео, VK Музыка и др.)</td></tr>
</tbody>
</table>

### 🔵 PROXY (через VPN)
<table width="100%">
<thead><tr><th align="left">Сервис / Направление</th><th align="left">Зачем</th></tr></thead>
<tbody>
<tr><td>🌐 <code>geosite:category-geoblock-ru</code></td><td>Зарубежные сервисы с геоблокировкой пользователей из РФ (Gemini, AI Studio, ChatGPT, Claude, Notion, Canva и др.)</td></tr>
<tr><td>🌐 <code>geosite:youtube</code></td><td>Обход замедлений ТСПУ и стабильное воспроизведение YouTube</td></tr>
<tr><td>🌐 <code>geosite:telegram</code></td><td>Стабильное подключение к дата-центрам Telegram в обход блокировок</td></tr>
<tr><td>🌐 <code>geosite:github</code></td><td>Обход фильтрации ресурсов и ассетов GitHub</td></tr>
<tr><td>🌐 <code>geosite:twitch-ads</code></td><td>Обход рекламы Twitch для сохранения максимального исходного качества (Source) трансляций</td></tr>
<tr><td>🌐 <b>Весь остальной зарубежный трафик</b></td><td>Все сайты и сервисы, не вошедшие в Direct-списки, направляются через прокси</td></tr>
</tbody>
</table>

### 🟢 DIRECT (напрямую без VPN)
<table width="100%">
<thead><tr><th align="left">Сервис / Домены</th><th align="left">Зачем</th></tr></thead>
<tbody>
<tr><td>✅ <code>geosite:category-ru</code> + <code>geoip:direct</code></td><td>Все российские и белорусские сайты, порталы и сервисы</td></tr>
<tr><td>✅ <code>geosite:apple-push</code> + <code>geosite:android-push</code></td><td>Доставка push-уведомлений Apple (APNs/iCloud), Android (Google FCM, Xiaomi, Huawei, Samsung) и проверка сетевого подключения (captive portal)</td></tr>
<tr><td>✅ <code>geosite:whitelist</code></td><td>Госуслуги, все банки РФ (реестр ЦБ РФ), критически важные ресурсы и сервисы Google</td></tr>
<tr><td>✅ <code>geosite:domains-ipchecker</code></td><td>Чекеры связности российских приложений (Ozon, 2GIS, X5 Group, ifconfig, ipify) напрямую для корректной геолокации</td></tr>
<tr><td>✅ <code>geosite:domains-geo-detect</code></td><td>225 сервисов проверки IP и сетевой геолокации (2ip, whoer, browserleaks, bgp.tools и др.) напрямую в обход VPN</td></tr>
<tr><td>✅ <code>geosite:microsoft</code></td><td>Windows Update, Xbox и сервисы Microsoft без расхода трафика сервера</td></tr>
<tr><td>✅ <code>geosite:steam</code></td><td>Игровой трафик Steam напрямую (максимальная скорость загрузки игр)</td></tr>
<tr><td>✅ <code>geosite:twitch</code></td><td>Видеопотоки Twitch напрямую (экономия трафика сервера)</td></tr>
<tr><td>✅ <code>geosite:pinterest</code></td><td>Прямой доступ к сервису Pinterest</td></tr>
<tr><td>✅ <code>geosite:private</code> + <code>geoip:private</code></td><td>Локальные сети (RFC 1918, 127.0.0.0/8, 192.168.x.x, роутер, локальные устройства)</td></tr>
</tbody>
</table>

> [!NOTE]
> **Приоритет Google vs Gemini:** Домен `google.com` включён в `whitelist` для быстрого прямого поиска без задержек VPN. При этом сервисы Gemini и AI Studio (`gemini.google.com`, `generativelanguage.googleapis.com`) гарантированно направляются в прокси, так как правило `geosite:category-geoblock-ru` имеет более высокий приоритет исполнения (`RouteOrder: block-proxy-direct`).

---

## 🛡️ Маршрутизация в профиле WHITELIST (Белый список)

Профиль предназначен для режима максимальной приватности или работы в небезопасных сетях: **весь интернет-трафик по умолчанию направляется в зашифрованный VPN-туннель**, за исключением критически важных российских сервисов, блокирующих зарубежные IP.

Порядок применения правил (`RouteOrder`): **`block-proxy-direct`**.

### 🔴 BLOCK (блокировка)
* 🚫 `geosite:win-spy` — телеметрия и слежка компонентов ОС Windows
* 🚫 `geosite:torrent` — публичные BitTorrent трекеры и DHT (защита VPS)
* 🚫 `geosite:category-ads` — реклама и трекеры

### 🟢 DIRECT (напрямую без VPN — только доверенные ресурсы)
<table width="100%">
<thead><tr><th align="left">Категория / Список</th><th align="left">Что входит</th></tr></thead>
<tbody>
<tr><td>✅ <code>geosite:whitelist</code></td><td><b>860+ проверенных корневых доменов</b> ключевых российских сервисов (банки, Госуслуги, суды, ФНС, ЕМИАС, аптеки, маркетплейсы, доставка, транспорт, авиация, телеком, облака)</td></tr>
<tr><td>✅ <code>geoip:whitelist</code></td><td><b>17 900+ доверенных IP-диапазонов РФ</b> для гарантированной работы банковских приложений и государственных порталов</td></tr>
<tr><td>✅ <code>geosite:apple-push</code> + <code>geosite:android-push</code></td><td>Push-уведомления Apple (APNs/iCloud), Android (Google FCM, Xiaomi, Huawei, Samsung) и проверка сетевого подключения (captive portal)</td></tr>
<tr><td>✅ <code>geosite:private</code> + <code>geoip:private</code></td><td>Локальные сети (RFC 1918, роутер, домашние устройства)</td></tr>
</tbody>
</table>

### 🔵 PROXY (через VPN)
* 🌐 `geosite:category-geoblock-ru` — зарубежные сервисы с геоблокировкой пользователей из РФ
* 🌐 **Весь остальной трафик** — все поисковики, зарубежные сайты, социальные сети, медиа и сервисы, не входящие в белый список, идут через защищённый туннель.

---

## 🔒 DNS и защита от утечек

В конфигурациях используется защищённый протокол **DNS-over-HTTPS (DoH)**:

<table width="100%">
<thead><tr><th align="center">Направление</th><th align="left">Протокол и сервер</th><th align="left">Как работает</th></tr></thead>
<tbody>
<tr>
  <td align="center">🏠 <b>Domestic (Direct)</b></td>
  <td><b>Яндекс DNS (DoH)</b><br><code>https://common.dot.dns.yandex.net/dns-query</code></td>
  <td>Используется для прямого мгновенного резолвинга российских сайтов через локального провайдера. Минимальный пинг в РФ.</td>
</tr>
<tr>
  <td align="center">🌍 <b>Remote (Proxy)</b></td>
  <td><b>Quad9 DNS (DoH)</b><br><code>https://dns.quad9.net/dns-query</code></td>
  <td>Резолвинг зарубежных и заблокированных сайтов. Запросы шифруются и идут <b>через зашифрованный VPN-туннель</b> (не перехватываются ТСПУ). Не ведет логов, юрисдикция Швейцарии, фильтрация фишинга.</td>
</tr>
</tbody>
</table>

### Статические записи (`DnsHosts` / `[Host]`)
Для гарантированного доступа к Личному кабинету налогоплательщика ФНС РФ в конфигах заданы статические сопоставления:
* `lkfl2.nalog.ru` ➔ `213.24.64.175`
* `lknpd.nalog.ru` ➔ `213.24.64.181`

---

## ⚙️ Особенности кастомных баз данных

### 🌎 GeoIP (`geoip.dat`)
Сборка базы выполняется с помощью утилиты Loyalsoldier на основе конфигурации [`geoip/config.json`](geoip/config.json):
* **Включает подсети РФ и РБ** из трёх авторитетных источников: MaxMind GeoLite2 ASN, IPinfo и DB-IP. Базы GeoLite2 и DB-IP конвертируются автономным скриптом [`geoip/buildtools/parse_country_db.py`](geoip/buildtools/parse_country_db.py) напрямую из выгрузок `@ip-location-db` без сторонних промежуточных сервисов.
* **Кастомные списки ([`geoip/CUSTOM-LIST-ADD.txt`](geoip/CUSTOM-LIST-ADD.txt))**:
  * Инфраструктура Yandex Cloud / HLL LLC (AS51115);
  * Зарубежные точки присутствия Яндекса (Yandex Oy Финляндия, Yandex Europe B.V., серверы в США, Казахстане, Беларуси);
  * Зарубежные серверы ВКонтакте и Mail.ru Games;
  * Официальные диапазоны шлюзов Apple Push Notification Service (APNs) для решения проблем с доставкой уведомлений на iPhone и Mac.
* **Кастомный белый список ([`geoip/CUSTOM-WHITELIST.txt`](geoip/CUSTOM-WHITELIST.txt))**: 17 900+ доверенных диапазонов для профиля WHITELIST.
* **Точечные исправления ([`geoip/CUSTOM-FIX-ADD.txt`](geoip/CUSTOM-FIX-ADD.txt))**: принудительное возвращение в `direct` адресов, ошибочно заблокированных РКН (например, `images.biggeek.ru`).
* **Исключение блокировок и CDN**:
  * Вычитание списков блокировок РКН: [Re:filter](https://github.com/1andrevich/Re-filter-lists) + [Antifilter.Network](https://antifilter.network);
  * Вычитание [зарубежных CDN](https://github.com/PentiumB/CDN-RuleSet), а также европейских хостингов (Hetzner, ZeroCDN) для исключения утечек прокси-трафика в прямой канал.

### 🌐 Geosite (`geosite.dat`)
Сборка базы выполняется компилятором `domain-list-community` из файлов правил [`geosite/data/`](geosite/data/):
* **Очистка от мусора**: включены только категории, реально используемые в роутинге (`category-ru`, `category-geoblock-ru`, `whitelist`, `apple-push`, `android-push`, `youtube`, `telegram`, `github`, `microsoft`, `steam`, `twitch`, `twitch-ads`, `pinterest`, `domains-geo-detect`, `domains-ipchecker`, `category-ads`, `torrent`, `win-spy`, `private`).
* **База `whitelist`**: более **860 проверенных корневых доменов** по 13 жизненно важным отраслям РФ (госуслуги, суды, банки, медицина, ритейл, доставка, транспорт, образование, страхование, телеком, облака, медиа), агрегированных из открытых белых списков, [pincetgore/amnezia-app-ru-list](https://github.com/pincetgore/amnezia-app-ru-list) и официального реестра ЦБ РФ.
* **Утилиты дедупликации ([`geosite/buildtools/`](geosite/buildtools/))**: автоматическая проверка доступности доменов через российские и зарубежные DNS-ноды для исключения доменов, чьи IP уже полностью входят в Direct-диапазоны. Скрипт поддерживает запуск как с удаленной загрузкой, так и с локальным файлом:
  ```bash
  python3 geosite/buildtools/deduplicate.py -f release/text/direct.txt geosite/data/category-ru
  ```

---

## 🔄 Автоматическая сборка и раздача геоданных

Пайплайн GitHub Actions ([`.github/workflows/build-and-update.yml`](.github/workflows/build-and-update.yml)):
1. **Параллельно загружает** актуальные выгрузки блокировок и геобаз (Re:filter, Antifilter, IPinfo, DB-IP, MaxMind GeoLite2).
2. **Компилирует бинарные файлы** `geoip.dat` и `geosite.dat`.
3. **Пушит результаты в изолированную ветку `release`** (без засорения ветки `main` тяжелыми бинарными diff'ами).
4. **Раздаёт файлы через Anycast CDN jsDelivr**:
   * `https://cdn.jsdelivr.net/gh/pincetgore/PinRouting@release/geoip.dat`
   * `https://cdn.jsdelivr.net/gh/pincetgore/PinRouting@release/geosite.dat`
5. **Публикует GitHub Releases** с бинарниками, контрольными суммами (`.sha256`) и архивом текстовых списков (`text.tar.gz`).
6. **Обновляет таймстемп `LastUpdated`** в JSON-конфигах, перегенерирует диплинки и собирает конфигурации Shadowrocket.
7. **Очищает кэш CDN jsDelivr** через Purge API.

Расписание запуска: **ежедневно в 04:00 UTC**, при каждом коммите в репозиторий или вручную через вкладку **Actions**.

---

## 📂 Структура репозитория

```text
├── .github/workflows/
│   └── build-and-update.yml   # Автоматизированный CI/CD пайплайн сборки
├── HAPP/                      # Конфигурации и диплинки для клиента Happ
│   ├── DEFAULT.JSON / .DEEPLINK
│   ├── WHITELIST.JSON / .DEEPLINK
│   └── BASIC.JSON / .DEEPLINK
├── INCY/                      # Зеркальные конфигурации для клиента INCY
│   ├── DEFAULT.JSON / .DEEPLINK
│   ├── WHITELIST.JSON / .DEEPLINK
│   └── BASIC.JSON / .DEEPLINK
├── SHADOWROCKET/              # Конфигурации и списки правил для Shadowrocket
│   ├── DEFAULT.CONF           # Основной профиль маршрутизации
│   ├── WHITELIST.CONF         # Профиль белого списка РФ
│   ├── BASIC.CONF             # Базовый профиль для подписки
│   ├── EXTENDED.CONF          # Шаблон пользовательских правил (include)
│   ├── rules/                 # Сгенерированные списки правил (.list)
│   └── tools/                 # Скрипты генерации конфигураций и правил
│       └── build_shadowrocket.py
├── geoip/                     # Конфигурация и кастомные списки GeoIP
│   ├── buildtools/            # Скрипты генерации IP-списков по странам
│   ├── config.json            # Правила объединения баз и вычитания списков РКН
│   ├── CUSTOM-FIX-ADD.txt     # Точечные фиксы ложных блокировок
│   ├── CUSTOM-LIST-ADD.txt    # Зарубежная инфраструктура Yandex, VK, Apple APNs
│   └── CUSTOM-WHITELIST.txt   # Кастомный белый список подсетей
├── geosite/
│   ├── buildtools/            # Скрипты тестирования и дедупликации доменов
│   └── data/                  # Текстовые списки доменов по категориям
├── .gitignore                 # Исключение временных файлов и build artifacts (release/)
├── LICENSE                    # Лицензия MIT
└── README.md                  # Документация проекта
```

---

## 🔗 Источники и благодарности

Проект агрегирует данные, списки и инструменты из следующих открытых источников:

### 🛠 Инструменты сборки
* [Loyalsoldier/geoip](https://github.com/Loyalsoldier/geoip) — инструмент компиляции бинарных баз `geoip.dat`.
* [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) — компилятор бинарных баз правил `geosite.dat`.

### 🌍 Базы IP-геолокации (GeoIP)
* [@ip-location-db](https://github.com/sapics/ip-location-db) — ежедневные выгрузки сопоставления IP и стран (GeoLite2, DB-IP Lite).
* [Davoyan/ipinfo](https://github.com/Davoyan/ipinfo) — ежедневные списки IP-диапазонов IPinfo Lite для России и Беларуси.
* [Netsyms / MaxMind](https://dl.netsyms.net/dbs/geolite2/) — зеркало базы GeoLite2 ASN для фильтрации подсетей по номерам автономных систем (ASN).

### 🛡 Списки блокировок РКН (для исключения из прямого трафика)
* [Re:filter](https://github.com/1andrevich/Re-filter-lists) — актуальные списки заблокированных ресурсов (ipsum, community).
* [Antifilter.Network](https://antifilter.network) — выгрузка заблокированных IP-адресов.
* [Antifilter Community](https://community.antifilter.download) — общественный список блокировок.

### 🌐 Исключение зарубежных CDN и хостингов
* [PentiumB/CDN-RuleSet](https://github.com/PentiumB/CDN-RuleSet) — сводная база диапазонов глобальных CDN.
* [mansourjabin/cdn-ip-database](https://github.com/mansourjabin/cdn-ip-database) — база IP-адресов сетей доставки контента.

### 📋 Белые списки и правила маршрутизации
* [escapingworm/russia-whitelist](https://github.com/escapingworm/russia-whitelist) — проверенные белые списки подсетей РФ (CIDR).
* [kirilllavrov/RU-domain-list-for-whitelist](https://github.com/kirilllavrov/RU-domain-list-for-whitelist) — списки российских доменов для белого списка.
* [hxehex/russia-mobile-internet-whitelist](https://github.com/hxehex/russia-mobile-internet-whitelist) — белые списки ресурсов мобильного интернета РФ.
* [pincetgore/amnezia-app-ru-list](https://github.com/pincetgore/amnezia-app-ru-list) — структурированные базы доверенных доменов РФ по отраслям.
* [misha-tgshv/shadowrocket-configuration-file](https://github.com/misha-tgshv/shadowrocket-configuration-file) — база сайтов кредитных организаций ЦБ РФ, чекеры доступности и шаблоны конфигураций Shadowrocket.
* [roscomvpn-routing](https://github.com/hydraponique/roscomvpn-routing), [roscomvpn-geoip](https://github.com/hydraponique/roscomvpn-geoip), [roscomvpn-geosite](https://github.com/hydraponique/roscomvpn-geosite) — базовые правила маршрутизации от hydraponique.

---

## 📄 Лицензия

Проект распространяется под открытой лицензией [MIT](LICENSE). Вы можете свободно использовать, модифицировать и распространять его как в личных, так и в коммерческих целях с обязательным сохранением указания авторства.

