import type { ExecutionState, FailureTarget, SimulationStep } from '@/types';

const baseSteps: SimulationStep[] = [
  { state: 'PLAN', level: 'INFO', source: 'SYSTEM', message: '필수 물품을 분석하고 작업 계획을 생성합니다.' },
  { state: 'DETECT', level: 'INFO', source: 'VISION', message: 'AprilTag를 탐지해 물품 위치를 확인합니다.' },
  { state: 'PICK', level: 'INFO', source: 'ARM', message: '로봇팔이 물품 파지를 시작합니다.' },
  { state: 'MOVE', level: 'SUCCESS', source: 'ARM', message: '파지 명령이 완료되어 목적지로 이동합니다.' },
  { state: 'PLACE', level: 'INFO', source: 'ARM', message: '물품을 목적지에 배치합니다.' },
  { state: 'VERIFY', level: 'INFO', source: 'SYSTEM', message: '실제 물품 적재 여부를 검증합니다.' },
];

export class SimulationEngine {
  private cancelled = false;
  cancel() { this.cancelled = true; }

  async run(options: {
    failure: FailureTarget;
    onStep: (step: SimulationStep) => void;
    onRetry: (state: ExecutionState, retry: number, message: string) => void;
  }) {
    this.cancelled = false;
    let failedOnce = false;
    for (const step of baseSteps) {
      if (this.cancelled) throw new Error('CANCELLED');
      options.onStep(step);
      await this.wait(step.state === 'DETECT' || step.state === 'PICK' || step.state === 'MOVE' ? 1100 : 750);
      if (!failedOnce && options.failure === step.state) {
        failedOnce = true;
        options.onRetry(step.state, 1, step.state === 'PICK' ? '물품 파지에 실패했습니다.' : '적재 검증에 실패했습니다.');
        await this.wait(900);
        if (this.cancelled) throw new Error('CANCELLED');
        options.onStep({ state: 'RECOVER', level: 'WARNING', source: 'SYSTEM', message: '회복 절차를 실행하고 재시도합니다.' });
        await this.wait(800);
        options.onStep({ ...step, level: 'SUCCESS', message: `${step.state === 'PICK' ? '물품 파지' : '적재 검증'} 재시도에 성공했습니다.` });
        await this.wait(700);
      }
    }
    if (this.cancelled) throw new Error('CANCELLED');
  }

  private wait(ms: number) { return new Promise<void>((resolve) => setTimeout(resolve, ms)); }
}
