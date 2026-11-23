export const LANGS: { code: string; name: string }[] = [
	{ code: 'es', name: 'Español' },
	{ code: 'en', name: 'Inglés' },
	{ code: 'ja', name: 'Japonés' },
	{ code: 'ko', name: 'Coreano' },
	{ code: 'zh', name: 'Chino' },
	{ code: 'fr', name: 'Francés' },
	{ code: 'de', name: 'Alemán' },
	{ code: 'it', name: 'Italiano' },
	{ code: 'pt', name: 'Portugués' },
	{ code: 'ru', name: 'Ruso' },
	{ code: 'ar', name: 'Árabe' }
];

export function langName(code: string): string {
	return LANGS.find((l) => l.code === code.toLowerCase())?.name ?? code.toUpperCase();
}
