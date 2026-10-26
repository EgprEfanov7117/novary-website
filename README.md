# NOVARY — статический сайт

Статический сайт на HTML5, CSS3 и Vanilla JavaScript. Фреймворков, сборщика,
зависимостей приложения, аналитики и сетевых запросов при просмотре нет.
Шрифты и изображения размещены локально.

## Локальный запуск

Из любой директории выполните:

```bash
python3 -m http.server 8001 --bind 127.0.0.1 --directory /Users/egor/Desktop/NOVARY/novary-website
```

Откройте **http://127.0.0.1:8001**. Остановка — `Ctrl+C`.
Страница услуг: **http://127.0.0.1:8001/services.html**.
Портфолио: **http://127.0.0.1:8001/projects.html**.
О студии: **http://127.0.0.1:8001/about.html**.
Контакты: **http://127.0.0.1:8001/contact.html**.
Установка npm-пакетов не нужна. Открытие `index.html` через `file://` не подходит
для JavaScript-модулей: используйте HTTP-сервер.

## Структура

```text
novary-website/
├── index.html
├── services.html              # Отдельная коммерческая страница услуг
├── projects.html              # Список демонстрационных проектов
├── about.html                 # Философия студии, процесс и роль AI
├── contact.html               # Начало обсуждения проекта в Telegram
├── robots.txt                 # Правила без вымышленного домена
├── dist/                      # Публичная сборка, исключена из Git
├── projects/                  # barber-cult.html и forma-architects.html
├── assets/
│   ├── css/styles.css
│   ├── css/services.css        # Только композиция страницы услуг
│   ├── css/projects.css        # Только портфолио и страницы проектов
│   ├── css/about.css           # Только композиция страницы студии
│   ├── css/contact.css         # Только композиция страницы контактов
│   ├── js/config.js
│   ├── js/main.js
│   ├── fonts/                  # Локальные WOFF и лицензии SIL OFL
│   ├── images/                 # Настоящие превью концептов и Open Graph
│   └── favicon.svg
├── docs/
│   ├── DESIGN_SYSTEM.md        # Исходная дизайн-система
│   ├── HOMEPAGE_STRUCTURE.md   # Исходная структура и тексты
│   ├── IMPLEMENTATION_NOTES.md # Соответствие реализации и уточнения
│   ├── SERVICES_PAGE.md        # Страница услуг, запуск и проверка
│   ├── PROJECTS_SECTION.md     # Портфолио, источники и границы проверки
│   ├── projects-checks.json    # Результаты браузерных проверок портфолио
│   ├── ABOUT_PAGE.md           # Страница студии, запуск и границы проверки
│   ├── about-checks.json       # Результаты браузерных проверок страницы студии
│   ├── CONTACT_PAGE.md         # Контакты, запуск и границы проверки
│   └── contact-checks.json     # Результаты браузерных проверок контактов
├── scripts/check_site.py       # Проверки без сторонних зависимостей
├── scripts/check_services.py   # Ресурсы, якоря и семантика страницы услуг
├── scripts/check_projects.py   # Кейсы, вложенные пути и сохранность старых файлов
├── scripts/check_about.py      # Студия, маршруты и необязательное сравнение с исходным снимком
├── scripts/check_contact.py    # Контакты, маршруты и необязательное сравнение с исходным снимком
├── scripts/build.py            # Allowlist, зависимости, SEO и проверка сборки
├── scripts/test_build.py       # Изолированные тесты production-сборки
├── scripts/audit_browser.py    # Регрессия Chromium, dev-инструмент
├── scripts/measure_performance.py # Локальные измерения LCP/CLS
├── previews/                  # Финальные снимки desktop и mobile
├── PRODUCT.md                 # Подтверждённые сведения и границы проекта
├── CREDITS.md
├── QA_REPORT.md
├── .gitignore
└── README.md
```

## Визуальная концепция

Крупная типографика слева и схема «идея → структура → интерфейс» справа.
Тёмная палитра Obsidian / Graphite, один синий акцент, открытые текстовые блоки
и крупные экраны проектов. Inter используется для всей кириллицы, Space Grotesk —
для латинского брендинга. Цвета, размеры и отступы задаются CSS-переменными.

Реализованы шапка, мобильное меню, hero, два концепта портфолио, четыре услуги,
четыре этапа работы, подход к AI, шесть вопросов, Telegram CTA и футер.

Меню использует нативный `dialog`: фон недоступен для взаимодействия,
Tab остаётся внутри, Escape закрывает меню, фокус возвращается на кнопку.
При переходе к разделу фокус переносится к его содержимому. FAQ использует
нативные `details` / `summary` и работает без JavaScript. Навигация без JavaScript
остаётся видимой. Услуги открываются на `services.html`, проекты — на
`projects.html`; «О студии» — на `about.html`, «Контакты» — на `contact.html`.
Все пять основных страниц существуют; из кейсов ссылка ведёт на `../contact.html`.
На внутренних страницах CTA «Обсудить проект» ведёт к их контактному блоку.
Состав и проверка страниц описаны в [docs/SERVICES_PAGE.md](docs/SERVICES_PAGE.md),
[docs/PROJECTS_SECTION.md](docs/PROJECTS_SECTION.md)
[docs/ABOUT_PAGE.md](docs/ABOUT_PAGE.md)
и [docs/CONTACT_PAGE.md](docs/CONTACT_PAGE.md).

## Конфигурация и подготовка к публикации

### Публичный адрес Telegram-бота

В **`assets/js/config.js`** уже указан предоставленный пользователем адрес:

```js
export const TELEGRAM_BOT_URL = "https://t.me/novary_studio_bot";
```

