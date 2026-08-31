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
        'field_import_mode': 'Roster import',
        'import_opt_off': 'Do not import roster',
        'import_opt_subscribe': 'Via subscription requests',
        'import_opt_rosterx': 'Via roster item exchange',
        'import_opt_auto': 'Auto-detect (client support)',
        'field_import_group': 'Group for imported contacts',
        'field_remove_from_roster':
            'Synchronize contact removal host->guest',
        'field_language': 'Language',
        # login status
        'status_logging_in': 'Logging in...',
        # jabber:iq:gateway
        'gw_desc': 'Enter XMPP name below',
        'gw_prompt': 'XMPP name',
        # ad-hoc command names (disco items / identities)
        'cmd_stat': 'Statistics',
        'cmd_options': 'Options',
        'cmd_register': 'Registration',
        'cmd_register_edit': 'Edit account',
        'cmd_delete_account': 'Delete account',
        'del_account_title': 'Delete account?',
        'del_account_warn':
            'This will remove your account and all virtual contacts.',
        'del_account_confirm': 'Confirm deletion',
        'note_account_deleted': 'Account deleted.',
        'note_account_not_deleted': 'Deletion cancelled.',
        'status_online': '%s online',
        'auto_reply_subject': 'J2J Auto Reply Service',
        'opts_rostersync': 'Synchronize rosters guest->host on login',
        'cmd_replicate_vcard':
            "Replicate host's vCard to guest's account",
        'disco_commands': 'Commands',
        'disco_users': 'Users',
        'disco_all_users': 'All users',
        'disco_guest_server': "Guest's server Discovery",
        'disco_guest_roster': 'Guest roster',
        'disco_ungrouped': 'Ungrouped',
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
        'replica_done_title': 'vCard replicated',
        'replica_done': 'Your vCard has been copied to the transport.',
        'replica_error': 'Failed to retrieve vCard from the server.',
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
        # relay (chat states / typing / delivery receipts) subsection
        'opts_relay_header': 'Relay:',
        'opts_typing': 'Typing notifications',
        'opts_chatstates': 'Activity notifications',
        'opts_receipts': 'Delivery notifications',
        # account suspension (user options)
        'opts_enable_account':
            'Enable account',
        'note_account_disabled':
            'Account suspended. Use the same checkbox to re-enable.',
        'note_account_enabled': 'Account re-enabled.',
        'opts_account_disabled_title': 'Account disabled',
        'opts_account_enabled_title': 'Account enabled',
        'msg_suspended':
            'Your account on this transport is suspended. Open the '
            'transport settings (ad-hoc command "Options") to '
            're-enable it, then log in again.',
        # ad-hoc administration menu
        'cmd_admin': 'Administration',
        'admin_title': 'J2J Administration',
        'admin_action_label': 'Action',
        'admin_act_setlang': 'Set default language',
        'admin_act_setmode': 'Default import mechanism',
        'admin_act_setgroup': 'Default import group',
        'note_setmode_done': 'Default import mechanism is now: %s',
        'note_setgroup_done': 'Default import group is now: %s',
        'admin_act_restart': 'Restart service',
        'admin_act_stop': 'Stop service',
        'admin_act_announce': 'Announcement',
        'setlang_title': 'Set default language',
        'note_setlang_done': 'Default language is now: %s',
        'admin_confirm_label': 'Confirm execution',
        'note_restart_done': 'The service is restarting...',
        'note_stop_done': 'The service is stopping...',
        'announce_title': 'Announcement',
        'announce_text_label':
            'Message text (sent to all registered users)',
        'note_announce_sent': 'Announcement sent to %s users',
        'note_action_cancelled': 'Action cancelled',
        # ad-hoc registration
        'note_register_done': 'Account registered.',
        'note_register_updated': 'Registration data updated.',
        'reg_error_invalid_data': 'Invalid registration data.',
        'reg_error_own_account':
            'You cannot connect your own account as a guest.',
        'msg_welcome': 'Welcome to J2J: Jabber-to-Jabber Transport!\nThe transport connects a guest account to your host account and lets you communicate with the guest\'s contacts as if they were in your Jabber client.',
        'msg_menu_heading': 'Available commands:',
        'msg_menu_guest': 'Available commands:\n1. reg - Register a new account\n2. lang - Choose interface language\n3. help or ? - Show help',
        'msg_menu_registered': 'Available commands:\n1. mod - Edit existing account\n2. lang - Choose interface language\n3. on - Enable transport\n4. off - Disable transport\n5. del - Delete account\n6. vcard - Copy host vCard to guest\n7. arepl - Auto-reply settings\n8. trans - Relay and synchronization settings\n9. help or ? - Show help',
        'msg_unknown': 'Unknown command.',
        'msg_invalid_item': 'Invalid menu item. The menu is shown again.',
        'msg_back': 'Exit',
        'msg_exit': 'Exited menu.',
        'msg_confirm': 'Confirm',
        'msg_confirm_menu': '%s\n1. Confirm\n\n0. Exit',
        'msg_lang_menu': 'Language:\n%s\n\n0. Exit',
        'msg_options_menu': 'Choose an option:\n%s',
        'msg_reg_menu': 'Registration fields:\n%s',
        'msg_reg_choices': 'Choices:\n%s',
        'msg_cancelled': 'Cancelled.',
        'msg_yes_no': 'Reply yes or no. Reply 0 to exit.',
        'msg_lang_prompt': 'Choose language: en, ru, uk. Reply 0 to exit.',
        'msg_lang_invalid': 'Choose en, ru, or uk.',
        'msg_lang_done': 'Language set to %s.',
        'msg_delete_confirm': 'Delete your account and all contacts? Reply yes or no.',
        'msg_deleted': 'Account deleted.',
        'msg_vcard_confirm': 'Copy your host vCard to the guest account? Reply yes or no.',
        'msg_vcard_login': 'Log in to the guest account first.',
        'msg_vcard_wait': 'Requesting vCard...',
        'msg_vcard_done': 'vCard copied to the guest account.',
        'msg_vcard_error': 'Could not retrieve the host vCard.',
        'msg_account_on': 'Account enabled.',
        'msg_account_off': 'Account disabled.',
        'msg_arepl_enabled': 'Enable auto-reply? Reply yes or no.',
        'msg_arepl_text': 'Enter auto-reply text, up to 1000 characters.',
        'msg_arepl_invalid': 'Auto-reply text must be at most 1000 characters.',
        'msg_trans_prompt': 'Forward messages while auto-reply is enabled? Currently %s. Reply yes or no.',
        'msg_saved': 'Settings saved.',
        'msg_reg_jid': 'Enter the guest Jabber ID (user@example.org).',
        'msg_reg_password': 'Enter the guest account password.',
        'msg_reg_domain': 'Enter the guest server domain or IP.',
        'msg_reg_port': 'Enter the guest server port (1-65535).',
        'msg_reg_import': 'Choose roster import mode: 1) off, 2) subscription, 3) roster exchange.',
        'msg_reg_group': 'Enter the group for imported contacts (blank for none).',
        'msg_reg_language': 'Choose language by number.',
        'msg_reg_confirm': 'Register these details? Reply yes or no.',
        'msg_reg_invalid': 'Invalid value. The dialog was not changed.',
        'msg_register_done': 'Registration saved.',
    },
    'ru': {
        'reg_title': 'Форма регистрации J2J',
        'reg_new_instructions':
            'Введите данные вашей учетной записи в Jabber',
        'reg_edit_instructions': 'Измените данные',
        'field_jid': 'Jabber ID',
        'field_password': 'Пароль',
        'field_domain': 'Домен или IP',
        'field_port': 'Порт',
        'field_import_roster': 'Импортировать ростер',
        'field_import_mode': 'Импорт ростера',
        'import_opt_off': 'Не импортировать ростер',
        'import_opt_subscribe': 'Через запросы подписки',
        'import_opt_rosterx': 'Через модификацию ростера',
        'import_opt_auto': 'Автоопределение (по поддержке клиента)',
        'field_import_group': 'Группа для импортированных контактов',
        'field_remove_from_roster':
            'Синхронизация удаления контактов хост->гость',
        'opts_relay_header': 'Трансляция:',
        'opts_typing': 'Уведомления о печати',
        'opts_chatstates': 'Уведомление об активности',
        'opts_receipts': 'Уведомление о доставке',
        'field_language': 'Язык',
        'status_logging_in': 'Выполняется вход...',
        'gw_desc': 'Введите XMPP-имя ниже',
        'gw_prompt': 'XMPP-имя',
        'cmd_stat': 'Статистика',
        'cmd_options': 'Настройки',
        'cmd_register': 'Регистрация',
        'cmd_register_edit': 'Изменить учетную запись',
        'cmd_delete_account': 'Удалить учетную запись',
        'del_account_title': 'Удалить учетную запись?',
        'del_account_warn':
            'Это удалит учетную запись и все виртуальные контакты.',
        'del_account_confirm': 'Подтвердить удаление',
        'note_account_deleted': 'Учетная запись удалена.',
        'note_account_not_deleted': 'Удаление отменено.',
        'status_online': '%s в сети',
        'auto_reply_subject': 'Автоответчик J2J',
        'opts_rostersync': 'Синхронизация ростеров гость->хост при логине',
        'cmd_replicate_vcard':
            'Скопировать vCard хоста в учётную запись гостя',
        'disco_commands': 'Команды',
        'disco_users': 'Пользователи',
        'disco_all_users': 'Все пользователи',
        'disco_guest_server': 'Обзор сервера гостя',
        'disco_guest_roster': 'Гостевой ростер',
        'disco_ungrouped': 'Без группы',
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
        'replica_done_title': 'vCard скопирована',
        'replica_done': 'Ваша vCard скопирована в транспорт.',
        'replica_error': 'Не удалось получить vCard с сервера.',
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
        'opts_enable_account':
            'Включить учётную запись',
        'note_account_disabled':
            'Учётная запись отключена. Тот же переключатель '
            'вернёт её в работу.',
        'note_account_enabled': 'Учётная запись снова включена.',
        'opts_account_disabled_title': 'Учётная запись отключена',
        'opts_account_enabled_title': 'Учётная запись включена',
        'msg_suspended':
            'Ваша учётная запись на этом транспорте отключена. '
            'Откройте настройки транспорта (ad-hoc-команда '
            '«Настройки»), чтобы включить её обратно, затем '
            'войдите заново.',
        'cmd_admin': 'Администрирование',
        'admin_title': 'Администрирование J2J',
        'admin_action_label': 'Действие',
        'admin_act_setlang': 'Установить язык по умолчанию',
        'admin_act_setmode': 'Механизм импорта по умолчанию',
        'admin_act_setgroup': 'Группа импорта по умолчанию',
        'note_setmode_done': 'Механизм импорта по умолчанию: %s',
        'note_setgroup_done': 'Группа импорта по умолчанию: %s',
        'admin_act_restart': 'Перезапустить сервис',
        'admin_act_stop': 'Остановить сервис',
        'admin_act_announce': 'Объявление',
        'setlang_title': 'Установка языка по умолчанию',
        'note_setlang_done': 'Язык по умолчанию: %s',
        'admin_confirm_label': 'Подтвердить выполнение',
        'note_restart_done': 'Сервис перезапускается...',
        'note_stop_done': 'Сервис останавливается...',
        'announce_title': 'Объявление',
        'announce_text_label':
            'Текст объявления (будет отправлен всем '
            'зарегистрированным пользователям)',
        'note_announce_sent': 'Объявление отправлено %s пользователям',
        'note_action_cancelled': 'Действие отменено',
        'note_register_done': 'Учётная запись зарегистрирована.',
        'note_register_updated': 'Данные регистрации обновлены.',
        'reg_error_invalid_data': 'Некорректные данные регистрации.',
        'reg_error_own_account':
            'Нельзя подключать собственную учётную запись как гостевую.',
        'msg_welcome': 'Добро пожаловать на J2J: Jabber-to-Jabber Transport!\nТранспорт позволяет подключать к основной учетной записи (хост-аккаунту) гостевой аккаунт и общаться с контактами «гостя» так, как будто он прописан непосредственно в вашем jabber-клиенте.',
        'msg_menu_heading': 'Доступные команды:',
        'msg_menu_guest': 'Доступные команды:\n1. reg - Зарегистрировать новый аккаунт\n2. lang - Выбор языка интерфейса\n3. help или ? - Вывести справку',
        'msg_menu_registered': 'Доступные команды:\n1. mod - Изменить существующий аккаунт\n2. lang - Выбор языка интерфейса\n3. on - Включить транспорт\n4. off - Выключить транспорт\n5. del - Удалить аккаунт\n6. vcard - Скопировать визитку хоста в гостя\n7. arepl - Настройки автоответчика\n8. trans - Настройки функций пересылки и синхронизации\n9. help или ? - Вывести справку',
        'msg_unknown': 'Неизвестная команда.',
        'msg_invalid_item': 'Некорректный пункт. Меню показано снова.',
        'msg_back': 'Выход',
        'msg_exit': 'Вышел из меню.',
        'msg_confirm': 'Подтвердить',
        'msg_confirm_menu': '%s\n1. Подтвердить\n\n0. Выход',
        'msg_lang_menu': 'Язык:\n%s\n\n0. Выход',
        'msg_options_menu': 'Выберите настройку:\n%s',
        'msg_reg_menu': 'Поля регистрации:\n%s',
        'msg_reg_choices': 'Варианты:\n%s',
        'msg_cancelled': 'Отменено.',
        'msg_yes_no': 'Ответьте да или нет. 0 для выхода.',
        'msg_lang_prompt': 'Выберите язык: en, ru, uk. 0 для выхода.',
        'msg_lang_invalid': 'Выберите en, ru или uk.',
        'msg_lang_done': 'Язык изменён: %s.',
        'msg_delete_confirm': 'Удалить учётную запись и все контакты? Ответьте да или нет.',
        'msg_deleted': 'Учётная запись удалена.',
        'msg_vcard_confirm': 'Скопировать vCard хоста в гостевую учётную запись? Ответьте да или нет.',
        'msg_vcard_login': 'Сначала войдите в гостевую учётную запись.',
        'msg_vcard_wait': 'Запрашиваю vCard...',
        'msg_vcard_done': 'vCard скопирована в гостевую учётную запись.',
        'msg_vcard_error': 'Не удалось получить vCard хоста.',
        'msg_account_on': 'Учётная запись включена.',
        'msg_account_off': 'Учётная запись отключена.',
        'msg_arepl_enabled': 'Включить автоответ? Ответьте да или нет.',
        'msg_arepl_text': 'Введите текст автоответа, не более 1000 символов.',
        'msg_arepl_invalid': 'Текст автоответа должен быть не длиннее 1000 символов.',
        'msg_trans_prompt': 'Пересылать сообщения при автоответе? Сейчас: %s. Ответьте да или нет.',
        'msg_saved': 'Настройки сохранены.',
        'msg_reg_jid': 'Введите Jabber ID гостя (user@example.org).',
        'msg_reg_password': 'Введите пароль гостевой учётной записи.',
        'msg_reg_domain': 'Введите домен или IP гостевого сервера.',
        'msg_reg_port': 'Введите порт гостевого сервера (1-65535).',
        'msg_reg_import': 'Выберите импорт ростера: 1) нет, 2) подписка, 3) обмен ростером.',
        'msg_reg_group': 'Введите группу импортированных контактов (пусто — без группы).',
        'msg_reg_language': 'Выберите язык по номеру.',
        'msg_reg_confirm': 'Сохранить эти данные? Ответьте да или нет.',
        'msg_reg_invalid': 'Некорректное значение. Диалог не изменён.',
        'msg_register_done': 'Регистрация сохранена.',
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
        'field_import_mode': 'Імпорт ростера',
        'import_opt_off': 'Не імпортувати ростер',
        'import_opt_subscribe': 'Через запити підписки',
        'import_opt_rosterx': 'Через модифікацію ростера',
        'import_opt_auto': "Автовизначення (за підтримкою клієнта)",
        'field_import_group': 'Група для імпортованих контактів',
        'field_remove_from_roster':
            'Синхронізація видалення контактів хост->гість',
        'opts_relay_header': 'Трансляція:',
        'opts_typing': 'Сповіщення про друк',
        'opts_chatstates': 'Сповіщення про активність',
        'opts_receipts': 'Сповіщення про доставку',
        'field_language': 'Мова',
        'status_logging_in': 'Виконується вхід...',
        'gw_desc': "Введіть XMPP-ім'я нижче",
        'gw_prompt': "XMPP-ім'я",
        'cmd_stat': 'Статистика',
        'cmd_options': 'Налаштування',
        'cmd_register': 'Реєстрація',
        'cmd_register_edit': 'Змінити обліковий запис',
        'cmd_delete_account': 'Видалити обліковий запис',
        'del_account_title': 'Видалити обліковий запис?',
        'del_account_warn':
            'Це видалить обліковий запис і всі віртуальні контакти.',
        'del_account_confirm': 'Підтвердити видалення',
        'note_account_deleted': 'Обліковий запис видалено.',
        'note_account_not_deleted': 'Видалення скасовано.',
        'status_online': '%s у мережі',
        'auto_reply_subject': 'Автовідповідач J2J',
        'opts_rostersync': 'Синхронізація ростерів при вході',
        'cmd_replicate_vcard':
            'Скопіювати vCard хоста до облікового запису гостя',
        'disco_commands': 'Команди',
        'disco_users': 'Користувачі',
        'disco_all_users': 'Усі користувачі',
        'disco_guest_server': 'Огляд сервера гостя',
        'disco_guest_roster': 'Гостьовий ростер',
        'disco_ungrouped': 'Без групи',
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
        'replica_done_title': 'vCard скопійовано',
        'replica_done': 'Ваша vCard скопійовано у транспорт.',
        'replica_error': 'Не вдалося отримати vCard з сервера.',
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
        'opts_enable_account':
            'Увімкнути обліковий запис',
        'note_account_disabled':
            'Обліковий запис вимкнено. Той самий перемикач '
            'поверне його в роботу.',
        'note_account_enabled': 'Обліковий запис знову увімкнено.',
        'opts_account_disabled_title': 'Обліковий запис вимкнено',
        'opts_account_enabled_title': 'Обліковий запис увімкнено',
        'msg_suspended':
            "Ваш обліковий запис на цьому транспорті вимкнено. "
            "Відкрийте налаштування транспорту (ad-hoc-команда "
            "«Налаштування»), щоб увімкнути його знову, потім "
            "увійдіть повторно.",
        'cmd_admin': 'Адміністрування',
        'admin_title': 'Адміністрування J2J',
        'admin_action_label': 'Дія',
        'admin_act_setlang': 'Встановити мову за замовчуванням',
        'admin_act_setmode': 'Механізм імпорту за замовчуванням',
        'admin_act_setgroup': 'Група імпорту за замовчуванням',
        'note_setmode_done': 'Механізм імпорту за замовчуванням: %s',
        'note_setgroup_done': 'Група імпорту за замовчуванням: %s',
        'admin_act_restart': 'Перезапустити сервіс',
        'admin_act_stop': 'Зупинити сервіс',
        'admin_act_announce': 'Оголошення',
        'setlang_title': 'Встановлення мови за замовчуванням',
        'note_setlang_done': 'Мова за замовчуванням: %s',
        'admin_confirm_label': 'Підтвердити виконання',
        'note_restart_done': 'Сервіс перезапускається...',
        'note_stop_done': 'Сервіс зупиняється...',
        'announce_title': 'Оголошення',
        'announce_text_label':
            'Текст оголошення (надійде всім зареєстрованим '
            'користувачам)',
        'note_announce_sent': 'Оголошення надіслано %s користувачам',
        'note_action_cancelled': 'Дію скасовано',
        'note_register_done': 'Обліковий запис зареєстровано.',
        'note_register_updated': 'Дані реєстрації оновлено.',
        'reg_error_invalid_data': 'Некоректні дані реєстрації.',
        'reg_error_own_account':
            'Не можна підключати власний обліковий запис як гостьовий.',
        'msg_welcome': 'Ласкаво просимо до J2J: Jabber-to-Jabber Transport!\nТранспорт дозволяє підключити гостьовий обліковий запис до основного та спілкуватися з його контактами так, ніби вони додані безпосередньо до вашого Jabber-клієнта.',
        'msg_menu_heading': 'Доступні команди:',
        'msg_menu_guest': 'Доступні команди:\n1. reg - Зареєструвати новий обліковий запис\n2. lang - Вибір мови інтерфейсу\n3. help або ? - Показати довідку',
        'msg_menu_registered': 'Доступні команди:\n1. mod - Змінити обліковий запис\n2. lang - Вибір мови інтерфейсу\n3. on - Увімкнути транспорт\n4. off - Вимкнути транспорт\n5. del - Видалити обліковий запис\n6. vcard - Скопіювати vCard хоста до гостя\n7. arepl - Налаштування автовідповіді\n8. trans - Налаштування пересилання та синхронізації\n9. help або ? - Показати довідку',
        'msg_unknown': 'Невідома команда.',
        'msg_invalid_item': 'Некоректний пункт. Меню показано знову.',
        'msg_back': 'Вихід',
        'msg_exit': 'Вийшов із меню.',
        'msg_confirm': 'Підтвердити',
        'msg_confirm_menu': '%s\n1. Підтвердити\n\n0. Вихід',
        'msg_lang_menu': 'Мова:\n%s\n\n0. Вихід',
        'msg_options_menu': 'Оберіть налаштування:\n%s',
        'msg_reg_menu': 'Поля реєстрації:\n%s',
        'msg_reg_choices': 'Варіанти:\n%s',
        'msg_cancelled': 'Скасовано.',
        'msg_yes_no': 'Відповідайте так або ні. 0 для виходу.',
        'msg_lang_prompt': 'Оберіть мову: en, ru, uk. 0 для виходу.',
        'msg_lang_invalid': 'Оберіть en, ru або uk.',
        'msg_lang_done': 'Мову змінено: %s.',
        'msg_delete_confirm': 'Видалити обліковий запис і всі контакти? Відповідайте так або ні.',
        'msg_deleted': 'Обліковий запис видалено.',
        'msg_vcard_confirm': 'Скопіювати vCard хоста до гостьового облікового запису? Відповідайте так або ні.',
        'msg_vcard_login': 'Спочатку увійдіть до гостьового облікового запису.',
        'msg_vcard_wait': 'Запитую vCard...',
        'msg_vcard_done': 'vCard скопійовано до гостьового облікового запису.',
        'msg_vcard_error': 'Не вдалося отримати vCard хоста.',
        'msg_account_on': 'Обліковий запис увімкнено.',
        'msg_account_off': 'Обліковий запис вимкнено.',
        'msg_arepl_enabled': 'Увімкнути автовідповідь? Відповідайте так або ні.',
        'msg_arepl_text': 'Введіть текст автовідповіді, не більше 1000 символів.',
        'msg_arepl_invalid': 'Текст автовідповіді має бути не довшим за 1000 символів.',
        'msg_trans_prompt': 'Пересилати повідомлення під час автовідповіді? Зараз: %s. Відповідайте так або ні.',
        'msg_saved': 'Налаштування збережено.',
        'msg_reg_jid': 'Введіть Jabber ID гостя (user@example.org).',
        'msg_reg_password': 'Введіть пароль гостьового облікового запису.',
        'msg_reg_domain': 'Введіть домен або IP гостьового сервера.',
        'msg_reg_port': 'Введіть порт гостьового сервера (1-65535).',
        'msg_reg_import': 'Оберіть імпорт ростера: 1) ні, 2) підписка, 3) обмін ростером.',
        'msg_reg_group': 'Введіть групу імпортованих контактів (порожньо — без групи).',
        'msg_reg_language': 'Оберіть мову за номером.',
        'msg_reg_confirm': 'Зберегти ці дані? Відповідайте так або ні.',
        'msg_reg_invalid': 'Некоректне значення. Діалог не змінено.',
        'msg_register_done': 'Реєстрацію збережено.',
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
