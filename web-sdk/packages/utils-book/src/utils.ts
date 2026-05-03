import { PUBLIC_CHROMATIC } from 'utils-book/node_modules/envs';
import { stateUrlDerived } from 'utils-book/node_modules/state-shared';
import { requestEndEvent } from 'utils-book/node_modules/rgs-requests';

import type { BaseBookEvent } from 'utils-book/src/types';

export function recordBookEvent<TBookEvent extends BaseBookEvent>({
	bookEvent,
}: {
	bookEvent: TBookEvent;
}) {
	if (PUBLIC_CHROMATIC || stateUrlDerived.replay()) {
		console.log('mock request end-event:', { index: bookEvent.index, type: bookEvent.type });
		return;
	}

	try {
		requestEndEvent({
			eventIndex: bookEvent.index,
			rgsUrl: stateUrlDerived.rgsUrl(),
			sessionID: stateUrlDerived.sessionID(),
		});
	} catch (error) {
		console.error(error);
	}
}

export function checkIsMultipleRevealEvents<TBookEvent extends BaseBookEvent>({
	bookEvents,
}: {
	bookEvents: TBookEvent[];
}) {
	const revealEventCount = bookEvents.filter((bookEvent) => bookEvent.type === 'reveal').length;
	const isMultipleReveals = revealEventCount > 1;
	return isMultipleReveals;
}