Это единая настройка контактных ссылок главной, hero-концептов, услуг,
портфолио, обеих страниц проектов, страницы студии и контактов.
Ссылки подключаются общим `assets/js/main.js` и открывают бота в новой вкладке.
Без JavaScript или при некорректной настройке остаётся уведомление о временной
недоступности канала. **Токен из `.env` Telegram-бота сюда переносить нельзя.**
При локальной проверке внешний Telegram не открывался, бот не запускался
и сообщения не отправлялись.

### Production-сборка и домен

Для публикации используйте **только `dist/`**. Корень проекта содержит документы
и служебные файлы. Сборка требует Python 3.10+ и стандартную библиотеку;
npm и сборщик JavaScript не нужны. Из корня `novary-website`:

```bash
python3 scripts/build.py
python3 scripts/build.py --check
python3 -m http.server 8002 --bind 127.0.0.1 --directory dist
```

Откройте **http://127.0.0.1:8002/**. Скрипт очищает старую сборку после проверки
входных зависимостей и копирует семь страниц и используемые ресурсы, включая
лицензии шрифтов. Внутренние каталоги и прототипы исключены. Ошибки ресурсов,
якорей, метаданных, потенциальные секреты и небезопасные зависимости останавливают
сборку. При наличии Node синтаксис JavaScript проверяется в явном ESM-режиме.

Домен **пока не определён**. Без него в сборке нет `sitemap.xml`, `canonical`
и `og:url`; Open Graph использует существующее относительное изображение.
Шаблон [docs/sitemap.xml.template](docs/sitemap.xml.template) остаётся вне `dist/`.
После выбора настоящего HTTPS-адреса задайте его локально в переменной
`NOVARY_SITE_URL` и выполните:

```bash
python3 scripts/build.py --site-url "$NOVARY_SITE_URL"
python3 scripts/build.py --check --site-url "$NOVARY_SITE_URL"
```

Сборщик создаст sitemap, директиву Sitemap в robots, canonical, og:url,
абсолютные og:image и twitter:image. Поддерживается базовый путь сайта.
Фиктивный адрес не подставляется. Настройки HTTPS, заголовков и кэша выполняются
на выбранном хостинге. Отчёт — [docs/LAUNCH_CHECKLIST.md](docs/LAUNCH_CHECKLIST.md).

Также перед публикацией подтвердите фактический состав услуг, процесс согласования
и условия передачи проекта. Цены, сроки, отзывы и юридические сведения не придуманы.
Формы, сбор персональных данных и аналитика на сайте отсутствуют.

## Решения по отличиям от исходных документов

Исходные документы проектирования сохранены без изменений. Позднейшие задания уточняют их:

- Контактная форма заменена переходом в Telegram.
- К трём направлениям добавлены AI-решения.
- Появились предоставленные BARBER CULT и FORMA ARCHITECTS, поэтому подключены
  раздел проектов и навигация. Обе работы явно отмечены как концепты.
- Второй hero CTA ведёт к проектам; услуги доступны из меню.
- Для услуг создана `services.html`, для портфолио — `projects.html` и две
  вложенные страницы проектов. Для студии создана `about.html`; «Контакты»
  в меню ведут на отдельную `contact.html`.

## Проверки

```bash
cd /Users/egor/Desktop/NOVARY/novary-website
python3 scripts/check_site.py
python3 scripts/check_hero_concepts.py
python3 scripts/check_services.py
python3 scripts/check_projects.py
python3 scripts/check_about.py
python3 scripts/check_contact.py
python3 scripts/test_build.py
python3 scripts/build.py --check
node --input-type=module --check < assets/js/config.js
node --input-type=module --check < assets/js/main.js
```

Node нужен только для необязательной проверки синтаксиса, а не для работы сайта.
Текущий production-аудит — [LAUNCH_CHECKLIST.md](docs/LAUNCH_CHECKLIST.md).
`QA_REPORT.md` сохраняет историческую проверку ранней главной страницы.
Полные снимки: [desktop](previews/desktop.webp), [mobile](previews/mobile.webp).
Проверки услуг и их границы: [SERVICES_PAGE.md](docs/SERVICES_PAGE.md).
Портфолио: [PROJECTS_SECTION.md](docs/PROJECTS_SECTION.md), включая команду
сравнения с исходным снимком и ссылки на шесть новых превью.
Студия: [ABOUT_PAGE.md](docs/ABOUT_PAGE.md), [проверки](docs/about-checks.json),
[desktop](previews/about-desktop.webp) и [mobile](previews/about-mobile.webp).
Контакты: [CONTACT_PAGE.md](docs/CONTACT_PAGE.md), [проверки](docs/contact-checks.json),
[desktop](previews/contact-desktop.webp) и [mobile](previews/contact-mobile.webp).

Для повторного браузерного аудита нужен доступный Playwright с Chromium
(это dev-инструмент, он не попадает в `dist/`). При работающем сервере `dist/`:

```bash
python3 scripts/audit_browser.py --base-url http://127.0.0.1:8002/ --report docs/production-browser-checks.json --captures previews/launch-png
python3 scripts/measure_performance.py --report docs/production-performance.json
```

Замеры локальные, с эмуляцией сети и CPU; это не Lighthouse и не полевые данные.

## Дальнейшее развитие

Общие токены и компоненты остаются в `assets/css/styles.css`, поведение —
в `assets/js/main.js`. Страница услуг подключает их и `assets/css/services.css`, портфолио и кейсы —
`assets/css/projects.css`, страница студии — `assets/css/about.css`,
контакты — `assets/css/contact.css`.
Новые страницы могут подключать общие файлы.
Навигация на услуги, проекты, студию и контакты использует фактические адреса.
Дублировать hero и весь состав главной на внутренних страницах не требуется.
