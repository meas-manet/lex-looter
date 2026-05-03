import { getContextEventEmitter } from 'components-ui-pixi/node_modules/utils-event-emitter';
import { getContextXstate } from 'components-ui-pixi/node_modules/utils-xstate';
import { getContextLayout } from 'components-ui-pixi/node_modules/utils-layout';
import { getContextApp } from 'pixi-svelte';

import type { EmitterEventUi } from 'components-ui-pixi/src/types';

export const getContext = () => ({
	...getContextEventEmitter<EmitterEventUi>(),
	...getContextXstate(),
	...getContextLayout(),
	...getContextApp(),
});
