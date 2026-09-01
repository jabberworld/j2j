# SPEC.md — J2J: Jabber-to-Jabber Transport

Полное описание проекта для воссоздания с нуля. Документ реконструирует
текущее состояние кодовой базы (эталон — файлы репозитория) так, чтобы по
тексту ниже можно было воспроизвести поведение, протокол, схему данных и
структуру кода без чтения исходников. Лицензия GPL-v3; авторы — JRuDevels
(2007, Добров Сергей «Binary»).

Все имена функций, сигнатуры, константы, XML-атрибуты и SQL-схема приведены
в точном соответствии с эталонной реализацией.

---

## 1. Обзор и стек

- **Назначение**: XMPP-транспорт (XEP-0114, `jabber:component:accept`),
  который подключает **гостевую учётную запись** пользователя на удалённом
  сервере к его **хост-аккаунту** и транслирует контакты гостя в ростер хоста,
  позволяя общаться с ними как с обычными контактами главного ростера.
- **Стек**: Python 3.11, Slixmpp 1.10.0 (asyncio), SQLite (stdlib `sqlite3`),
  `cryptography` (Fernet / PBKDF2).
- **Структура модулей** (файл → роль):

| Файл | Роль |
|------|------|
| `main.py` | Точка входа, CLI, daemonize, PID-файл, сигналы, версия |
| `j2j.py` | `J2JComponent` (XEP-0114): маршрутизация, регистрация, disco/vCard/gateway, оффлайн-учёт |
| `client.py` | `GuestClient` (C2S-сессия): carbons, импорт/удаление ростера, `route()` |
| `utils.py` | helper: экранирование JID, retag, X-Data формы, `errorCodeMap`, xmlns-константы |
| `database.py` | SQLite-доступ, миграции, шифрование паролей (`Database`) |
| `dbCrypto.py` | Fernet-шифрование паролей гостей (`dbCrypto`) |
| `config.py` | INI-конфиг (`Config`) |
| `i18n.py` | переводы en/ru/uk (`i18n`) |
| `adhoc.py` | ad-hoc команды (`AdHoc`) |
| `dialogs.py` | чат-интерфейс (`MessageDialogs`) |
| `roster.py` | сборка/разбор ростера и XEP-0144 (`Roster`) |
| `debug.py` | логирование (`Debug`) |

- **Внешние зависимости** (`requirements.txt`): `slixmpp==1.10.0`,
  `aiodns>=3.2.0`, `pyasn1>=0.6.1`, `pyasn1-modules>=0.4.1`, `cryptography>=3.4`.

---

## 2. Конфигурация (`config.py` + `j2j.conf.example`)

Class `Config`; конструктор `Config(configname=["j2j.conf", …])` ищет файл
по порядку: `j2j.conf`, `~/.j2j/j2j.conf`, `/etc/j2j/j2j.conf`. INI-парсинг
через `configparser`; декоратор `config_decorator(section, option, default,
required=False)` экспортирует значение в атрибут `SECTION_OPTION` (верхний
регистр). Булевы — через `getboolean`, целые — `int()`. Неизвестные опции
игнорируются.

Доступные атрибуты (после `__init__`):

- `[general]`:
  - `default_language` → `DEFAULT_LANGUAGE` (нормализуется `i18n.normalize`).
  - `import_mode` → `IMPORT_MODE` (нижний регистр: `off|subscribe|rosterx|auto`).
  - `roster_group_name` → `ROSTER_GROUP_NAME`.
- `[component]`:
  - `JID` → `JID` (обязателен) — JID транспорта.
  - `Host` → `HOST` (обязателен) — адрес сервера.
  - `Port` → `PORT` (обязателен, int) — порт компонента (XEP-0114).
  - `Password` → `PASSWORD` (обязателен) — общий секрет.
  - `Send_probes` → `SEND_PROBES` (bool, default True).
- `[process]`:
  - `Pid` → `PROCESS_PID` (путь к PID-файлу, может быть пустым).
- `[database]`:
  - `Name` → `DB_NAME` (обязателен) — путь к SQLite-файлу.
  - `master_password` → `MASTER_PASSWORD` (default '' = шифрование выключено).
- `[admins]`:
  - `List` → `ADMINS` (список JID через запятую, с пробелов по краям) .
  - `Registrations_notify` → `REGISTRATION_NOTIFY` (bool, default False).
- `[debug]`:
  - `logfile` → `LOGFILE`; `loglevel` → `LOGLEVEL` (default 'info', lowercase);
  - `registrations` → `DEBUG_REGISTRATIONS` (bool, default True);
  - `logins` → `DEBUG_LOGINS` (bool, default False);
  - `component_xml` → `DEBUG_COMPXML` (bool, default False);
  - `clients_xml` → `DEBUG_CLXML` (bool, default False);
  - `clients_jids_to_log` → `DEBUG_CLXMLACL` (default '' — «All» или список JID).

Методы, персистящие значение обратно в конфиг-файл (`_persistOption(option,
value, section='general')`): `setDefaultLanguage(lang)`, `setImportMode(mode)`,
`setRosterGroupName(name)`.

---

## 3. Запуск и жизненный цикл (`main.py`)

- CLI (argparse, `prog='j2j'`): `-c/--config FILE` (кастомный конфиг; иначе
  `Config()` по умолчанию), `-b/--background` (daemonize, только POSIX).
- Версия — константа `version = "2.5.2"`.
- `daemonize()`: двойной fork + `setsid()`, `chdir("/")`, `umask(0)`, перенаправление
  stdio в `/dev/null`.
- PID-файл: пишется (`PROCESS_PID`) после daemonize; удаляется при штатном
  выходе и при отказе старта.
- Старт: `J2JComponent(version, config, config.JID)`; при `database.StartupError`
  печать `Cannot start: <msg>` в stderr, удаление PID, `sys.exit(1)`.
- Затем `c.connect()`, регистрация обработчиков `SIGINT`/`SIGTERM` на
  `c.shutdownHandler`, `loop.run_forever()`.
