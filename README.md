# 🛡️ PinRouting

[![Build and Update Routing](https://github.com/pincetgore/PinRouting/actions/workflows/build-and-update.yml/badge.svg)](https://github.com/pincetgore/PinRouting/actions/workflows/build-and-update.yml)
[![Check and Cleanup Dead Entries](https://github.com/pincetgore/PinRouting/actions/workflows/check-dead-entries.yml/badge.svg)](https://github.com/pincetgore/PinRouting/actions/workflows/check-dead-entries.yml)
[![GitHub Release](https://img.shields.io/github/v/release/pincetgore/PinRouting?style=flat-square&color=blue)](https://github.com/pincetgore/PinRouting/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Clients](https://img.shields.io/badge/Clients-Happ%20%7C%20INCY%20%7C%20Shadowrocket-blueviolet?style=flat-square)](#-быстрая-установка)
<p align="center">
  <a href="https://yoomoney.ru/to/4100119554027650">
    <img src="https://img.shields.io/badge/Поддержать-ЮMoney-8B3FFD?style=for-the-badge&logo=yoomoney&logoColor=white" alt="Поддержать" />
  </a>
</p>

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
  <td><b>Основной профиль:</b> RU/BY, банки, гос. сервисы, Twitch напрямую. YouTube, Telegram, GitHub и зарубежный интернет — через прокси. Реклама и телеметрия заблокированы.</td>
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
<thead><tr><th align="left">Профиль</th><th align="left">Автообновление (Autorouting)</th><th align="left">Разовый импорт (.DEEPLINK)</th><th align="left">JSON-конфиг</th><th align="left">Описание</th></tr></thead>
<tbody>
<tr>
  <td><b>DEFAULT</b></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/DEFAULT.AUTOLINK">DEFAULT.AUTOLINK</a></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/DEFAULT.DEEPLINK">DEFAULT.DEEPLINK</a></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/DEFAULT.JSON">DEFAULT.JSON</a></td>
  <td><b>Основной профиль:</b> Полная маршрутизация с разделением RU-трафика и зарубежных ресурсов.</td>
</tr>
<tr>
  <td><b>WHITELIST</b></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/WHITELIST.AUTOLINK">WHITELIST.AUTOLINK</a></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/WHITELIST.DEEPLINK">WHITELIST.DEEPLINK</a></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/WHITELIST.JSON">WHITELIST.JSON</a></td>
  <td><b>Белый список:</b> Прямой доступ только к доверенным государственным и банковским сервисам.</td>
</tr>
<tr>
  <td><b>BASIC</b></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/BASIC.AUTOLINK">BASIC.AUTOLINK</a></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/BASIC.DEEPLINK">BASIC.DEEPLINK</a></td>
  <td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/BASIC.JSON">BASIC.JSON</a></td>
  <td><b>Базовый профиль:</b> Системные пуши напрямую, DNS и базы geodata для тонкой ручной кастомизации.</td>
</tr>
</tbody>
</table>

### Для Shadowrocket

Импортируйте нужный `.CONF` файл по ссылке в Shadowrocket (**Config** ➔ **+** ➔ вставить URL):

* 🛡️ **[DEFAULT.CONF](https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/SHADOWROCKET/DEFAULT.CONF)** — основной профиль со всеми оптимизациями.
* 📋 **[WHITELIST.CONF](https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/SHADOWROCKET/WHITELIST.CONF)** — режим строгого белого списка.
* ⚙️ **[BASIC.CONF](https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/SHADOWROCKET/BASIC.CONF)** — базовый профиль без предустановленных правил маршрутизации сайтов.

---

## 🧭 Логика маршрутизации

Порядок обработки правил во всех профилях строго упорядочен:

1. **Блокировка (Block / Reject):**
   * Рекламные сети, трекеры и баннеры (`geosite:category-ads`).
   * Торрент-трекеры (`geosite:torrent`), предотвращающие утечки в туннель и нагрузку на сервер.
2. **Системные исключения (Direct):**
   * Push-уведомления Apple (`geosite:apple-push`) и Google FCM / Huawei HMS / Xiaomi (`geosite:android-push`).
   * Загрузка системных обновлений iOS/macOS (`geosite:apple-update`).
   * Скачивание APK и приложений из Google Play (`geosite:google-play`).
   * Сетевые протоколы операторов связи (VoWiFi / IMS) и домены локального определения IP (`geosite:domains-geo-detect`).
3. **Прямое соединение (Direct):**
   * Локальные и приватные адреса (`geosite:private`, `geoip:private`).
   * Российские ресурсы, порталы и банки (`geosite:category-ru`, `geoip:ru`, `geoip:by`, `geoip:direct`, `geoip:custom-list-add`).
   * Ресурсы белого списка (`geosite:whitelist`, `geoip:whitelist`).
   * Стриминг и медиа: Twitch (`geosite:twitch`), Pinterest (`geosite:pinterest`).
4. **Проксирование (Proxy):**
   * Заблокированные и международные социальные сети: YouTube (`geosite:youtube`), Telegram (`geosite:telegram`), Instagram / Threads (`geosite:instagram`), X / Twitter (`geosite:twitter`).
   * Инструменты разработки: GitHub (`geosite:github`).
   * Ресурсы, блокирующие пользователей из РФ (GeoBlock): AI-сервисы (ChatGPT, Claude, Gemini, Copilot), Canva, Spotify, Notion и др. (`geosite:category-geoblock-ru`).
   * **Финальное правило (Catch-all):** весь остальной зарубежный трафик направляется через Proxy.

---

## ⚙️ Настройки DNS

Все сгенерированные конфигурации по умолчанию используют защищённые и оптимизированные резолверы:

* **Remote DNS (для зарубежных и заблокированных доменов):**
  * `Cloudflare DoH` — `https://1.1.1.1/dns-query`
  * `Google DoH` — `https://dns.google/dns-query`
* **Direct DNS (для российских ресурсов):**
  * `Yandex DNS` — `77.88.8.8`, `77.88.8.1`
  * `Cloudflare DNS` — `1.1.1.1`, `1.0.0.1`

---

## 📦 Релизы и ссылки на базы

Скомпилированные файлы всегда доступны в ветке [`release`](https://github.com/pincetgore/PinRouting/tree/release) и через глобальный CDN:

| Файл | Описание | Прямая ссылка через jsDelivr CDN |
| :--- | :--- | :--- |
| `geoip.dat` | Бинарная база диапазонов IP | `https://cdn.jsdelivr.net/gh/pincetgore/PinRouting@release/geoip.dat` |
| `geosite.dat` | Бинарная база доменных правил | `https://cdn.jsdelivr.net/gh/pincetgore/PinRouting@release/geosite.dat` |
| `geoip.dat.sha256` | Контрольная сумма SHA-256 | `https://cdn.jsdelivr.net/gh/pincetgore/PinRouting@release/geoip.dat.sha256` |
| `geosite.dat.sha256` | Контрольная сумма SHA-256 | `https://cdn.jsdelivr.net/gh/pincetgore/PinRouting@release/geosite.dat.sha256` |
| `text.tar.gz` | Текстовые дампы CIDR списков | В релизах [GitHub Releases](https://github.com/pincetgore/PinRouting/releases) |

---

## 🔄 Автоматизация (CI/CD)

В репозитории настроен автоматический пайплайн GitHub Actions:

### 1. `build-and-update.yml` (Сборка баз и конфигов)
1. **Проверяет синтаксис** и валидность всех профилей и правил (`ruff`, `lint_rules.py`, `pinrouting lint`).
2. **Запускает симуляцию роутинга** (`pinrouting test`), гарантируя отсутствие регрессий.
3. **Загружает свежие списки** GeoLite2, DB-IP, IPinfo, Re:filter, Antifilter и CDN.
4. **Компилирует бинарные файлы** `geoip.dat` и `geosite.dat` через `geoip-tool` и `domain-list-community`.
5. **Публикует релизы** с бинарниками, контрольными суммами и архивом `text.tar.gz`.
6. **Генерирует клиентские конфигурации** Happ, INCY и Shadowrocket.

Расписание запуска: **ежедневно в 01:00 UTC**, при каждом коммите в репозиторий или вручную через **Actions**.

### 2. `check-dead-entries.yml` (Проверка и очистка неживых записей)
1. **Проверяет домены** на liveness через 3 независимых DNS-резолвера (`1.1.1.1`, `8.8.8.8`, `77.88.8.8`) с подтверждением `NXDOMAIN`.
2. **Проверяет IP и подсети** через TCP-пробы (443 TLS, 80 HTTP) и ICMP ping со сэмплированием хостов для сетей `/24` и шире.
3. **Формирует детальный отчет** в Markdown и JSON (прикрепляется к GitHub Step Summary и артефактам).
4. **Удаляет неживые записи** и автоматически создает Pull Request (`action: pr`) либо коммитит в ветку.

Расписание запуска: **ежемесячно 1-го числа в 03:00 UTC** или вручную через **Actions** (`workflow_dispatch`).

---

## 📁 Структура репозитория

```text
├── .github/workflows/
│   ├── build-and-update.yml   # Автоматизированный CI/CD пайплайн сборки
│   └── check-dead-entries.yml # Проверка и очистка неживых доменов и IP (PR / Commit)
├── HAPP/                      # Конфигурации и диплинки для клиента Happ
│   ├── DEFAULT.JSON / .DEEPLINK
│   ├── WHITELIST.JSON / .DEEPLINK
│   └── BASIC.JSON / .DEEPLINK
├── INCY/                      # Конфигурации для клиента INCY (автообновление и разовый импорт)
│   ├── DEFAULT.JSON / .AUTOLINK / .DEEPLINK
│   ├── WHITELIST.JSON / .AUTOLINK / .DEEPLINK
│   └── BASIC.JSON / .AUTOLINK / .DEEPLINK
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
│   ├── buildtools/            # Скрипты тестирования, линтинга и дедупликации доменов
│   │   ├── lint_rules.py      # Линтер синтаксиса и избыточности правил
│   │   ├── test_routing.py    # Симуляция и регрессионное тестирование роутинга
│   │   └── deduplicate.py     # Анализатор пересечений IP и доменов
│   └── data/                  # Текстовые списки доменов по категориям
├── profiles/                  # SSOT JSON-манифесты профилей (DEFAULT, WHITELIST, BASIC)
├── tools/                     # Пакет PinRouting CLI и инструментов автоматизации
│   └── pinrouting/
│       ├── cli/
│       │   ├── build.py       # Сборка конфигураций всех клиентов
│       │   ├── check_dead.py  # Проверка и очистка неживых доменов и IP
│       │   ├── lint.py        # Линтинг профилей и правил
│       │   └── test.py        # Регрессионные тесты роутинга
│       ├── emitters/          # Генераторы форматов HAPP, INCY, Shadowrocket
│       └── models.py          # Модели конфигураций и профилей
├── Makefile                   # make lint, make test, make build, make check-dead
├── pyproject.toml             # Конфигурация Python проекта и линтера Ruff
├── LICENSE                    # Лицензия MIT
└── README.md                  # Документация проекта
```

---

## 🔗 Источники и благодарности

Проект агрегирует данные, списки и инструменты из следующих открытых источников:

### 🛠️ Инструменты сборки
* [Loyalsoldier/geoip](https://github.com/Loyalsoldier/geoip) — инструмент компиляции бинарных баз `geoip.dat`.
* [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) — компилятор бинарных баз правил `geosite.dat`.

### 🌍 Базы IP-геолокации (GeoIP)
* [@ip-location-db](https://github.com/sapics/ip-location-db) — ежедневные выгрузки сопоставления IP и стран (GeoLite2, DB-IP Lite).
* [Davoyan/ipinfo](https://github.com/Davoyan/ipinfo) — ежедневные списки IP-диапазонов IPinfo Lite для России и Беларуси.
* [Netsyms / MaxMind](https://dl.netsyms.net/dbs/geolite2/) — зеркало базы GeoLite2 ASN для фильтрации подсетей по номерам автономных систем (ASN).

### 🛡️ Списки блокировок РКН (для исключения из прямого трафика)
* [Re:filter](https://github.com/1andrevich/Re-filter-lists) — актуальные списки заблокированных ресурсов (ipsum, community).
* [Antifilter.Network](https://antifilter.network) — выгрузка заблокированных IP-адресов.
* [Antifilter Community](https://community.antifilter.download) — общественный список блокировок.

### 🌐 Исключение зарубежных CDN и хостингов
* [PentiumB/CDN-RuleSet](https://github.com/PentiumB/CDN-RuleSet) — сводная база диапазонов глобальных CDN.
* [mansourjabin/cdn-ip-database](https://github.com/mansourjabin/cdn-ip-database) — база IP-адресов сетей доставки контента.

### 📋 Белые списки и правила маршрутизации
* [DigneZzZ/routing](https://github.com/DigneZzZ/routing) — архитектурные подходы к оптимизации мобильного роутинга и концепции сквозного тестирования правил.
* [escapingworm/russia-whitelist](https://github.com/escapingworm/russia-whitelist) — проверенные белые списки подсетей РФ (CIDR).
* [kirilllavrov/RU-domain-list-for-whitelist](https://github.com/kirilllavrov/RU-domain-list-for-whitelist) — списки российских доменов для белого списка.
* [hxehex/russia-mobile-internet-whitelist](https://github.com/hxehex/russia-mobile-internet-whitelist) — белые списки ресурсов мобильного интернета РФ.
* [pincetgore/amnezia-app-ru-list](https://github.com/pincetgore/amnezia-app-ru-list) — структурированные базы доверенных доменов РФ по отраслям.
* [misha-tgshv/shadowrocket-configuration-file](https://github.com/misha-tgshv/shadowrocket-configuration-file) — база сайтов кредитных организаций ЦБ РФ, чекеры доступности и шаблоны конфигураций Shadowrocket.
* [roscomvpn-routing](https://github.com/hydraponique/roscomvpn-routing), [roscomvpn-geoip](https://github.com/hydraponique/roscomvpn-geoip), [roscomvpn-geosite](https://github.com/hydraponique/roscomvpn-geosite) — базовые правила маршрутизации от hydraponique.

---

## 📄 Лицензия

Проект распространяется под открытой лицензией [MIT](LICENSE). Вы можете свободно использовать, модифицировать и распространять его как в личных, так и в коммерческих целях с обязательным сохранением указания авторства.

---

## ☕ Поддержка автора

Если проект оказался вам полезен и помогает удобно маршрутизировать трафик, вы можете поддержать его развитие и поблагодарить автора:

<p align="center">
  <a href="https://yoomoney.ru/to/4100119554027650">
    <img src="https://img.shields.io/badge/Поддержать_проект-ЮMoney-8B3FFD?style=for-the-badge&logo=yoomoney&logoColor=white" alt="Поддержать проект" />
  </a>
</p>
