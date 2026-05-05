import type { paths } from './schema';
import { fetcher } from 'utils-fetcher';

function resolveRgsUrl(rgsUrl: string, path: string): string {
	const isLocal =
		rgsUrl.startsWith('localhost') ||
		rgsUrl.startsWith('127.0.0.1') ||
		rgsUrl.startsWith('0.0.0.0');
	const protocol = isLocal ? 'http' : 'https';
	return `${protocol}://${rgsUrl}${path}`;
}

export const rgsFetcher = {
	post: async function post<
		T extends keyof paths,
		TResponse = paths[T]['post']['responses'][200]['content']['application/json'],
	>(options: {
		url: T;
		rgsUrl: string;
		variables?: paths[T]['post']['requestBody']['content']['application/json'];
	}): Promise<TResponse> {
		const response = await fetcher({
			method: 'POST',
			variables: options.variables,
			endpoint: resolveRgsUrl(options.rgsUrl, options.url as string),
		});

		if (response.status !== 200) console.error('error', response);
		const data = await response.json();
		return data as TResponse;
	},
	get: async function get<
		T extends keyof paths,
		TResponse = paths[T]['get']['responses'][200]['content']['application/json'],
	>(options: { url: T; rgsUrl: string }): Promise<TResponse> {
		const response = await fetcher({
			method: 'GET',
			endpoint: resolveRgsUrl(options.rgsUrl, options.url as string),
		});

		if (response.status !== 200) console.error('error', response);
		const data = await response.json();
		return data as TResponse;
	},
};
