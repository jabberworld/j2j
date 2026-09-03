# J2J: Jabber-to-Jabber Transport — руководство для агента

## Обзор

J2J — это транспорт для XMPP (XEP-0114, `jabber:component:accept`): компонент,
который подключает к **хост-аккаунту** пользователя его **гостевую учётную запись**
на другом сервере и транслирует контакты гостя в ростер хоста, позволяя общаться
с ними как с обычными контактами.

- Назначение: мост «мой основной Jabber-аккаунт ↔ мой/чужой гостевой аккаунт».
- Стек: Python 3.11, Slixmpp 1.10.0 (asyncio), SQLite, `cryptography` (Fernet).
- Точка входа: `main.py` → `j2j.py` (`J2JComponent`).
- Текущая версия: `2.5.2` (см. `main.py`, история — `Changelog.txt`).

## Архитектура

Две ключевые сущности:

- **Компонент** — `J2JComponent` (`j2j.py`). Подключён к серверу как XEP-0114
  компонент, получает все станзы пользователей, разбирает и маршрутизирует.
- **Гостевой клиент** — `GuestClient` (`client.py`). Отдельная C2S-сессия,
  поднимаемая от имени подключённой гостевой учётной записи. Ключ сессии —
  bare/host JID (`fro`), по нему ищется в `self.clients`.

### Маршрутизация станз

- `onMessage` / `onPresence` / `onIq` (`j2j.py`) — вход компонента.
- Если адресат — сам компонент (`_isToComponent`), станза обрабатывается локально
  (`componentIq`, регистрация, disco, vCard, gateway и т.п.).
- Иначе — `routeStanza` (j2j.py:253) на хост-сторону гостя:
  `to` декодируется через `unquoteJID` → `retag` в пространство `jabber:client` →
  отправка гостевому `GuestClient`.
- Обратное направление: `GuestClient.route()` (client.py) — станзы гостя
  перекодируются в `jabber:component:accept` и уходят хосту через компонент.
- Оба пути валидируют `JID` и **гасят повреждённые станзы**, не роняя поток.

### Виртуальные JID (экранирование)

`quoteJID`/`unquoteJID` (`utils.py`, обёртки `J2JComponent.quoteJID/unquoteJID`):

