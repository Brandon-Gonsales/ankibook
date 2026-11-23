import type { Progress, Rating } from './types';

/*
 * Mirror of app/services/srs.py, used only to label the rating buttons with
 * the interval each one would produce. The backend stays the source of truth.
 */
const MIN = 1 / (24 * 60);

export function previewInterval(progress: Progress | null, rating: Rating): number {
	const state = progress?.state ?? 'new';
	const ease = progress?.ease ?? 2.5;
	if (state === 'new' || state === 'learning') return [MIN, 6 * MIN, 1, 4][rating - 1];
	if (state === 'relearning') return [10 * MIN, 0.5, 1, 2][rating - 1];
	const interval = Math.max(progress?.interval_days ?? 0, 1);
	return [10 * MIN, interval * 1.2, interval * ease, interval * ease * 1.3][rating - 1];
}

export function formatInterval(days: number): string {
	const minutes = Math.round(days * 24 * 60);
	if (minutes < 60) return `${Math.max(1, minutes)} min`;
	const hours = Math.round(days * 24);
	if (hours < 24) return `${hours} h`;
	if (days < 30) return `${Math.round(days)} d`;
	if (days < 365) return `${Math.round(days / 30)} m`;
	return `${(days / 365).toFixed(1)} a`;
}