- После выхода: если `c.restartRequested` — `os.execv` на тот же процесс
  (runtime-restart сохраняет PID). Иначе удаление PID-файла.

---

## 4. Компонент XEP-0114 (`j2j.py`, `J2JComponent(ComponentXMPP)`)

### 4.1 `__init__(self, version, config, cJid)`
- `ComponentXMPP.__init__(str(cJid), config.PASSWORD, host=config.HOST,
  port=config.PORT, plugin_config={}, plugin_whitelist=[])`.
- Поля: `config`, `adhoc=AdHoc(self)`, `VERSION`, `cJid` (str), `clients={}`
  (ключ — full host JID → `GuestClient`), `dialogs=MessageDialogs(self)`,
  `presence_resources={}` (uid → set of forwarded full guest-JID),
  `shuttingDown=False`, `restartRequested=False`, `startTime=0`,
  `pending_disco={}` (iq id → callback), `rosterx_support={}`,
  `pending_vcards={}`, `pending_virtual_iq={}`, `reconnectAttempts=0`,
  `lastRecvData=0.0`, `selfPingIds=set()`, `_selfPingTimer=None`,
  `_livenessTimer=None`, `debug=Debug(...)`, `db=Database(config)`.
- Обработчики событий: `session_start→componentConnected`,
  `disconnected→componentDisconnected`, `connection_failed→componentConnectFailed`.
- `register_handler` Callback для presence/message/iq (`J2JPresence`,
  `J2JMessage`, `J2JIq`) → `onPresence`/`onMessage`/`onIq`.

### 4.2 i18n на компоненте
- `effectiveLang(lang)`: возвращает нормализованный язык или `config.DEFAULT_LANGUAGE`.
- `getUserLang(bare)`: язык из `db.getLangById` (через uid) через `effectiveLang`.

### 4.3 Соединение компонента
- `componentConnected`: `shuttingDown=False`, сброс `reconnectAttempts`,
  `startTime=time.time()`. Если `config.SEND_PROBES` — для каждого active JID
  (`db.activeUserJids()`: registered, non-suspended) шлёт
  `send_presence(ptype='probe', pto=jid, pfrom=self.cJid)`. Включает TCP
  keepalive на сокете компонента, инициализирует `lastRecvData`, запускает
  `_scheduleSelfPing()` и `_scheduleLivenessCheck()`; log «Connected to server…».
- `componentDisconnected`/`componentConnectFailed`: сброс ловушек, логи, при
  `shuttingDown` не переподключаться; защита от рекурсии переподключения через
  `reconnectAttempts`.
- `_scheduleSelfPing`/`sendSelfPing`: периодический `iq ping` (XEP-0199) себе.
- `_scheduleLivenessCheck`/`livenessCheck`: watchdog на `lastRecvData`,
  авто-переподключение при half-open TCP.
- `_cancelLivenessTimers`: отмена таймеров.

### 4.4 Вход станз
- `incoming_filter(xml)`: лог (сырой дамп при `DEBUG_COMPXML`), обновление
  `lastRecvData`.
- `send_raw(data)`: лог исходящих, `ComponentXMPP.send_raw`.
- `db.activeUserJids()` (см. раздел 7.2) — источник адресов для проб;
  `sendProbes()` вызывается из `componentConnected` при `SEND_PROBES`.

### 4.5 Маршрутизация
- `_isToComponent(to)`: `str(to.bare).lower() == str(JID(self.cJid).bare).lower()`
  (нормализованное сравнение).
- `onMessage(el)`: читает `JID(el['from'])`/`JID(el['to'])` в `try/except
  InvalidJID` (исключение → return, гашение). Если `_isToComponent(to)` — локально
  (`dialogs.handle` по `body`). Иначе если `fro.full in self.clients` и
  authenticated → `routeStanza(el, fro, to)`, иначе `sendError(el, 'cancel',
  'service-unavailable')`.
- `onPresence(el)`: аналогично в `try/except InvalidJID`. `_isToComponent` →
  `componentPresence` (или `service-unavailable` при shutdown). Иначе активация
  гостя: добавление presence в `cl.presences_available`, `_available_full`,
  логи, обработка подписок и т.п.
- `onIq(el)`: `try/except InvalidJID`; `_isToComponent(to)` →
  `componentIq(el,fro,to,ID,iqType)`; административные прокси
  (`_proxyAdminVirtualIq`); иначе authenticated-клиент → `routeStanza`, иначе
  `sendError(..., 'cancel','service-unavailable')`.

### 4.6 `routeStanza(el, fro, to)` (компонент → гость)
Полный алгоритм:
1. `cl = self.getClient(fro)`; если нет — return.
2. `real_to = self.unquoteJID(to.full)`.
3. `JID(real_to)` в `try/except InvalidJID` — при сбое debug-лог «Dropping stanza
   to unquotable …»; если `el.name=='iq'` → `sendError(el,'cancel','jid-malformed')`;
   return (станза гасится, поток не роняется).
4. `xml = utils.retag(el.xml, COMPONENT_NS, CLIENT_NS)`; `xml.set('to', real_to)`;
   `xml.attrib.pop('from', None)` (гостевой сервер сам решает отправителя).
5. Для message: `uid` → `opts` → `utils.strip_relay_features(xml, typing,
   activity, receipts)`; **возвращает True, пока в сообщении остался контент
   (body или любой другой child)**. Если возврат False (после очистки контента
   не осталось) — return (пустой остаток не пересылается).
6. `cl.send(utils.tostring(xml))`.

### 4.7 Гостевая сессия
- `connectGuestSession(fro, uid, el)`: если `fro.full in self.clients` — return.
  Логит login, шлёт host-unavailable-статус. `data=db.getDataById(uid)`;
  строит `clientJid = JID(username@domain[/resource])` в `try/except InvalidJID`
  (сбой → `sendError(...,'modify','not-acceptable')`). **Защита от закольцовки**:
  если `str(clientJid.bare).lower()==str(fro.bare).lower()` → `sendError(...,'modify',
  'not-acceptable')` и return. Если `data[3]` пусто — `data[3]=data[2]`.
  Создаёт `GuestClient(uid, el, self, fro, clientJid, data[3], data[1],
  data[4], data[5], data[6], data[7])`, кладёт в `self.clients[fro.full]`.