- Текущая схема: `@`→`%`, `%`→`\%` (контакт `user@server` = `user%server@transport`).
- Legacy-схема (транспорт 2007, JRuDevels / XEP-0106): `\40`=`@`, `\2f`=`/`, `\5c`=`\`
  и др. — также распознаётся в `unquoteJID` через `_LEGACY_ESCAPES`.

### Регистрация

Единая точка валидации — `submitRegistration` (j2j.py:949). Обслуживает три
интерфейса: `jabber:iq:register` (`setRegister`), ad-hoc «register» (`adhoc.setRegisterAdhoc`)
и чат-диалог (`dialogs._submitRegistration`).

- **Запрет закольцовки**: guest-JID не может совпадать с host-JID регистрирующегося
  (`fro.bare`, регистронезависимо) → `conflict`. Продублировано в
  `connectGuestSession` (защита от уже сохранённых записей).

### Прочее

- **Карбонсы** (XEP-0280, `client.py`): гостевая сессия включает carbons; исходящие
  сообщения с других клиентов зеркалятся хосту, входящие копии отбрасываются.
- **Импорт/синхронизация ростера** (`client.py` + `roster.py`): режимы off/subscribe/
  rosterx/auto, зеркалирование `db.rosters`, удаление исчезнувших контактов
  (unsubscribe-пары или XEP-0144 delete), приоритет `virtual_contacts`.
- **База** (`database.py`): SQLite, таблицы `users`, `rosters`, `users_options`,
  `crypto_meta` (схема — `j2j.schema.sqlite`, создаётся автоматически).
  Пароли гостей шифруются Fernet (`dbCrypto.py`), если задан `[database] master_password`.
- **i18n** (`i18n.py`): языки en/ru/uk; все пользовательские строки — через
  `i18n.t(lang, key)`; `getUserLang`/`effectiveLang` на компоненте.
- **Чат-интерфейс** (`dialogs.py`): текстовые меню (reg/mod/lang/on/off/del/vcard/arepl/trans).
- **Ad-hoc команды** (`adhoc.py`): stat, options, register, replicate_vCard, delete_account, admin.
- **Конфиг** (`config.py`, шаблон `j2j.conf.example`): секции `[general]` `[component]`
  `[process]` `[database]` `[admins]` `[debug]`.
- **Логирование** (`debug.py`): консоль/файл, уровни, досылки регистраций/логинов,
  сырые дампы станз.

## Конвенции кода

- Без комментариев в коде, если они не поясняют нетривиальное решение; стиль
  файлов сохранять (отступы, кавычки, переносы — как в соседнем коде).
- JID читать/строить через `JID(...)` внутри `try/except InvalidJID`; битые адреса
  не должны ронять обработчик/поток (образец — `client.route()`, `routeStanza`).
- Сравнение bare-JID — регистронезависимое, через `str(...).lower()`.
- i18n-строки: новую пользовательскую строку добавлять **во все три языка сразу**
  (en/ru/uk), ключ — рядом с `reg_error_invalid_data` в блоке регистрации.
- Не оставлять мёртвый код и не ломать обратную совместимость экранирования JID.
- Ошибки гостю: iq с malformed адресом — `jid-malformed`; запрет закольцовки —
  `conflict` (`etype=cancel`).

## Процессы и команды

- Проверка синтаксиса: `python3 -m py_compile *.py`.
- Импорт-проверка: `python3 -c "import utils, client, j2j, adhoc, database, roster, i18n, debug, dialogs, config, dbcrypto"`.
- Тест-харнессы небольшие пишутся инлайн (bash+python3 heredoc) с фейковыми
  компонентом/клиентом; тестового фреймворка в репозитории нет.
- **Режим Plan/Build**: по умолчанию (Plan) агент только исследует и составляет
  план; переходить к правкам только по явной команде вида «Реализуй».
- **Версия** задаётся в `main.py` (`version = "2.5.x"`).
- **Changelog** — `Changelog.txt`, новые записи сверху, формат: `X.Y.Z:` + строки
  с префиксами `[fix] [add] [chg] [imp]` на русском.
- **Коммит** — один на изменение (правки + версия + changelog), сообщение на
  английском, по стилю истории (`git log --oneline`).
- **Синхронизация документации**: при любом изменении проекта (`AGENTS.md`,
  `SPEC.md`, а также схема/сигнатуры/константы/поведение в коде) обновлять
  `AGENTS.md` и `SPEC.md` в том же изменении, чтобы они оставались актуальными.
  `AGENTS.md` описывает правила работы, `SPEC.md` — техническую спецификацию
  для воссоздания проекта с нуля.
- Не трогать посторонние незакоммиченные правки без согласования; коммитить только
  по явному запросу.

## Таблица файлов

| Файл | Назначение | Где чаще всего правят |
|------|-----------|--------------------|
| `main.py` | Точка входа, CLI, версия | версия, загрузка конфига/базы |
| `j2j.py` | `J2JComponent`: маршрутизация, регистрация, disco/vCard/gateway, оффлайн-учёт | `submitRegistration`, `routeStanza`, `connectGuestSession`, `onMessage/Presence/Iq` |
| `client.py` | `GuestClient`: гостевая C2S-сессия, carbons, импорт/удаление ростера, `route` | `route`, `onPresence`, `onSessionStart`, `_importVia…`, `_removeVia…` |
| `utils.py` | helper: `quoteJID`/`unquoteJID`, `retag`, x-data формы, стазис, `errorCodeMap` | `unquoteJID`, `_LEGACY_ESCAPES`, `addsub` |
| `database.py` | SQLite-доступ, миграции, шифрование паролей | запросы к `users`/`rosters`/`users_options` |
| `dbCrypto.py` | Fernet-шифрование паролей гостей | формат `enc1:` |
| `i18n.py` | переводы en/ru/uk | новые ключи строк |
| `adhoc.py` | ad-hoc команды (stat/options/register/vCard/del/admin) | регистрация, настройки |
| `dialogs.py` | чат-меню | текстовые меню, `_submitRegistration` |
| `roster.py` | сборка/разбор roster и roster-item-exchange | импорт ростера |
| `config.py` | конфиг (INI-секции) | новые опции |
| `debug.py` | логирование | уровни/дампы |
