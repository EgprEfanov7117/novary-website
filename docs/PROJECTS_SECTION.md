# NOVARY — портфолио и страницы проектов

26 октября 2026 года. Раздел расширяет существующий Digital Architecture.
Визуальная основа — [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) и действующий
`assets/css/styles.css`. Исходные документы проектирования сохранены как история;
их формулировки о стадии «до реализации» не описывают текущий объём сайта.

## Страницы и навигация

- `projects.html` — два демонстрационных проекта, описание и ссылки на кейсы и демосайты.
- `projects/barber-cult.html` — BARBER CULT, сайт барбершопа.
- `projects/forma-architects.html` — FORMA ARCHITECTS, сайт архитектурной студии.

Шапка, мобильное меню, футер и контактный блок используют общие стили и поведение
`assets/js/main.js`. «Услуги» ведут на `services.html`, «Проекты» — на
`projects.html`, «О студии» и «Контакты» в меню — на `index.html#about` и
`index.html#contact` с поправкой на вложенность. CTA «Обсудить проект» открывает
контактный раздел текущей страницы. Хлебные крошки возвращают к главной и списку,
«Следующий проект» связывает оба кейса. Активное направление отмечено `aria-current`.

Контактные ссылки получают `https://t.me/novary_studio_bot` из общего
`assets/js/config.js`. Без JavaScript сохраняются навигация и уведомление
о недоступности Telegram. Ссылки на демосайты открываются в новой вкладке
с `rel="noopener noreferrer"` и доступной подписью об этом.

## Композиция в существующей системе

Общие цвета сохранены: Obsidian `#0B0D0C`, Graphite `#151815`, Electric Blue
`#3D7BFF`, основной текст `#F5F6F2`, вторичный `#8E938A`. Inter обслуживает
кириллицу, Space Grotesk — латинские названия. Локальный `projects.css` добавляет
только композицию портфолио, кейсов и подписанные образцы типографики проектов.

Список начинается с крупного заголовка слева и более тихого введения справа;
обложка BARBER CULT входит в первый экран. На широком экране BARBER CULT занимает
полную ширину контейнера, FORMA отступает вправо и занимает 83,3333% (90% ниже
1200 px). Ниже 768 px страницы переходят в последовательный одноколоночный поток.
В кейсах имя, категория, статус концепции, описание и ссылка предшествуют обложке.
Далее идут контекст, дизайн, реализация, экраны, следующий проект и контакт.

Настоящие интерфейсы показываются без декоративных 3D-рамок и добавленных фильтров.
Синий штрих под обложкой расширяется при hover; изображение слегка увеличивается.
Введение списка появляется один раз за 450 мс, обложка кейса — за 500 мс.
При reduced motion эти появления и переходы отключены. Палитры и Oswald/Manrope
показаны как материалы конкретных проектов, не как новая идентичность NOVARY.

## Подтверждённые функции и границы

Оба бренда вымышленные, оба сайта созданы для портфолио. Это не клиентские заказы.
Метрики, бизнес-результаты, реальные отзывы, награды и сроки не заявляются.
Функции и технологии сверены с локальными `index.html`, `styles.css`, `script.js`
в `../portfolio/barbershop/` и `../portfolio/forma-architects/`.

| Проект | Проверенные возможности демосайта | Граница демонстрации |
| --- | --- | --- |
| BARBER CULT | Адаптивная навигация, секционные переходы, нативный `dialog` с выбранной услугой/мастером, возврат фокуса, переключение трёх текстов отзывов | Реальная запись не выполняется, данные не собираются; отзывы — примеры интерфейса |
| FORMA ARCHITECTS | Адаптивное меню с управлением фокусом и Escape, карточки четырёх концептов с нативным `dialog`, изображением, описанием и характеристиками | Контакт объясняет демостатус; отправки заявки и подключённых соцсетей нет; фотографии не обозначают построенные FORMA объекты |

Оба оригинала используют HTML, CSS и Vanilla JavaScript, локальные шрифты и WebP,
адаптивную вёрстку и reduced motion. Серверной части и фреймворков нет.

## Изображения и лицензии

Обложки `assets/images/barber-cult-{640,960,1440}.webp` и
`forma-architects-{640,960,1440}.webp` переиспользованы из существующего сайта.
Это настоящие первые экраны исходных концептов, снятые при 1440 × 900.

