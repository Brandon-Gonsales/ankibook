import {
	GoogleAuthProvider,
	onAuthStateChanged,
	signInWithPopup,
	signInWithRedirect,
	signOut as fbSignOut,
	type User
} from 'firebase/auth';
import { DEV_UID, getFirebaseAuth } from './firebase';

interface Session {
	ready: boolean;
	uid: string | null;
	name: string | null;
	email: string | null;
	photo: string | null;
}

export const session: Session = $state({
	ready: false,
	uid: null,
	name: null,
	email: null,
	photo: null
});

let current: User | null = null;
let started = false;

export function initAuth(): void {
	if (started) return;
	started = true;

	if (DEV_UID) {
		Object.assign(session, { ready: true, uid: DEV_UID, name: 'Desarrollo', email: null, photo: null });
		return;
	}

	const auth = getFirebaseAuth();
	if (!auth) {
		session.ready = true;
		return;
	}

	onAuthStateChanged(auth, (user) => {
		current = user;
		Object.assign(session, {
			ready: true,
			uid: user?.uid ?? null,
			name: user?.displayName ?? null,
			email: user?.email ?? null,
			photo: user?.photoURL ?? null
		});
	});
}

export async function signInWithGoogle(): Promise<void> {
	const auth = getFirebaseAuth();
	if (!auth) throw new Error('Firebase no está configurado.');
	const provider = new GoogleAuthProvider();
	provider.setCustomParameters({ prompt: 'select_account' });
	try {
		await signInWithPopup(auth, provider);
	} catch (err) {
		const code = (err as { code?: string }).code ?? '';
		// Some mobile browsers block popups; fall back to a full redirect.
		if (code === 'auth/popup-blocked' || code === 'auth/operation-not-supported-in-environment') {
			await signInWithRedirect(auth, provider);
			return;
		}
		if (code === 'auth/popup-closed-by-user' || code === 'auth/cancelled-popup-request') return;
		throw err;
	}
}

export async function signOut(): Promise<void> {
	const auth = getFirebaseAuth();
	if (auth) await fbSignOut(auth);
}

/** Headers that authenticate a request against the backend. */
export async function authHeaders(): Promise<Record<string, string>> {
	if (DEV_UID) return { 'X-User-Id': DEV_UID };
	if (!current) return {};
	return { Authorization: `Bearer ${await current.getIdToken()}` };
}
