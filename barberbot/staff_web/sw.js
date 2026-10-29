// Service worker адмінки: показує сповіщення. Push приходить без вмісту (див. barberbot/webpush.py),
// тому текст беремо з API — останнє сповіщення з /api/notes.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  event.waitUntil((async () => {
    let title = "✂️", body = "", tag = "bb";
    try {
      const r = await fetch("api/notes", { credentials: "include", cache: "no-store" });
      const notes = (await r.json()).notes || [];
      const last = notes[notes.length - 1];
      if (last) { title = last.title; body = last.body; tag = "bb-" + last.id; }
    } catch (e) { /* немає мережі — покажемо коротке сповіщення */ }
    await self.registration.showNotification(title, { body, tag, icon: "icon-192.png", badge: "icon-192.png" });
  })());
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil((async () => {
    const wins = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const w of wins) { if ("focus" in w) { w.postMessage("refresh"); return w.focus(); } }
    return self.clients.openWindow("./");
  })());
});