В `assets/images/projects/` добавлены 12 WebP общим размером 583 616 байт.
26 октября 2026 года в Chromium с reduced motion сняты предоставленные
[BARBER CULT](https://egprefanov7117.github.io/barber-cult/) и
[FORMA ARCHITECTS](https://egprefanov7117.github.io/forma-architects/):

| Кадр | Файлы и ширины |
| --- | --- |
| BARBER CULT `#about` | `barber-cult-about-{640,1200}.webp` |
| BARBER CULT `#gallery` | `barber-cult-gallery-{640,1200}.webp` |
| FORMA `#projects` | `forma-architects-projects-{640,1200}.webp` |
| FORMA `#process` | `forma-architects-process-{640,1200}.webp` |
| Первые экраны при viewport 390 × 844 | `{barber-cult,forma-architects}-mobile-{390,780}.webp` |

Источник записан в XMP каждого файла. Варианты мобильных кадров шириной 780
сохраняют тот же вид 390 × 844. `srcset`, `sizes`, размеры и альтернативные тексты
заданы в HTML; дополнительные экраны загружаются лениво. Обложки получают высокий
приоритет. Фотографии внутри экранов остаются материалами оригинальных концептов;
авторство и лицензии перечислены в [CREDITS.md](../CREDITS.md) и исходных credits.
Генеративных изображений и подмены содержимого нет.

`portfolio-oswald.woff` и `portfolio-manrope.woff` скопированы из локальных
оригиналов. Их SIL OFL лицензии — `assets/fonts/Portfolio-OFL-Oswald.txt` и
`Portfolio-OFL-Manrope.txt`. Они применяются только к подписанным образцам.

## Запуск и проверка

```bash
python3 -m http.server 8001 --bind 127.0.0.1 --directory /Users/egor/Desktop/NOVARY/novary-website
```

Откройте `http://127.0.0.1:8001/projects.html`. Вложенные кейсы доступны по
`/projects/barber-cult.html` и `/projects/forma-architects.html`. Сборка не нужна.

```bash
cd /Users/egor/Desktop/NOVARY/novary-website
python3 scripts/check_site.py
python3 scripts/check_hero_concepts.py
python3 scripts/check_services.py
python3 scripts/check_projects.py
```

При наличии исходного временного снимка используйте сравнение:

```bash
python3 scripts/check_projects.py --baseline /private/tmp/novary-projects-before/manifest.json --allow-changed README.md --allow-changed PRODUCT.md --allow-changed CREDITS.md
```

Четыре проверки проходят. Baseline содержит 45 исходных файлов. Обновления трёх
перечисленных документов разрешены явно; прочие прежние файлы сохранены, кроме
10 навигационных `href` у ссылок «Проекты» в `index.html`, `services.html`,
`hero-a.html` и `hero-b.html`. Hero, тело главной и услуг, общие CSS/JS,
оригинальные изображения и превью не менялись.

[projects-checks.json](projects-checks.json) фиксирует 126 пройденных проверок,
0 неуспешных и 0 ошибок браузера. Проверены все три страницы в Chromium:
13 ширин 320, 360, 375, 390, 480, 600, 768, 900, 1024, 1199, 1200, 1440 и 1920 px;
отсутствие горизонтального переполнения, состояние меню, увеличение текста до
200%, клавиатурная skip-ссылка, начальный фокус и удержание фокуса в меню,
Escape и возврат фокуса, внутренние и вложенные маршруты, безопасные внешние
ссылки, загрузка изображений, reduced motion, работа без JavaScript и общий
Telegram-конфиг. Отдельный HEAD-запрос к каждому публичному демосайту вернул 200.
Telegram не запускался, сообщения не отправлялись.

Это локальная проверка Chromium, а не сертификация доступности или проверка
всех браузеров. Impeccable context/detector недоступны: CLI engine отсутствует;
их результат не заявляется. Визуальный просмотр завершён с решением ship,
существенных исправлений нет. Публикация и Git-коммиты не выполнялись.

## Превью

Шесть финальных снимков локальных страниц сохранены с XMP-источником.
Исходные превью других страниц не изменены.

| Страница | Desktop (1440 px) | Mobile (390 px) |
| --- | --- | --- |
| Портфолио | [projects-desktop.webp](../previews/projects-desktop.webp) | [projects-mobile.webp](../previews/projects-mobile.webp) |
| BARBER CULT | [projects-barber-cult-desktop.webp](../previews/projects-barber-cult-desktop.webp) | [projects-barber-cult-mobile.webp](../previews/projects-barber-cult-mobile.webp) |
| FORMA ARCHITECTS | [projects-forma-architects-desktop.webp](../previews/projects-forma-architects-desktop.webp) | [projects-forma-architects-mobile.webp](../previews/projects-forma-architects-mobile.webp) |
