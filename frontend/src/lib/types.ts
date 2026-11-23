export type CardState = 'new' | 'learning' | 'review' | 'relearning';
export type Direction = 'base_to_target' | 'target_to_base';
export type Rating = 1 | 2 | 3 | 4;

export interface Book {
	id: string;
	author_id: string;
	title: string;
	description: string | null;
	target_lang: string;
	base_lang: string;
	created_at: string;
	lections_count: number;
	cards_count: number;
	/** The current user wrote this book and can edit it. */
	is_owner: boolean;
	/** The current user added this (someone else's) book to their library. */
	is_added: boolean;
}

export interface Lection {
	id: string;
	ankibook_id: string;
	name: string;
	position: number;
	cards_count: number;
}

export interface BookDetail extends Book {
	ankilections: Lection[];
}

export interface CardFields {
	base_text: string;
	target_1: string;
	target_2: string | null;
	target_3: string | null;
	reading: string | null;
	example_base: string | null;
	example_target_1: string | null;
	example_target_2: string | null;
	example_target_3: string | null;
}

export interface Card extends CardFields {
	id: string;
	ankilection_id: string;
	created_at: string;
}

export interface LectionDetail extends Lection {
	ankicards: Card[];
}

export interface Progress {
	id: string;
	user_id: string;
	ankicard_id: string;
	state: CardState;
	due: string;
	interval_days: number;
	ease: number;
	reps: number;
	lapses: number;
	last_review: string | null;
}

export interface DueCard {
	card: Card;
	progress: Progress | null;
	lection_id: string;
	lection_name: string;
	book_id: string;
	book_title: string;
}

export interface ReviewResult {
	progress: Progress;
	next_due: string;
	message: string;
}
