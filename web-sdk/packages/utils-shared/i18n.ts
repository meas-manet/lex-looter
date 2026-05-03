import _ from 'components-shared/node_modules/utils-shared/node_modules/@types/lodash';
import type { Messages } from '@lingui/core';

import type { Language } from 'components-shared/node_modules/utils-shared/node_modules/state-shared';

export type MessagesMap = Record<Language, Messages>;

export const mergeMessagesMaps = (messagesMapList: MessagesMap[]) => {
	const merged = messagesMapList
		.filter(Boolean)
		.reduce((acc, current) => _.merge(acc, current), {} as MessagesMap);

	return merged;
};
