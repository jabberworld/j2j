# XEPs.md: поддержка стандартов XMPP в J2J

Аннотированный список XEP, которые J2J использует или прозрачно пропускает
через мост. При изменении поведения, добавлении или удалении поддержки какого-либо
XEP — обновляйте этот список в том же изменении.

| XEP | Название | Роль в J2J |
|-----|----------|------------|
| XEP-0030 | Service Discovery | disco#info/disco#items компонента и виртуальных JID; гостевой клиент анонсирует серверу фичи своей сессии |
| XEP-0050 | Ad-Hoc Commands | команды управления: stat, options, register, replicate_vCard, delete_account, admin |
| XEP-0054 | vCard-temp | статическая визитка транспорта и виртуальных контактов; replicate_vCard копирует vCard хоста в гостевую учётку |
| XEP-0085 | Chat State Notifications | состояния чата передаются через мост с учётом опций notify_typing/notify_activity (strip_relay_features) |
| XEP-0100 | Gateway Interaction | jabber:iq:gateway: desc/prompt/jid для запроса регистрации у транспорта |
| XEP-0106 | JID Escaping | виртуальные JID: текущая схема `@`→`%`; legacy-схема (`\40`, `\2f`, `\5c` и др.) распознаётся в unquoteJID для контактов времён транспорта 2007 |
| XEP-0114 | Jabber Component Protocol | `jabber:component:accept` — протокол подключения транспорта к серверу (точка входа `main.py` → `J2JComponent`) |
| XEP-0144 | Roster Item Exchange | импорт ростера гостя на хост (пары-подписки) и удаление исчезнувших контактов (rosterx delete) |
| XEP-0184 | Message Delivery Receipts | подтверждения доставки пропускаются через мост с учётом опции notify_receipts |
| XEP-0198 | Stream Management | гостевой клиент включает stream management: внезапный обрыв потока не роняет виртуальные контакты — сессия переподключается и возобновляет поток (resumption), станзы буферизуются |
| XEP-0199 | XMPP Ping | респондер ping на стороне компонента и keepalive гостевой сессии (гарантирует живость потока) |
| XEP-0280 | Message Carbons | гостевая сессия включает carbons: сообщения, отправленные с других клиентов гостевого аккаунта, зеркалируются на хост |