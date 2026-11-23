import { authHeaders } from './auth.svelte';
import type {
	Book,
	BookDetail,
	Card,
	CardFields,
	Direction,
	DueCard,
	Lection,
	LectionDetail,
	Rating,
	ReviewResult
} from './types';

const BASE = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '');

export class ApiError extends Error {
	status: number;
	constructor(message: string, status: number) {
		super(message);
		this.status = status;
	}
}

function describe(detail: unknown, status: number): string {
	if (typeof detail === 'string') return detail;
	if (Array.isArray(detail) && detail.length) {
		const first = detail[0] as { msg?: string };
		if (first?.msg) return first.msg.replace(/^Value error, /, '');
	}
	if (status === 401) return 'Tu sesión expiró. Vuelve a iniciar sesión.';
	if (status === 404) return 'No encontrado.';
	return 'Algo salió mal. Inténtalo de nuevo.';
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
	const headers: Record<string, string> = { ...(await authHeaders()) };
	if (body !== undefined) headers['Content-Type'] = 'application/json';

	let res: Response;
	try {
		res = await fetch(BASE + path, {
			method,
			headers,
			body: body === undefined ? undefined : JSON.stringify(body)
		});
	} catch {
		throw new ApiError('Sin conexión con el servidor.', 0);
	}

	if (res.status === 204) return undefined as T;
	const data = await res.json().catch(() => null);
	if (!res.ok) throw new ApiError(describe(data?.detail, res.status), res.status);
	return data as T;
}

export type BookInput = Pick<Book, 'title' | 'description' | 'target_lang' | 'base_lang'>;

export const api = {
	books: () => request<Book[]>('GET', '/ankibooks'),
	explore: () => request<Book[]>('GET', '/ankibooks/explore'),
	addToLibrary: (id: string) => request<void>('PUT', `/ankibooks/${id}/library`),
	removeFromLibrary: (id: string) => request<void>('DELETE', `/ankibooks/${id}/library`),
	book: (id: string) => request<BookDetail>('GET', `/ankibooks/${id}`),
	createBook: (data: BookInput) => request<Book>('POST', '/ankibooks', data),
	updateBook: (id: string, data: Partial<BookInput>) => request<Book>('PATCH', `/ankibooks/${id}`, data),
	deleteBook: (id: string) => request<void>('DELETE', `/ankibooks/${id}`),

	lection: (id: string) => request<LectionDetail>('GET', `/lections/${id}`),
	createLection: (bookId: string, data: { name: string; position: number }) =>
		request<Lection>('POST', `/ankibooks/${bookId}/lections`, data),
	updateLection: (id: string, data: { name?: string; position?: number }) =>
		request<Lection>('PATCH', `/lections/${id}`, data),
	deleteLection: (id: string) => request<void>('DELETE', `/lections/${id}`),

	card: (id: string) => request<Card>('GET', `/cards/${id}`),
	createCard: (lectionId: string, data: CardFields) =>
		request<Card>('POST', `/lections/${lectionId}/cards`, data),
	createCards: (lectionId: string, cards: CardFields[]) =>
		request<Card[]>('POST', `/lections/${lectionId}/cards/bulk`, { cards }),
	updateCard: (id: string, data: Partial<CardFields>) => request<Card>('PATCH', `/cards/${id}`, data),
	deleteCard: (id: string) => request<void>('DELETE', `/cards/${id}`),

	/** Without a scope: due cards only. With a book or lesson: due + its new cards. */
	due: (limit = 50, scope: { book?: string; lection?: string } = {}) => {
		const params = new URLSearchParams({ limit: String(limit) });
		if (scope.book) params.set('book_id', scope.book);
		if (scope.lection) params.set('lection_id', scope.lection);
		return request<DueCard[]>('GET', `/reviews/due?${params}`);
	},
	review: (ankicard_id: string, rating: Rating, direction: Direction) =>
		request<ReviewResult>('POST', '/reviews', { ankicard_id, rating, direction })
};
