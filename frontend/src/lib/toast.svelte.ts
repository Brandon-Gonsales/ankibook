export const toast = $state({ message: '', visible: false });

let timer: ReturnType<typeof setTimeout> | undefined;

export function notify(message: string): void {
	toast.message = message;
	toast.visible = true;
	clearTimeout(timer);
	timer = setTimeout(() => (toast.visible = false), 3200);
}

export function notifyError(err: unknown): void {
	notify(err instanceof Error ? err.message : 'Algo salió mal.');
}
