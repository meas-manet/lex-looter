import type { BetType } from 'utils-xstate/node_modules/rgs-requests';

import type { createPrimaryMachines } from 'utils-xstate/src/createPrimaryMachines';
import type { createIntermediateMachineBet } from 'utils-xstate/src/createIntermediateMachineBet';
import type { createIntermediateMachineAutoBet } from 'utils-xstate/src/createIntermediateMachineAutoBet';
import type { createIntermediateMachineResumeBet } from 'utils-xstate/src/createIntermediateMachineResumeBet';

export type IntermediateMachineBet = ReturnType<typeof createIntermediateMachineBet>;
export type IntermediateMachineAutoBet = ReturnType<typeof createIntermediateMachineAutoBet>;
export type IntermediateMachineResumeBet = ReturnType<typeof createIntermediateMachineResumeBet>;

export type IntermediateMachines = {
	bet: IntermediateMachineBet;
	autoBet: IntermediateMachineAutoBet;
	resumeBet: IntermediateMachineResumeBet;
};

export type PrimaryMachines = ReturnType<typeof createPrimaryMachines>;

export type BaseBet = BetType<any>;