- `deleteClient(jid)`: удаляет из `self.clients`.
- `disconnectGuestSessions(bare_jid)`: отключает все сессии bare-JID (для suspend).

### 4.8 componentIq и вспомогательные ответы
- `componentIq(...)`: обработка disco#info/items, stats, vCard, gateway,
  jabber:iq:last, version, x-data регистрации, админ-прокси. Отвечает
  `_newResultIq(fro, ID)` + `send(tostring(iq))`.
- `_newResultIq(fro, ID)`: iq type=result, to=fro.full, from=self.cJid, id=ID.
- `getIqGateway`/`setIqGateway`: `jabber:iq:gateway` desc/prompt и ответ
  с `jid` = `quoteJID(prompt)`.
- `getLast`/`getVersion`: seconds с `startTime`; name/version/os (Python, slixmpp).
- `sendIqResult(fro_full, cJid, ID, ns)`: атрибуты to/from/id/type=result + query ns.
- `sendError(el, etype, condition, sender=None)`: генерирует error-станзу из копии
  исходной: `from`/`to` меняются местами, type='error', элемент `<error>` с
  `type=etype`, `code=errorCodeMap[condition]`, `<condition>` в ns
  `urn:ietf:params:xml:ns:xmpp-stanzas`.

### 4.9 vCard
- `getvcard`: для JID транспорта — статическая карточка; для виртуальных JID —
  прокси к гостю (`resultVirtualVcard`, `pending_vcards`).
- `result_vCard(el,...)`: обработка ответа на запрос (репликация).
- vCard репликация (ad-hoc `replicate_vCard`): копирует визитку хоста в гостя.

### 4.10 Disco
- `getDiscoInfo`: identity + supported features (`disco_*` строки i18n).
- `getDiscoItems`: браузер сервисов; для админов — разделы «Все пользователи» и
  «Пользователи в сети», для пользователей — их виртуальные JID
  (`addDiscoItem(query, quoteJID(jid), jid)`).
- `getStats`: элементы `jabber:iq:stats`.

### 4.11 Оффлайн-учёт
- `notePresenceForwarded(uid, full_jid)` / `notePresenceWithdrawn(uid, full_jid)` /
  `drainPresenceResources(uid)`: ведение `presence_resources`.
- `offlineUser(uid, host_jid, client=None, remove=False)`: полный алгоритм
  эвакуации (см. раздел 6.8), создаёт «свежую» станзу на каждый send
  (обход отложенной сериализации slixmpp), гасит дубли, исключает самоконтакт,
  при `remove` шлёт unsubscribe/unsubscribed.

### 4.12 Регистрация (см. также раздел 10)
- `sendProbes`, `requestShutdown(restart=False)`, `shutdownHandler(signum,frame)`.

---

## 5. Гостевой клиент (`client.py`, `GuestClient(ClientXMPP)`)

`PING_INTERVAL = 60`.

### 5.1 `__init__(self, uid, el, component, host_jid, client_jid, server, secret, port=5222, import_roster=False, remove_from_roster=False, import_group=None, test_mode=False)`
- `ClientXMPP.__init__(self, client_jid.full, secret)`.
- Поля: `uid`, `config=component.config`, `xmlstream=self`, `isGTalk=False`,
  `presences={}`, `presences_available=[]`, `presences_available_full=[]`,
  `virtual_contacts=set()` (пары forwarded), `alreadyReply=[]`, `component`,
  `connected=False`, `authenticated=False`, `host_jid`, `guest_roster=Roster(self)`,
  `server`, `port`, `import_roster`, `remove_from_roster`, `import_group`,
  `client_jid`, `need_disconnect=False`, `error=None`, `secret`,
  `presenceSent=False`, `startPresence=el`, `ping_obj=None`,
  `carbons_enabled=False`, `default_domain=server`, `default_port=port`.
- Slixmpp настройки: `auto_authorize=None`, `auto_subscribe=False`
  (своё управление подписками), `enable_direct_tls=False`,
  `enable_plaintext=True` (legacy plaintext/STARTTLS).
- `register_plugin('xep_0280')` (carbons).
- Обработчики событий: `session_start→onSessionStart`, `presence→onPresence`,
  `roster_update→onRosterResult`, `disconnected→onDisconnected`,
  `connection_failed→onConnectFailed`; Callback `GuestMessage`/`GuestIq` →
  `onMessage`/`onIq`.
- Лог `loginsLog("User %s is connecting to %s:%s with guest-jid %s")`.
- Подключение: если не `test_mode` — резолв IPv4 (`socket.getaddrinfo` с
  `AF_INET`), при получении адреса `self.connect(addr, int(port))`, иначе
  `self.connect()` (обход half-open IPv6).

### 5.2 XML logging
- `incoming_filter(xml)` / `send_raw(data)`: дампы через
  `component.clientsXmlsLog(data, jid=self.client_jid.full, hjid=self.host_jid.full, …)`
  с учётом `DEBUG_CLXMLACL`.

### 5.3 `onSessionStart(event)`
- При неудаче (`if not self.authenticated` варианты) — `disconnect()`.
- **TCP keepalive**: если `transport.socket` — `utils.enableTcpKeepalive(sock)`
  (NAT-таймауты, мёртвые хосты без FIN/RST).
- Если `startPresence` — replay (retag в `CLIENT_NS`).
- `self.get_roster()` и `self._enableCarbons()`.
- `authenticated=True; connected=True`. Запуск `ping` (PING_INTERVAL).

### 5.4 `ping()`
- Если `transport` и циркулирует — `send_presence(pto=self.host_jid.full,
  pstatus='', pfrom=self.client_jid.full)` (0-length keepalive); исключения
  глушатся; планирует следующий ping.

