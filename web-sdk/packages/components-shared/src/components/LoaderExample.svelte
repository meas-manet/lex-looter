<script lang="ts">
	import LoaderBase from './LoaderBase.svelte';

	type Props = {
		src: string;
	};

	const props: Props = $props();

	let showText = $state(true);
</script>

<LoaderBase
	maxWidth={300}
	backgroundColor={'#000000'}
	timeout={2000}
	src={props.src}
	oncomplete={() => (showText = false)}
/>

<style lang="scss">
	.add-your-loader {
		z-index: 999;
		color: white;
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, 10px);
	}
</style>
