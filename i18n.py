# Part of J2J (http://JRuDevels.org)

# User-facing interface strings for the transport, keyed by language.
# Every dialog shown to a user (registration form, ad-hoc commands,
# gateway prompts, login status, disco names) renders through t().

DEFAULT = 'en'

# Language code -> native name, shown in the language selection menu.
LANGUAGES = {
    'en': 'English',
    'ru': 'Русский',
    'uk': 'Українська',
}

STRINGS = {
    'en': {
        # registration form
        'reg_title': 'J2J Registration Form',
        'reg_new_instructions':
            'Please enter data for your Jabber account',
        'reg_edit_instructions': 'Please edit data',
        'field_jid': 'Jabber ID',
        'field_password': 'Password',
        'field_domain': 'Domain or IP',
        'field_port': 'Port',
        'field_import_roster': 'Import roster',
        'field_remove_from_roster':
            'Remove contacts from guest roster automatically',
        'field_language': 'Language',
        # login status
        'status_logging_in': 'Logging in...',
        # jabber:iq:gateway
        'gw_desc': 'Enter XMPP name below',
        'gw_prompt': 'XMPP name',
        # ad-hoc command names (disco items / identities)
        'cmd_stat': 'Statistics',
        'cmd_options': 'Options',
        'cmd_replicate_vcard':
            "Replicate host's vCard to guest's account",
        'disco_commands': 'Commands',
        'disco_users': 'Users',
        'disco_guest_server': "Guest's server Discovery",
        'disco_guest_roster': 'Guest roster',
        'disco_online_users': 'Online users',
        # ad-hoc: statistics
        'stat_title': 'J2J Statistics',
        'stat_online_users': 'Online Users: %s',
        'stat_total_users': 'Total Users: %s',
        'stat_version': 'Version: %s',
        'stat_uptime': 'Uptime: %d days %d hours %d minutes %d seconds',
        # ad-hoc: vCard replication
        'replica_err_title': 'Execution error',
        'replica_need_login': 'Please log in first.',
        'replica_title': 'vCard replication',
        'replica_confirm':
            "Are you sure want to replicate your host's vCard to "
            "your guest's account?",
        'replica_yes': 'Yes, do it',
        'replica_cancel_title': 'Execution canceled',
        'replica_cancelled': 'Replication cancelled',
        # ad-hoc: options
        'opts_title': 'J2J Options and Settings',
        'opts_only_roster':
            'Receive messages only from contacts from Guest roster',
        'opts_autoreply_header': 'Auto Reply Settings',
        'opts_autoreply_enabled':
            'Enable Auto Reply for ALL guest contacts',
        'opts_autoreply_forward': 'Always forward messages to me',
        'opts_reply_text': 'Text for Auto Reply (1000 chars max)',
        'note_options_updated': 'Options were updated',
    },
    'ru': {
        'reg_title': 'Форма регистрации J2J',
        'reg_new_instructions':
            'Введите данные вашей Jabber-учётной записи',
        'reg_edit_instructions': 'Измените данные',
        'field_jid': 'Jabber ID',
        'field_password': 'Пароль',
        'field_domain': 'Домен или IP',
        'field_port': 'Порт',
        'field_import_roster': 'Импортировать ростер',
        'field_remove_from_roster':
            'Удалять контакты из гостевого ростера автоматически',
        'field_language': 'Язык',
        'status_logging_in': 'Выполняется вход...',
        'gw_desc': 'Введите XMPP-имя ниже',
        'gw_prompt': 'XMPP-имя',
        'cmd_stat': 'Статистика',
        'cmd_options': 'Настройки',
        'cmd_replicate_vcard':
            'Скопировать vCard хоста в учётную запись гостя',
        'disco_commands': 'Команды',
        'disco_users': 'Пользователи',
        'disco_guest_server': 'Обзор сервера гостя',
        'disco_guest_roster': 'Гостевой ростер',
        'disco_online_users': 'Пользователи в сети',
        'stat_title': 'Статистика J2J',
        'stat_online_users': 'Пользователей в сети: %s',
        'stat_total_users': 'Всего пользователей: %s',
        'stat_version': 'Версия: %s',
        'stat_uptime':
            'Время работы: %d дн. %d ч. %d мин. %d сек.',
        'replica_err_title': 'Ошибка выполнения',
        'replica_need_login': 'Сначала войдите в транспорт.',
        'replica_title': 'Копирование vCard',
        'replica_confirm':
            'Вы действительно хотите скопировать vCard вашего хоста '
            'в учётную запись гостя?',
        'replica_yes': 'Да, выполнить',
        'replica_cancel_title': 'Выполнение отменено',
        'replica_cancelled': 'Копирование отменено',
        'opts_title': 'Параметры и настройки J2J',
        'opts_only_roster':
            'Получать сообщения только от контактов '
            'из гостевого ростера',
        'opts_autoreply_header': 'Настройки автоответа',
        'opts_autoreply_enabled':
            'Включить автоответ для ВСЕХ гостевых контактов',
        'opts_autoreply_forward': 'Всегда пересылать сообщения мне',
        'opts_reply_text':
            'Текст автоответа (максимум 1000 символов)',
        'note_options_updated': 'Настройки сохранены',
    },
    'uk': {
        'reg_title': 'Форма реєстрації J2J',
        'reg_new_instructions':
            'Введіть дані вашого облікового запису Jabber',
        'reg_edit_instructions': 'Змініть дані',
        'field_jid': 'Jabber ID',
        'field_password': 'Пароль',
        'field_domain': 'Домен або IP',
        'field_port': 'Порт',
        'field_import_roster': 'Імпортувати ростер',
        'field_remove_from_roster':
            'Автоматично видаляти контакти з гостьового ростера',
        'field_language': 'Мова',
        'status_logging_in': 'Виконується вхід...',
        'gw_desc': "Введіть XMPP-ім'я нижче",
        'gw_prompt': "XMPP-ім'я",
        'cmd_stat': 'Статистика',
        'cmd_options': 'Налаштування',
        'cmd_replicate_vcard':
            'Скопіювати vCard хоста до облікового запису гостя',
        'disco_commands': 'Команди',
        'disco_users': 'Користувачі',
        'disco_guest_server': 'Огляд сервера гостя',
        'disco_guest_roster': 'Гостьовий ростер',
        'disco_online_users': 'Користувачі в мережі',
        'stat_title': 'Статистика J2J',
        'stat_online_users': 'Користувачів у мережі: %s',
        'stat_total_users': 'Усього користувачів: %s',
        'stat_version': 'Версія: %s',
        'stat_uptime':
            'Час роботи: %d дн. %d год. %d хв. %d с.',
        'replica_err_title': 'Помилка виконання',
        'replica_need_login': 'Спочатку увійдіть у транспорт.',
        'replica_title': 'Копіювання vCard',
        'replica_confirm':
            'Ви справді хочете скопіювати vCard вашого хоста '
            'до облікового запису гостя?',
        'replica_yes': 'Так, виконати',
        'replica_cancel_title': 'Виконання скасовано',
        'replica_cancelled': 'Копіювання скасовано',
        'opts_title': 'Параметри та налаштування J2J',
        'opts_only_roster':
            'Отримувати повідомлення лише від контактів '
            'із гостьового ростера',
        'opts_autoreply_header': 'Налаштування автовідповіді',
        'opts_autoreply_enabled':
            'Увімкнути автовідповідь для УСІХ гостьових контактів',
        'opts_autoreply_forward': 'Завжди пересилати мені повідомлення',
        'opts_reply_text':
            'Текст автовідповіді (макс. 1000 символів)',
        'note_options_updated': 'Налаштування збережено',
    },
}


def normalize(lang):
    """Map arbitrary input (None, 'RU', 'ru-RU') onto a supported code;
    unknown values fall back to DEFAULT."""
    if not lang:
        return DEFAULT
    code = str(lang).strip().lower()
    if code in LANGUAGES:
        return code
    base = code.split('-', 1)[0]
    return base if base in LANGUAGES else DEFAULT


def t(lang, key):
    """Translate *key* into *lang*, falling back to the default
    language and finally to the bare key."""
    table = STRINGS.get(normalize(lang)) or STRINGS[DEFAULT]
    return table.get(key) or STRINGS[DEFAULT].get(key, key)


def options():
    """Sorted (code, native name) pairs for selection menus."""
    return sorted(LANGUAGES.items())
