// Isolated menu controller for the two comparison pages.
// main.js and the Telegram configuration of the real homepage remain unchanged.
const trigger = document.querySelector(".menu-trigger");
const menu = document.querySelector("#mobile-menu");
const closeButton = menu?.querySelector(".menu-close");
const desktop = window.matchMedia("(min-width: 1200px)");

if (trigger && menu && closeButton && typeof menu.showModal === "function") {
  trigger.hidden = false;
  document.documentElement.classList.add("js");

  function closeMenu(returnFocus = true) {
    if (!menu.open) return;
    menu.close();
    trigger.setAttribute("aria-expanded", "false");
    document.documentElement.classList.remove("menu-open");
    if (returnFocus && !desktop.matches) trigger.focus();
  }

  trigger.addEventListener("click", () => {
    if (menu.open) return;
    menu.showModal();
    trigger.setAttribute("aria-expanded", "true");
    document.documentElement.classList.add("menu-open");
    closeButton.focus();
  });
  closeButton.addEventListener("click", () => closeMenu());
  menu.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeMenu();
  });
  menu.addEventListener("click", (event) => {
    if (event.target === menu) closeMenu();
  });
  menu.querySelectorAll("a[href]").forEach((link) => {
    link.addEventListener("click", () => closeMenu(false));
  });
  menu.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") return;
    const controls = [...menu.querySelectorAll("button:not([disabled]), a[href]")];
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
