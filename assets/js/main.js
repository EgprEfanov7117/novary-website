import { TELEGRAM_BOT_URL } from "./config.js";

// Ссылка на Telegram включается только после заполнения публичного username.
// Пока адрес не задан, обычная внутренняя ссылка ведёт к честному уведомлению.
function configureTelegram() {
  let botURL;
  try {
    botURL = new URL(TELEGRAM_BOT_URL);
  } catch {
    return;
  }

  const username = botURL.pathname.slice(1);
  const isConfigured = botURL.protocol === "https:"
    && botURL.hostname === "t.me"
    && !botURL.port && !botURL.username && !botURL.password
    && /^[a-z][a-z0-9_]{4,31}$/i.test(username)
    && !username.toUpperCase().includes("REPLACE_WITH");

  if (!isConfigured) return;

  document.querySelectorAll("[data-telegram-link]").forEach((link) => {
    link.href = botURL.href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.setAttribute("aria-label", `${link.textContent.trim()} — в новой вкладке`);
  });
  document.querySelector("#contact-status").textContent =
    "Откроется Telegram-бот NOVARY. Напишите о вашей задаче — ответим в этом же чате.";
}

function configureMenu() {
  const trigger = document.querySelector(".menu-trigger");
  const menu = document.querySelector("#mobile-menu");
  const closeButton = menu.querySelector(".menu-close");
  const desktop = window.matchMedia("(min-width: 1200px)");
  let restoreFocus = true;

  if (typeof menu.showModal !== "function") return;

  trigger.hidden = false;
  document.documentElement.classList.add("js");

  function closeMenu(returnToTrigger = true) {
    restoreFocus = returnToTrigger;
    if (!menu.open) return;
    menu.close();
    trigger.setAttribute("aria-expanded", "false");
    document.documentElement.classList.remove("menu-open");
    if (restoreFocus && !desktop.matches) trigger.focus();
  }

  trigger.addEventListener("click", () => {
    if (menu.open) return;
    restoreFocus = true;
    menu.showModal();
    trigger.setAttribute("aria-expanded", "true");
    document.documentElement.classList.add("menu-open");
    closeButton.focus();
  });

  closeButton.addEventListener("click", () => closeMenu());
  menu.addEventListener("click", (event) => {
    if (event.target === menu) closeMenu();
  });
  menu.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeMenu();
  });

  menu.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", () => {
      closeMenu(false);
      // Переносим фокус к выбранному разделу, а не за закрытую панель.
      document.querySelector(link.getAttribute("href"))?.focus({ preventScroll: true });
    });
  });

  menu.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") return;
    const controls = [...menu.querySelectorAll("a[href], button:not([disabled])")];
    const first = controls[0];
    const last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  desktop.addEventListener("change", (event) => {
    if (event.matches && menu.open) {
      closeMenu(false);
      document.querySelector(".header-inner .wordmark").focus({ preventScroll: true });
    }
  });
}

configureTelegram();
configureMenu();
document.querySelectorAll("[data-year]").forEach((element) => {
  element.textContent = new Intl.DateTimeFormat("ru-RU", { year: "numeric" }).format(new Date());
});
