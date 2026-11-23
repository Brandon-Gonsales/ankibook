<script lang="ts">
	import { page } from '$app/state';
	import Icon from './Icon.svelte';

	const items = [
		{ href: '/', label: 'Libros', icon: 'home' },
		{ href: '/explore', label: 'Explorar', icon: 'search' },
		{ href: '/review', label: 'Repasar', icon: 'study' },
		{ href: '/settings', label: 'Ajustes', icon: 'settings' }
	] as const;

	function active(href: string): boolean {
		const path = page.url.pathname;
		if (href === '/') return path === '/' || path.startsWith('/books') || path.startsWith('/lections') || path.startsWith('/cards');
		return path.startsWith(href);
	}
</script>

<nav aria-label="Principal">
	{#each items as item (item.href)}
		<a href={item.href} aria-current={active(item.href) ? 'page' : undefined}>
			<Icon name={item.icon} />
			<span>{item.label}</span>
		</a>
	{/each}
</nav>

<style>
	nav {
		position: fixed;
		left: 0;
		right: 0;
		bottom: 0;
		z-index: 20;
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		height: calc(var(--nav-h) + var(--safe-b));
		padding-bottom: var(--safe-b);
		background: color-mix(in srgb, var(--paper) 88%, transparent);
		backdrop-filter: blur(12px);
		-webkit-backdrop-filter: blur(12px);
		border-top: 1px solid var(--line);
	}

	a {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 2px;
		font-size: 0.72rem;
		font-weight: 600;
		color: var(--muted);
	}

	a[aria-current='page'] {
		color: var(--accent);
	}
</style>
