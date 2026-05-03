import { stateMeta } from 'components-ui-html/node_modules/state-shared';

export const stateBonus = $state({
	selectedBetModeKey: 'BASE',
});

export const stateBonusDerived = {
	selectedBetModeData: () => stateMeta.betModeMeta[stateBonus.selectedBetModeKey],
};
