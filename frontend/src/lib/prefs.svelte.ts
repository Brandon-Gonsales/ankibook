export type Theme = 'system' | 'light' | 'dark';
export type StudyMode = 'base_to_target' | 'target_to_base' | 'mixed';

const THEME_KEY = 'ankibook-theme';
const MODE_KEY = 'ankibook-mode';

function read(key: string): string | null {
	try {
		return localStorage.getItem(key);
	} catch {
		return null;
	}
}

function write(key: string, value: string | null): void {
	try {
		if (value === null) localStorage.removeItem(key);
		else localStorage.setItem(key, value);
	} catch {
		/* storage unavailable: keep the in-memory value */
	}
}

const savedTheme = read(THEME_KEY);
const savedMode = read(MODE_KEY);

export const prefs: { theme: Theme; mode: StudyMode } = $state({
	theme: savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : 'system',
	mode: savedMode === 'target_to_base' || savedMode === 'mixed' ? savedMode : 'base_to_target'
});

export function setTheme(theme: Theme): void {
	prefs.theme = theme;
	write(THEME_KEY, theme === 'system' ? null : theme);
	applyTheme();
}

export function setMode(mode: StudyMode): void {
	prefs.mode = mode;
	write(MODE_KEY, mode);
}

/** Sync <html data-theme> and the browser UI colour with the current theme. */
export function applyTheme(): void {
	const root = document.documentElement;
	if (prefs.theme === 'system') delete root.dataset.theme;
	else root.dataset.theme = prefs.theme;
	const bg = getComputedStyle(root).getPropertyValue('--paper').trim();
	document.querySelector('meta[name="theme-color"]')?.setAttribute('content', bg);
}
