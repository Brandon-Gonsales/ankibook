import { initializeApp } from 'firebase/app';
import { getAuth, type Auth } from 'firebase/auth';

const env = import.meta.env;

/** Local shortcut: talk to the backend with X-User-Id instead of Firebase. */
export const DEV_UID: string = (env.VITE_DEV_UID ?? '').trim();

export const firebaseConfigured = Boolean(env.VITE_FIREBASE_API_KEY && env.VITE_FIREBASE_PROJECT_ID);

let auth: Auth | null = null;

export function getFirebaseAuth(): Auth | null {
	if (!firebaseConfigured) return null;
	if (!auth) {
		const app = initializeApp({
			apiKey: env.VITE_FIREBASE_API_KEY,
			authDomain: env.VITE_FIREBASE_AUTH_DOMAIN,
			projectId: env.VITE_FIREBASE_PROJECT_ID,
			appId: env.VITE_FIREBASE_APP_ID
		});
		auth = getAuth(app);
		auth.languageCode = 'es';
	}
	return auth;
}