### 5.5 `onConnectFailed(event)` / `onDisconnected(event)`
- Лог, `self.error`, `self.connected=False`, отмена ping.
- `onDisconnected` (не при ошибке): **эвакуация оффлайна** — через
  `component.offlineUser(uid, self.host_jid, client=self, remove=False)`
  (покрывает все контакты из `db.rosters`); затем `component.deleteClient(self.host_jid)`.
- `need_disconnect` логика для suspend/disable.

### 5.6 `onRosterResult(iq)` — синхронизация ростера
- `guest_roster.updateFromClientRoster()`.
- Если `not presenceSent` — слать available-презенс хосту с pfrom=`cJid`,
  pstatus=`i18n.t(lang,'status_online') % client_jid.bare`; `presenceSent=True`.
- Ростер-импорт (если `uid` и `import_roster in (1,2)`):
  - `opts=db.getOptsById(uid)`; `rostersync = opts[10] if … else 1`.
  - `self_jids={str(self.client_jid.bare)}` — самоконтакт никогда не импортируется.
  - `dbroster` = строки из `db.rosters`.
  - `removed` = контакты в `dbroster`, отсутствующие в гостевом ростере (и не
    самоконтакт). Если есть: режим 1 → unsubscribe/unsubscribed-пары (свежая
    станза на каждую); иначе `_removeViaRosterExchange` (XEP-0144 delete).
    Перед удалением строки — гашение presence (resource-level из
    `presence_resources`, bare как fallback), затем `DELETE FROM rosters`.
  - `missing` = контакты гостя (кроме самоконтакта). Если `rostersync` — все;
    иначе только не импортированные (`not in dbroster`). Режим 1 →
    `_importViaSubscriptions`, иначе `_importViaRosterExchange`.
  - Запись импортированных в `db.rosters` (без дублей), `db.commit()`.
- Логика «каждый логин предлагать все» vs «только новые» — опция rostersync.

### 5.7 Импорт/удаление ростера
- `_importViaSubscriptions(missing)`: subscribe-презенсы по одному.
- `_importViaRosterExchange(missing)`: единый XEP-0144, jid = `quoteJID(jid)`,
  группа `import_group or config.ROSTER_GROUP_NAME`.
- `_removeViaRosterExchange(removed)`: XEP-0144 «delete» (см. `build_roster_exchange_removal`).

### 5.8 Carbons (XEP-0280)
- `_enableCarbons()`: `self['xep_0280'].enable(timeout=15)`; по завершении
  future — `carbons_enabled=True` или debug-лог.
- `_carbonChild(el)`: возвращает `(direction, inner)` — ищет `{CARBONS_NS}sent`
  или `{CARBONS_NS}received` → `{FORWARD_NS}forwarded` →
  `{CLIENT_NS}message`; иначе `(None,None)`.
- `onMessage(el)`: `_carbonChild`; `sent` → `_mirrorSentCarbon` и return;
  `received` → отбрасывается как дубликат.
- `_mirrorSentCarbon(inner)`: защитные проверки (`carbons_enabled`, тип None/''/'chat',
  наличие body, `from`/`to` строки, `JID(...)` в try/except InvalidJID;
  `fjid.bare==self.client_jid.bare`, получатель реальный («@» есть, не сам),
  uid и гейт `opts[2]`). Строит carbon-копию к хосту: `<message type=chat
  from=host_jid.bare to=host_jid.full>` → `<sent>` → `<forwarded>` →
  `<message type=chat from=host_jid.bare to=quoteJID(tjid.full)>` + `<body>`;
  `component.send(tostring(wrap))`.

### 5.9 `onPresence(pres)`
- `fro = pres['from']` в `try/except InvalidJID` (сбой → return).
- `presType = pres['type']`; пустой `fro` → return.
- Определяет uid по `host_jid`; проверки гейта «только контакты гостевого
  ростера» (`presences_available`), отсев самоконтакта.
- Для чужих `fro` — `virtual_contacts.add(fro.full)`; `available` →
  `component.notePresenceForwarded(uid, fro.full)`; `unavailable` →
  `notePresenceWithdrawn`.
- `self.route(pres)`.

### 5.10 `onIq(el)`
- Маршрутизация ответов компоненту; для disco#info result — подстановка
  vcard-temp feature если отсутствует (проксиvCard); для gateway —
  подстановка `jid`; `RETAG` в компонентный ns; `route`.

### 5.11 `route(el)` (гость → хост)
Полный алгоритм:
1. `fro = JID(el['from'])` и `to = el['to']` читаются **внутри** `try/except
   InvalidJID` (само чтение `el['from']` может кидать InvalidJID); сбой → return
   (станза гасится, поток жив — фикс «Fatal error on SSL»).
2. `if not fro or not fro.full: return` (пустой JID-объект truthy — проверка по `.full`).
3. `to = JID(to)` если задан.
4. Логи; определение uid; `opts=db.getOptsById(uid)`.
5. Гейт onlyroster для message: `opts[2]` и `fro.bare not in guest_roster.items`
   → return.
6. Автоответчик (`opts[3]`): `flag=True` только для message type chat/normal с
   body (не groupchat/headline) и для presence subscribe (в этом случае сразу
   шлётся `unsubscribed`). Если `flag` и отправителя нет в `alreadyReply` —
   `make_message(mto=fro.full, mtype='normal',
   msubject=i18n.t(lang,'auto_reply_subject'), mbody=opts[0])` + занесение в
   `alreadyReply`. Затем если не `autoreplybutforward` (`opts[1]`) — return
   (автоответ вместо пересылки).
7. `xml = utils.retag(el.xml, CLIENT_NS, COMPONENT_NS)`.
8. Для message: `utils.strip_relay_features(xml, bool(opts[7]), bool(opts[8]),
   bool(opts[9]))`; если возврат False (после очистки контент не остался) —
   return.
9. `self.component.send(utils.tostring(xml))`.

- `sendError(el, etype, condition)`: как в компоненте, но через `self.send`.

---

## 6. Виртуальные JID и экранирование (`utils.py`)

