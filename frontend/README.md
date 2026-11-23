# AnkiBook Web

Frontend móvil de AnkiBook: SvelteKit 3 (SPA) + Firebase Auth (Google).

## Puesta en marcha

```powershell
cd frontend
npm install
copy .env.example .env   # completa las claves VITE_FIREBASE_*
npm run dev              # http://localhost:5173 (también accesible por IP de la red local)
```

El backend debe estar corriendo en `localhost:8000`. En desarrollo, Vite reenvía `/api` al backend, así que no hace falta configurar CORS.

- **Claves de Firebase:** Consola de Firebase → Configuración del proyecto → Tus apps → Web.
- **Probar sin Firebase:** pon `VITE_DEV_UID="dev-user"`. Solo funciona con el backend en `ENVIRONMENT=development`.
- **Probar desde el celular:** abre `http://<IP-de-tu-PC>:5173`. Para que funcione el login con Google, añade esa IP en Firebase → Authentication → Settings → Authorized domains.

## Scripts

| Comando | Qué hace |
| --- | --- |
| `npm run dev` | Servidor de desarrollo |
| `npm run check` | Revisión de tipos (svelte-check) |
| `npm run build` | Genera la versión estática en `build/` (SPA con `200.html` como fallback) |

## Estructura

```text
src/
├── app.css                 # Sistema de 2 colores + modo claro/oscuro
├── lib/
│   ├── api.ts              # Cliente REST del backend
│   ├── auth.svelte.ts      # Sesión Firebase (Google)
│   ├── prefs.svelte.ts     # Tema y dirección de repaso (localStorage)
│   ├── srs.ts              # Vista previa de intervalos (espejo de app/services/srs.py)
│   └── components/         # Sheet, BottomNav, formularios, íconos…
└── routes/
    ├── +page.svelte        # Libros + tarjetas pendientes
    ├── login/              # Inicio de sesión con Google
    ├── books/[id]/         # Lecciones de un libro
    ├── lections/[id]/      # Tarjetas (una o pegando varias)
    ├── cards/[id]/         # Editar tarjeta
    ├── review/             # Sesión de repaso
    └── settings/           # Tema, dirección, cerrar sesión
```

> SvelteKit 3: la configuración va en `vite.config.js` (ya no hay `svelte.config.js`) y el alias de la librería es `#lib` (antes `$lib`).
