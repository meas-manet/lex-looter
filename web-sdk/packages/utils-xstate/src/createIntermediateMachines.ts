import { createIntermediateMachineBet } from 'utils-xstate/src/createIntermediateMachineBet';
import { createIntermediateMachineAutoBet } from 'utils-xstate/src/createIntermediateMachineAutoBet';
import { createIntermediateMachineResumeBet } from 'utils-xstate/src/createIntermediateMachineResumeBet';

import type { PrimaryMachines } from 'utils-xstate/src/types';

const createIntermediateMachines = ({
	resumeGame,
	newGame,
	playGame,
	endGame,
}: PrimaryMachines) => {
	const bet = createIntermediateMachineBet({ newGame, playGame, endGame });
	const autoBet = createIntermediateMachineAutoBet({ bet });
	const resumeBet = createIntermediateMachineResumeBet({ resumeGame, playGame, endGame });

	return {
		bet,
		autoBet,
		resumeBet,
	};
};

export { createIntermediateMachines };
