/** Mirror of app/schemas/limits.py so the UI rejects input the API would reject. */
export const LIMITS = {
	title: 255,
	description: 2000,
	text: 500,
	reading: 255,
	example: 1000,
	bulk: 1000
} as const;