xmlns-константы: `XML_NS`, `COMPONENT_NS='jabber:component:accept'`,
`CLIENT_NS='jabber:client'`, `COMMANDS_NS='http://jabber.org/protocol/commands'`,
`DISCO_INFO_NS/…/DISCO_ITEMS_NS`, `STATS_NS`, `VCARD_NS='vcard-temp'`,
`CHATSTATES_NS`, `RECEIPTS_NS`, `CARBONS_NS='urn:xmpp:carbons:2'`,
`FORWARD_NS='urn:xmpp:forward:0'`.

### 6.1 Экранирование JID
- Базовый модульный `_base_quote`/экранирование:
  - **quoteJID(ujid, cJid)**: `@`→`%`, `%`→`\%` (URL-style). Результат —
    `<quoted>@<cJid>`.
  - **unquoteJID(qjid, cJid)**: обратное; двухэтапно: (1) `%`→`@` с учётом
    `\%`→`%`; (2) legacy `re.sub(r'\\([0-9a-f]{2})', …)` по `_LEGACY_ESCAPES`
    (однопроходно, без каскадов; неизвестные `\%`-последовательности не трогаются).
- `_LEGACY_ESCAPES` (hex→символ): `{'20':' ','22':'"','26':'&',"27":"'",
  '2f':'/','3a':':','3c':'<','3e':'>','40':'@','5c':'\\'}`.
- Оборки на компоненте: `J2JComponent.quoteJID(ujid)=utils.quoteJID(ujid,self.cJid)`,
  `J2JComponent.unquoteJID(qjid)=utils.unquoteJID(qjid,self.cJid)`.

### 6.2 Станозы и NS
- `retag(el, src_ns, dst_ns)`: возвращает deep-копию с пере-тегированием
  рекурсивно (смена xmlns). `retag_in_place` — модифицирует на месте.

### 6.3 XML helpers
- `locname(el)` — локальное имя; `nsname(el)` — ns; `children(el,name=None)`.
- `addsub(parent, name, ns, attrib=None, text=None)` — `ET.SubElement` с ns-добавлением.
- `tostring(xml, xmlns=None)` — сериализация с корректными префиксами/ns
  (внутри локальная `ser`).

### 6.4 X-Data формы (jabber:x:data)
- `createForm(iq, formType)`, `addTitle`, `addLabel`, `addCheckBox(name,caption,value)`,
  `addHidden(name,value)`, `addTextBox(name,caption,value,required)`,
  `addTextPrivate`, `addMemo`, `addListSingle(name,caption,value,options)`.
- `xdataFields(el)`, `xdataValue(el, var)`, `xdataValueList(el, var)`.

### 6.5 Разное
- `strToBool(string)`.
- `enableTcpKeepalive(sock)`: TCP keepalive + пробы (TCP_KEEPIDLE/KEEPINTVL etc.).
- `strip_relay_features(xml, typing, activity, receipts)`: удаляет chatstates
  (typing→composing/paused, activity→active/inactive/gone, XEP-0085) и receipts
  (XEP-0184) по тумблерам; **возвращает True, если после очистки остался
  контент (body или любой другой child), иначе False** — вызывающая сторона
  дропает пустой остаток.
- `addDiscoItem(query, jid, name=None, node=None)`, `createCommand(iq, node,
  status, sessionid)`, `createNote(command, notetype, text)`.
- `errorCodeMap` (см. полный словарь в коде): `bad-request 400, conflict 409,
  feature-not-implemented 501, forbidden 403, gone 302, internal-server-error 500,
  item-not-found 404, jid-malformed 400, not-acceptable 406, not-allowed 405,
  not-authorized 401, payment-required 402, recipient-unavailable 404, redirect 302,
  registration-required 407, remote-server-not-found 404, remote-server-timeout 504,
  resource-constraint 500, service-unavailable 503, subscription-required 407,
  undefined-condition 500, unexpected-request 400`.

---

## 7. Схема базы данных (`database.py`)

`class Database`; `__init__(config)`: `sqlite3.connect(config.DB_NAME)`,
открытие курсора, `_initSchema()`, `_initCrypto()`. `__del__` закрывает.

### 7.1 `_initSchema()` — точные DDL
- `users(id INTEGER PRIMARY KEY AUTOINCREMENT, jid TEXT UNIQUE, username TEXT,
  domain TEXT, server TEXT, password TEXT, port INTEGER, import_roster INTEGER
  DEFAULT 0, remove_from_guest_roster INTEGER DEFAULT 0, import_group TEXT)`.
- `rosters(user_id INTEGER, jid TEXT)` + индексы `idx_rosters_user_id`,
  `idx_rosters_user_jid (user_id, jid)`.
- `users_options(user_id INTEGER UNIQUE, replytext TEXT, autoreplybutforward
  INTEGER DEFAULT 0, onlyroster INTEGER DEFAULT 0, autoreplyenabled INTEGER
  DEFAULT 0, language TEXT, disabled INTEGER DEFAULT 0, rostersync INTEGER
  DEFAULT 1)` + индекс `idx_users_options_user_id`.
- `crypto_meta(key TEXT PRIMARY KEY, value TEXT)` — создаётся всегда.
- **Миграции**: для `users_options` через `PRAGMA table_info` — если нет
  `language`, `disabled`, `notify_typing`, `notify_activity`, `notify_receipts`,
  `rostersync` — `ALTER TABLE ADD COLUMN` (перечисленные: `language TEXT`,
  `disabled INTEGER DEFAULT 0`, `notify_typing INTEGER DEFAULT 1`,
  `notify_activity INTEGER DEFAULT 1`, `notify_receipts INTEGER DEFAULT 1`,
  `rostersync INTEGER DEFAULT 1`). Для `users` — если нет `import_group` —
  `ALTER TABLE users ADD COLUMN import_group TEXT`.

> Примечание: файл `j2j.schema.sqlite` — человекочитаемый образец той же схемы;
> фактическая автоконфигурация идёт в `_initSchema()`.

