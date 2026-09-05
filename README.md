# 🛡️ PinRouting

Оптимизированные конфигурации маршрутизации (роутинга) для клиентов **Happ** и **INCY** на базе кастомных легковесных баз GeoIP и Geosite.

## 📱 Установка для Happ

<table width="100%">
<thead><tr><th align="left">Способ</th><th align="left">Ссылка</th><th align="left">Описание</th></tr></thead>
<tbody>
<tr><td colspan="3"><b>DEFAULT</b> — полный профиль: RU/BY direct, YouTube/Telegram/GitHub через прокси, реклама блокируется</td></tr>
<tr><td>🔗 DEFAULT.DEEPLINK</td><td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/HAPP/DEFAULT.DEEPLINK">Просмотр</a></td><td>Диплинк-ссылка в текстовом формате</td></tr>
<tr><td>📊 DEFAULT.JSON</td><td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/HAPP/DEFAULT.JSON">Просмотр</a></td><td>JSON-конфиг роутинга</td></tr>
<tr><td colspan="3"><b>WHITELIST</b> — direct только для сервисов и IP из белых списков РФ; всё остальное через прокси</td></tr>
<tr><td>🔗 WHITELIST.DEEPLINK</td><td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/HAPP/WHITELIST.DEEPLINK">Просмотр</a></td><td>Диплинк-ссылка в текстовом формате</td></tr>
<tr><td>📊 WHITELIST.JSON</td><td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/HAPP/WHITELIST.JSON">Просмотр</a></td><td>JSON-конфиг роутинга</td></tr>
<tr><td colspan="3"><b>JSONSUB</b> — минимальный профиль: только DNS + кастомные geoip/geosite, без встроенных правил</td></tr>
<tr><td>🔗 JSONSUB.DEEPLINK</td><td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/HAPP/JSONSUB.DEEPLINK">Просмотр</a></td><td>Диплинк-ссылка в текстовом формате</td></tr>
<tr><td>📊 JSONSUB.JSON</td><td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/HAPP/JSONSUB.JSON">Просмотр</a></td><td>JSON-конфиг роутинга</td></tr>
</tbody>
</table>

## 📱 Установка для INCY

<table width="100%">
<thead><tr><th align="left">Способ</th><th align="left">Ссылка</th><th align="left">Описание</th></tr></thead>
<tbody>
<tr><td colspan="3"><b>DEFAULT</b> — полный профиль: RU/BY direct, YouTube/Telegram/GitHub через прокси, реклама блокируется</td></tr>
<tr><td>🔗 DEFAULT.DEEPLINK</td><td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/DEFAULT.DEEPLINK">Просмотр</a></td><td>Диплинк-ссылка в текстовом формате</td></tr>
<tr><td>📊 DEFAULT.JSON</td><td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/DEFAULT.JSON">Просмотр</a></td><td>JSON-конфиг роутинга</td></tr>
<tr><td colspan="3"><b>WHITELIST</b> — direct только для сервисов и IP из белых списков РФ; всё остальное через прокси</td></tr>
<tr><td>🔗 WHITELIST.DEEPLINK</td><td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/WHITELIST.DEEPLINK">Просмотр</a></td><td>Диплинк-ссылка в текстовом формате</td></tr>
<tr><td>📊 WHITELIST.JSON</td><td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/WHITELIST.JSON">Просмотр</a></td><td>JSON-конфиг роутинга</td></tr>
<tr><td colspan="3"><b>JSONSUB</b> — минимальный профиль: только DNS + кастомные geoip/geosite, без встроенных правил</td></tr>
<tr><td>🔗 JSONSUB.DEEPLINK</td><td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/JSONSUB.DEEPLINK">Просмотр</a></td><td>Диплинк-ссылка в текстовом формате</td></tr>
<tr><td>📊 JSONSUB.JSON</td><td><a href="https://raw.githubusercontent.com/pincetgore/PinRouting/refs/heads/main/INCY/JSONSUB.JSON">Просмотр</a></td><td>JSON-конфиг роутинга</td></tr>
</tbody>
</table>

---

## ✨ Преимущества

<details open>
<summary><b>🌎 Кастомный GeoIP — <a href="https://github.com/hydraponique/roscomvpn-geoip">GitHub</a></b></summary>

