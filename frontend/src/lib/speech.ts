/*
 * Pronunciation with the browser's built-in voices (Web Speech API).
 * Free and offline-capable; quality depends on the voices of each device.
 */

const synth: SpeechSynthesis | null =
	typeof window !== 'undefined' && 'speechSynthesis' in window ? window.speechSynthesis : null;

let voices: SpeechSynthesisVoice[] = [];

function loadVoices(): void {
	if (synth) voices = synth.getVoices();
}

if (synth) {
	loadVoices();
	// Most browsers load the voice list asynchronously.
	synth.addEventListener?.('voiceschanged', loadVoices);
}

function voiceFor(lang: string): SpeechSynthesisVoice | null | undefined {
	const code = lang.toLowerCase();
	const matches = voices.filter((v) => v.lang.toLowerCase().replace('_', '-').split('-')[0] === code);
	if (!voices.length) return undefined; // list not loaded yet: let the browser choose by lang
	return matches.find((v) => v.default) ?? matches.find((v) => v.localService) ?? matches[0] ?? null;
}

/** Say `text` in `lang` (ISO code such as "en"). Silently does nothing if unsupported. */
export function speak(text: string, lang: string): void {
	if (!synth || !text.trim()) return;
	const voice = voiceFor(lang);
	// A device without a voice for this language would read it with the wrong
	// accent (e.g. English words with a Spanish voice): better stay silent.
	if (voice === null) return;
	synth.cancel();
	const utterance = new SpeechSynthesisUtterance(text);
	utterance.lang = voice?.lang ?? lang;
	if (voice) utterance.voice = voice;
	utterance.rate = 0.95;
	synth.speak(utterance);
}

export function stopSpeaking(): void {
	synth?.cancel();
}

export const speechSupported = synth !== null;