### 7.2 API
- `execute(query, params=())`, `fetchone`, `fetchall`, `commit`, `getCount(table,
  where='', params=())`.
- `getIdByJid(qjid)` → id по `jid` (нижний регистр).
- `getDataById(uid)` → `[username, password, domain, server, port, import_roster,
  remove_from_guest_roster, import_group]` (индексы соответствуют `SELECT
  username,password,domain,server,port,import_roster,remove_from_guest_roster,
  import_group`; `password` на позиции 1 возвращается расшифрованным через
  `_decryptPassword`).
- `getOptsById(uid)` → кортеж `[replytext, autoreplybutforward, onlyroster,
  autoreplyenabled, language, disabled, remove_from_guest_roster, notify_typing,
  notify_activity, notify_receipts, rostersync]` (`remove_from_guest_roster` лежит
  в `users`, остальное — в `users_options`; JOIN). `replytext` по умолчанию '' ,
  `rostersync` по умолчанию 1. Используется `opts[2]` (onlyroster-гейт),
  `opts[7]/[8]/[9]` (notify_typing/activity/receipts), `opts[10]` (rostersync).
- `getLangById(uid)` / `setLangById(uid, lang)`.
- `isDisabled(uid)/setDisabled(uid, flag)`, `setRemoveFromGuestRoster(uid, flag)`.
- `encryptPassword(password)` / `_decryptPassword(stored)` — см. раздел 8.
- `activeUserJids()`: bare JID зарегистрированных и не приостановленных
  пользователей (`LEFT JOIN users_options … COALESCE(o.disabled,0)=0`) — источник
  адресов для `SEND_PROBES`.

### 7.3 Шифрование при старте (`_initCrypto`)
- `master = config.MASTER_PASSWORD or ''`; `encrypted = getCount("users",
  "password LIKE ?", ('enc1:%',))`.
- Если `not master` и есть шифрованные — `StartupError("… encrypted but
  master_password not configured …")`.
- Соль: `SELECT value FROM crypto_meta WHERE key='kdf_salt'`; если нет —
  `dbcrypto.generate_salt()` + INSERT.
- `_cryptoKey = dbcrypto.derive_key(master, salt)`.
- **Миграция открытых**: все `password` не-NULL/непустые и не начинающиеся с
  `enc1:` — переписываются `encryptPassword`; при наличии — commit + log.
- **Fail-fast при неверном master**: берёт первую шифрованную запись и
  `dbcrypto.decrypt`; при `CryptoError` → `StartupError("Master password does
  not match the database")`.

---

## 8. Шифрование паролей (`dbcrypto.py`)

- `PREFIX = "enc1:"`, `ITERATIONS = 600_000`.
- `class CryptoError(ValueError)`.
- `looks_encrypted(value)` → `isinstance(value,str) and value.startswith(PREFIX)`.
- `generate_salt()` → hex (lower) 16 случайных байт, `base64.b16encode`.
- `derive_key(master, salt)` → `PBKDF2HMAC(hashes.SHA256(), length=32,
  salt=salt.encode('ascii'), iterations=ITERATIONS)` → `base64.urlsafe_b64encode`.
- `encrypt(key, plaintext)` → `PREFIX + Fernet(key).encrypt(plaintext).decode()`.
- `decrypt(key, stored)`: если не `looks_encrypted` → `CryptoError`; иначе
  `Fernet(key).decrypt(stored[len(PREFIX):])`; при `InvalidToken/ValueError/
  UnicodeDecodeError` → `CryptoError("decryption failed …")`.

---

## 9. Ростер (XEP-0144; `roster.py` + `client.py`)

- `class Roster`; `__init__(host)`: `self.host=host`, `self.items` и `self.groups`
  наполняются из host-клиента.
- `getGroups(ungrouped="Undefined", exclude=None)`, `getAllInGroup(group,
  ungrouped="Undefined", exclude=None)`, `updateFromClientRoster()`,
  `removeItem(jid)`.
- Псевдогруппа «Без группы» для контактов без групп (локализуется).
- `build_roster_exchange(from_jid, to_jid, items, group)` (client.py): строит
  `<message type=normal to=… from=… id=uuid>` → `<x xmlns=rosterx>` → item`'ы`
  с `jid`, `<group>`. Используется для импорта (action по умолчанию = add).
- `build_roster_exchange_removal(from_jid, to_jid, jids, group=None)`:
  то же, но item'ы с `action="delete"` — удаление.