Максимально уменьшенный geoip.dat — выпилено все, кроме кастомного списка `geoip:direct`, где:
- ➕ Русские/белорусские CIDR-диапазоны из трёх независимых геобаз: GeoLite2 (MaxMind), IPinfo, DB-IP
- ➕ Кастомный список IP-диапазонов "казенных" VK Company, Yandex, CDNVideo (включая их зарубежные активы)
- ➕ CIDR Apple Push-уведомлений (решение проблем с доставкой уведомлений на iOS устройствах)
- ➖ DIFF-исключение списков: [Re:filter](https://github.com/1andrevich/Re-filter-lists) + [Antifilter.Network](https://antifilter.network) (для разблокировки РКН-списков)
- ➖ DIFF-исключение Community-списков: [Re:filter](https://github.com/1andrevich/Re-filter-lists) + [Antifilter.Network](https://antifilter.network) + [Antifilter.Download](https://antifilter.download) (для проблемных/не работающих, НЕ заблокированных сервисов — 4pda, CloudFlare, аниме и др.)
- ➖ DIFF-исключение [зарубежных CDN-сервисов](https://github.com/PentiumB/CDN-RuleSet) + кастомный список Hetzner и ZeroCDN (а именно их CIDR стран нашего таргета)
- ➖ DIFF-исключение `0.0.0.0/8` из private списка (предотвращение утечки DNS на некоторых устройствах)

</details>

<details open>
<summary><b>🌐 Кастомный Geosite — <a href="https://github.com/hydraponique/roscomvpn-geosite">GitHub</a></b></summary>

- **Обновленные списки сервисов** — максимально оптимизированы под этот роутинг + дедупликация
- **Минималистичный подход** — то, чего нет в конфиге роутинга, выпилено с корнем
- **Облегченные списки** — разгружают ядро от фильтрации мусора и include-редиректов

</details>

---

## 🗺 Что роутится в DEFAULT-версии

### 🔴 BLOCK (блокировка)

<table width="100%">
<thead><tr><th align="left">Что</th><th align="left">Зачем</th></tr></thead>
<tbody>
<tr><td>🚫 <b>Домены слежки Windows</b></td><td>Отключаем телеметрию и слежку за пользователями</td></tr>
<tr><td>🚫 <b>BitTorrent DHT</b></td><td>Известные публичные DHT-серверы, для экономии трафика вашего сервера и успокоения хостера</td></tr>
<tr><td>🚫 <b>Реклама VK Company</b></td><td>Отключаем рекламу в ВК Видео и ВК Музыке</td></tr>
</tbody>
</table>

### 🟢 DIRECT (напрямую)

<table width="100%">
<thead><tr><th align="left">Что</th><th align="left">Зачем</th></tr></thead>
<tbody>
<tr><td>✅ <b>Русские/белорусские</b> домены и CIDR</td><td>За исключением РКН-списков + РФ активов зарубежных CDN-сервисов</td></tr>
<tr><td>✅ <b>"Казенные" сервисы РФ и CDN</b></td><td>VK, OK, Mail.Ru, Яндекс, CDNVideo (включая зарубежные активы)</td></tr>
<tr><td>✅ <b>Обновления и пуши</b></td><td>Apple, Microsoft — корректная работа устройства + экономия трафика</td></tr>
<tr><td>✅ <b>Все банки РФ</b></td><td>Вытащены с сайта ЦБ РФ + собрано саморезолвингом, включая зарубежные домены</td></tr>
<tr><td>✅ <b>Steam</b></td><td>Экономия трафика + решение проблем подключения через прокси</td></tr>
<tr><td>✅ <b>Twitch</b></td><td>Экономия трафика сервера</td></tr>
<tr><td>✅ <b>Pinterest</b></td><td>Блокировка рекламы на сервисе</td></tr>
</tbody>
</table>

### 🔵 PROXY (через VPN)

<table width="100%">
<thead><tr><th align="left">Что</th><th align="left">Зачем</th></tr></thead>
<tbody>
<tr><td>🌐 <b>Google Play/Android</b></td><td>Борьба с ТСПУ и банами РКН</td></tr>
<tr><td>🌐 <b>YouTube</b></td><td>Борьба с ТСПУ и банами РКН</td></tr>
<tr><td>🌐 <b>Telegram</b></td><td>Борьба с ТСПУ и банами РКН</td></tr>
<tr><td>🌐 <b>GitHub</b></td><td>Борьба с ТСПУ и банами РКН</td></tr>
<tr><td>🌐 <b>Twitch-ads</b></td><td>Возвращаем полное качество (Source) стримов с блокировкой рекламы</td></tr>
<tr><td>🌐 <b>Весь остальной интернет</b></td><td>Все, чего нет в других списках, включая все зарубежные CDN</td></tr>
</tbody>
</table>

---

## 🇷🇺 DNS

<table width="100%">
<thead><tr><th align="center">Назначение</th><th align="left">Сервер</th><th align="left">Зачем</th></tr></thead>
<tbody>
<tr><td align="center">🏠 Domestic (direct)</td><td><a href="https://dns.yandex.ru/">Яндекс DNS</a> <code>77.88.8.8</code></td><td>Для работы ВЕЗДЕ в РФ — без вариантов в реалиях БС, шатдаунов и ТСПУ. Низкий пинг в РФ</td></tr>
<tr><td align="center">🌍 Remote (proxy)</td><td><a href="https://www.quad9.net/">Quad9 DNS</a> <code>9.9.9.9</code></td><td>Резолвинг-DNS для проксируемого трафика</td></tr>
</tbody>
</table>

---

## 🔄 Автообновление

> [!IMPORTANT]
> Конфиги автоматически обновляются при выходе новых релизов [roscomvpn-geoip](https://github.com/hydraponique/roscomvpn-geoip) и [roscomvpn-geosite](https://github.com/hydraponique/roscomvpn-geosite)

GitHub Actions:
- Проверяет теги апстрим-репозиториев
- Обновляет URL и таймстемпы в JSON-конфигах
- Генерирует base64-диплинки для Happ и INCY
- Коммитит изменения автоматически

## 🔗 Связанные проекты

- [roscomvpn-geoip](https://github.com/hydraponique/roscomvpn-geoip) — IP-диапазоны (geoip.dat)
- [roscomvpn-geosite](https://github.com/hydraponique/roscomvpn-geosite) — доменные списки (geosite.dat)