- Режимы импорта (из формы/конфига): `off`(0), `subscribe`(1), `rosterx`(2),
  `auto`(предвыбор по disco#info). Реализация подписок vs rosterx — см. раздел 5.7.

---

## 10. Регистрация и управление аккаунтом

### 10.1 Единая точка — `submitRegistration(el, fro)` → `(ok, error_condition, created)`
Обслуживает `jabber:iq:register` (`setRegister`), ad-hoc «register»
(`adhoc.setRegisterAdhoc`) и чат-диалог (`dialogs._submitRegistration`).
Порядок валидаций (строго по эталону):
1. `jid = xdataValue(el,'jid')`. **strip()**. Если `jid.count('@') != 1` →
   `("jid-malformed", False)`.
2. `username, server = jid.split('@',1)`. `JID(username+'@'+server)` в
   `try/except InvalidJID`; если есть resource / нет user / нет server → то же.
3. **Запрет закольцовки**: `str(parsed.bare).lower() == str(fro.bare).lower()`
   → `(False, "conflict", False)`.
4. `password = xdataValue(el,'password')`; пустой или `len>256` →
   `not-acceptable`.
5. `domain = xdataValue(el,'domain') or server`; содержит пробел →
   `not-acceptable`; `JID("user@"+domain)` в try (иначе `not-acceptable`).
6. `port=f"{int(...)}"`; вне `1..65535` → `not-acceptable`.
7. `import_roster`: `'2'→2`, `'1'/'true'→1`, `''/'0'/'false'→0`, иначе
   `not-acceptable`.
8. `import_group = (xdataValue or '').strip()[:128] or None`.
9. `language = i18n.normalize(lang_submitted)` если задан; при несовпадении
   `lang_submitted` с его lowercase → `not-acceptable`.
10. `uid = db.getIdByJid(fro.bare)`; `edit = uid is not None`.
- **Новый аккаунт** (`not edit`): INSERT в `users` (jid=fro.bare, username,
  domain, server, `encryptPassword(password)`, port, import_roster, import_group);
  INSERT в `users_options (user_id, language)`; commit; `subscribe`-презенс
  хосту от `cJid`; при `ADMINS и REGISTRATION_NOTIFY` — нотификация админам;
  `registrationsLog`; `(True, None, True)`.
- **Редактирование** (`edit`): если сменились username/server — рассылка
  unsubscribe/unsubscribed по старым контактам ростера и очистка `rosters`;
  `UPDATE users` (заново `encryptPassword`); обновление import_roster/group
  только если поле есть; `setLangById` если язык задан; commit;
  `registrationsLog`; `(True, None, False)`.

### 10.2 Контекст и форма
- `registerContext(fro)` → `(uid, data)`; при отсутствии — свежий шаблон data.
- `defaultImportMode(config, rosterx_supported)`: `auto` → 2 если rosterx иначе 0;
  иначе `{"off":0,"subscribe":1,"rosterx":2}[IMPORT_MODE]`.
- `buildRegisterForm(parent, lang, uid, data, mode_default=None)`: поля jid,
  password, domain, port, import_roster, import_group, language (edit-предвыбор).

### 10.3 `setRegister(el, fro, ID)`
- Если `<remove/>` → `deleteAccount` (или `registration-required` если uid нет);
  ответ `sendIqResult` с ns `jabber:iq:register`.
- Иначе `submitRegistration`; при `not ok` → `sendError(el, etype="cancel" if
  err=="conflict" else "modify", condition=err)`; при ok → `sendIqResult`.

### 10.4 `deleteAccount(fro)`
Teardown: определение сессий (`clients` по `fro.bare+/…`), для каждой —
`offlineUser(uid, cl.host_jid, client=cl, remove=True)` (или `offlineUser(uid,
fro, remove=True)` без сессий), `cl.disconnect()`; DELETE `rosters`,
`users_options`, `users`; commit; `registrationsLog`.

---

## 11. Ad-hoc команды (`adhoc.py`, `AdHoc`)

- `__init__(component)`; `getSid()` — уникальный sid; `getCommandsList(query,
  lang, fro)` — список команд (фильтр по правам/регистрации); `done_sids` —
  множество завершённых sid (защита от повторного «Finish»).
- `onCommand(el, fro, ID, node)`: диспетчер по `node`: `stat` → `getStat`,
  `options` → `getOpts`, `register` → `getRegisterAdhoc`, `replicate_vCard` →
  `getReplica`, `delete_account` → `getDeleteAccount`, `admin` → `getAdmin`.
  Неизвестный/неавторизованный узел — `command-not-found`/`not-authorized`/
  `registration-required`.
- Формы строятся через `utils.createCommand(iq, node, status, sid)` +
  X-Data; статусы `executing`/`completed`/`cancelled`.
- `setRegisterAdhoc(el, iq, sid, fro, ID)`: `submitRegistration`; на «conflict»
  — `reg_error_own_account`, иначе `reg_error_invalid_data`; при ok —
  `note_register_done/updated`; `done_sids[sid]=True`.
- `getDeleteAccount`/`setDeleteAccount`: подтверждение и `deleteAccount`.
- `getReplica`/`setReplica`/`finishReplica`: vCard-репликация (checkbox commit);
  `pending`-завершение через `component.result_vCard`.
- `getStat`: статистика (пользователи, сессии, рwister и т.п.).
- `getOpts`/`setOpts`: форма настроек аккаунта; поля соответствуют
  `users_options` (вкл. rostersync, notify_typing/activity/receipts, disabled,
  autoreply, onlyroster, language). Применение через `setDisabled`,
  `setRemoveFromGuestRoster`, `setLangById` и т.п. Возможен перезапуск гостевой
  сессии при изменении аккаунта.
- `getAdmin`/`setAdmin`: только админы; `adminSetLang` (персист в конфиг),
  `adminSetMode`, `adminSetGroup`, `adminPower` (stop/restart), `adminAnnounce`
  (рассылка всем зарегистрированным).

---

## 12. Чат-диалог (`dialogs.py`, `MessageDialogs`)

- `__init__(component)`: `self.component`, `self.dialogs={}` (bare → state),
  `self.languages={}` (bare → lang), `self.text_vcard_sids={}`.
- `_text(fro, key, *args)` — шлёт местное сообщение через `component.send(...)`.
- `_menu(fro)`: корневое меню (reg-oriented) для незарегистрированных;
  полное (mod/lang/on/off/del/vcard/arepl/trans/help) — для зарегистрированных.
- `handle(fro, body)`: диспетчер команд по тексту; проходит через `_dialog`
  (для многошаговых состояний). Команды: `reg`, `mod`, `lang`, `on`, `off`,
  `del`, `vcard`, `arepl`, `trans`, `help`/`?`, `menu`, `cancel`.
- `_registrationMenu`/`_registrationChoices`/`_registrationStep`: пошаговый
  ввод полей регистрации (jid/password/domain/port/import/group/language);
  подтверждение → `_submitRegistration`.
  - На шаге `jid`: валидация `JID(text)`; **ранняя проверка закольцовки** —
    если `str(candidate.bare).lower()==str(fro.bare).lower()` → показать
    `reg_error_own_account` и вернуть в меню.
- `_submitRegistration(fro, dialog, query=None)`: собирает x-data submit из
  `dialog["fields"]` и вызывает `component.submitRegistration`; при `conflict` →
  `reg_error_own_account`, иначе по результату `msg_register_done`/
  `msg_reg_invalid`; затем `_menu(fro)`.
- `_beginAutoreply`/`_beginTrans`/`_optionsMenu`: подменю автоответчика и
  настроек пересылки/синхронизации.
- `_accountSwitch(fro, enabled)`: вкл/выкл аккаунта.
- `_confirmMenu`, `_requestVcard`, `result_vcard`: vCard + подтверждения.

---

## 13. Переводы (`i18n.py`)

- `DEFAULT='en'`; `LANGUAGES = {'en':'English','ru':'Русский','uk':'Українська'}`.
- `STRINGS = {'en':{...},'ru':{...},'uk':{...}}` — ключи с текстом на трёх
  языках; строки с подстановками используют `%s`/`%d` форматирование.
- `t(lang, key)` → строка: `STRINGS[normalize(lang)]` (fallback на `STRINGS[DEFAULT]`,
  затем вообще на сам ключ). Форматирование `%s`/`%d` вызывающая сторона
  выполняет сама через оператор `%`.
- `options()` → список `(code, native_name)` из `LANGUAGES` (используется в
  меню выбора языка и в форме регистрации).
- `normalize(lang)` → приведение к допустимому коду языка в `LANGUAGES`
  (неверные/пустые — fallback на `DEFAULT`).
- **Правило**: каждую новую пользовательскую строку добавлять во все три языка;
  ключи ошибок регистрации (`reg_error_invalid_data`, `reg_error_own_account`,
  `note_register_done/updated` и т.п.) группируются в блоке регистрации.
- `getUserLang`/`effectiveLang` — на компоненте (см. 4.2).

---

## 14. Логирование (`debug.py`, `Debug`)

- `Debug(logFile, registrations, logins, componentXmlLog, clientsXmlLog,
  clientsJidsToLog, loglevel)`:
  - если `logFile` — file handler, иначе console; `loglevel` → уровень (`debug/
    info/warning/error/critical`).
- Методы: `getTheTime()`, `registrationsLog(message)`, `loginsLog(message)`,
  `loginConflictLog(message)`, `loginErrorLog(message)`, `componentXmlsLog(data,
  out=False)` (сырые дампы, gated `DEBUG_COMPXML`), `clientsXmlsLog(data, jid,
  hjid, out=False)` (gated `DEBUG_CLXML` + `DEBUG_CLXMLACL`).
- `self.logger` — стандартный logging.logger, доступный всем модулям.

---

## 15. Инварианты и правила (переносимы в «Definition of Done»)

1. **Валидация JID**: любые `JID(...)`-чтения и построения — внутри
   `try/except InvalidJID`; повреждённая станза гасится (return), поток не
   роняется. Эталон: `client.route()`, `routeStanza`.
2. **Сравнение bare-JID — регистронезависимо** через `str(...).lower()`.
3. **Запрет закольцовки** (guest-JID == host-JID) — в `submitRegistration`
   (регистрация) и `connectGuestSession` (уже сохранённые). Ошибка: `conflict`
   с `etype=cancel` для iq, `not-acceptable` при логине.
4. **Экранирование**: одинаковая поддержка текущей (`%`) и legacy (`\XX`,
   XEP-0106) схем; не ломать обратную совместимость.
5. **Оффлайн виртуальных контактов**: при отключении гостя — `offlineUser`,
   покрывая все (контакт,ресурс) из `presence_resources` + `virtual_contacts` +
   `presences_*` + `db.rosters`; исключая самоконтакт; уникализация дублей;
   свежая станза на каждый send.
6. **Свежая станза на каждый send** при итеративном шлёте (slixmpp
   сериализует объекты позже) — см. `offlineUser`, `_importVia…`.
7. **Carbons**: только `sent`-копии зеркалятся, `received`-дубликаты
   отбрасываются; гейт onlyroster соблюдается.
8. **i18n**: все пользовательские строки через `i18n.t`; ключ — во всех трёх
   языках.
9. **База**: схема + миграции как в разделе 7; шифрование паролей как в 8;
   fail-fast при неверном/отсутствующем master.
10. **Версия/Changelog**: версия в `main.py`; запись в `Changelog.txt`
   (префиксы `[fix][add][chg][imp]`, русский); один коммит на изменение.

---

## 16. Чек-лист соответствия (Definition of Done)

Для «в точности» восстановления каждый модуль должен пройти:

- [ ] `main.py`: CLI/daemonize/PID/сигналы/restart/`Cannot start`.
- [ ] `config.py`: все `SECTION_OPTION` атрибуты + персист.
- [ ] `j2j.py`: маршрутизация, `routeStanza`, `connectGuestSession`, disco/vCard/
      gateway/stats, `submitRegistration`/`setRegister`/`deleteAccount`,
      `offlineUser`, liveness/self-ping.
- [ ] `client.py`: `__init__`, `onSessionStart` (keepalive+carbons+roster),
      `onPresence`, `onMessage`/carbons, `onIq`, `onRosterResult` (sync/remove/
      import), `route` (все гейты), `sendError`.
- [ ] `utils.py`: quote/unquote (обе схемы), retag, ns, addsub, xdata, stats,
      `errorCodeMap`, keepalive, strip_relay_features.
- [ ] `database.py`: схема + миграции + crypto-инициализация + API.
- [ ] `dbcrypto.py`: `enc1:` формат, PBKDF2, encrypt/decrypt.
- [ ] `roster.py`/`client.py` XEP-0144: add/delete, группы.
- [ ] `adhoc.py`: все команды + `done_sids`.
- [ ] `dialogs.py`: все меню/команды + `submitRegistration`.
- [ ] `i18n.py`: все ключи x3, fallback en.
- [ ] `debug.py`: уровни/файлы/дампы.

Критерии проверки:
- `python3 -m py_compile *.py` — без ошибок.
- `python3 -c "import utils, client, j2j, adhoc, database, roster, i18n, debug, dialogs, config, dbcrypto"` — без ошибок.
- Функциональные тест-харнессы (небольшие heredoc, см. `AGENTS.md`) для:
  маршрутизации, регистрации (вкл. закольцовку→conflict, логин→not-acceptable),
  quote/unquote (текущая + legacy `\40`, `\2f`), карбонсов, ростер-синка.
