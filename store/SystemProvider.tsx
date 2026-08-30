'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { SimulationEngine } from '@/mocks/simulationEngine';
import { mockArmStatus, mockDetections, mockEvents, mockItems, mockJobs, mockSystemStatus } from '@/mocks/mockData';
import { armService, type ArmCommand } from '@/services/armService';
import { eventService } from '@/services/eventService';
import { itemService } from '@/services/itemService';
import { jobService } from '@/services/jobService';
import { systemService } from '@/services/systemService';
import { visionService } from '@/services/visionService';
import type { ArmStatus, DetectionResult, EventLog, FailureTarget, Item, Job, PageKey, SystemStatus } from '@/types';

interface SystemContextValue {
  page: PageKey; setPage: (page: PageKey) => void;
  status: SystemStatus; arm: ArmStatus; currentJob: Job | null;
  jobs: Job[]; events: EventLog[]; items: Item[]; detections: DetectionResult[];
  failureTarget: FailureTarget; setFailureTarget: (target: FailureTarget) => void;
  startJob: (type: 'PACK' | 'SORT') => Promise<void>;
  stopJob: () => void; emergencyStop: () => void; resetEmergency: () => void;
  sendArmCommand: (command: ArmCommand) => Promise<void>;
  simulateDetection: () => Promise<void>;
  saveItem: (item: Omit<Item, 'id'> & { id?: number }) => Promise<void>;
  deleteItem: (id: number) => Promise<void>; toggleItem: (id: number) => Promise<void>;
}

const SystemContext = createContext<SystemContextValue | null>(null);

export function SystemProvider({ children }: { children: React.ReactNode }) {
  const [page, setPage] = useState<PageKey>('dashboard');
  const [status, setStatus] = useState<SystemStatus>(mockSystemStatus);
  const [arm, setArm] = useState<ArmStatus>(mockArmStatus);
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [jobs, setJobs] = useState<Job[]>(mockJobs);
  const [events, setEvents] = useState<EventLog[]>(mockEvents);
  const [items, setItems] = useState<Item[]>(mockItems);
  const [detections, setDetections] = useState<DetectionResult[]>(mockDetections);
  const [failureTarget, setFailureTarget] = useState<FailureTarget>('NONE');
  const engineRef = useRef<SimulationEngine | null>(null);

  useEffect(() => {
    Promise.all([systemService.getStatus(), itemService.getItems(), jobService.getJobs(), eventService.getEvents(), visionService.getDetections(), armService.getStatus()])
      .then(([nextStatus, nextItems, nextJobs, nextEvents, nextDetections, nextArm]) => {
        setStatus(nextStatus); setItems(nextItems); setJobs(nextJobs); setEvents(nextEvents); setDetections(nextDetections); setArm(nextArm);
      });
  }, []);

  const addEvent = useCallback((level: EventLog['level'], source: EventLog['source'], message: string, jobId?: string) => {
    const event = eventService.createEvent(level, source, message, jobId);
    setEvents((previous) => [event, ...previous].slice(0, 60));
  }, []);

  const startJob = useCallback(async (type: 'PACK' | 'SORT') => {
    if (status.emergencyStop || currentJob?.status === 'RUNNING') return;
    const created = await jobService.createJob(type, items);
    let taskList = (created.tasks ?? []).map((task) => ({ ...task }));
    let retries = 0;
    setCurrentJob(created);
    setStatus((previous) => ({ ...previous, currentState: 'PLAN' }));
    addEvent('INFO', 'SYSTEM', `${created.id} ${type === 'PACK' ? '가방 준비' : '귀가 분류'} 작업을 시작했습니다.`, created.id);

    try {
      for (let index = 0; index < taskList.length; index += 1) {
        taskList = taskList.map((task, taskIndex) => ({ ...task, status: taskIndex === index ? 'RUNNING' : task.status }));
        const task = taskList[index];
        setCurrentJob((previous) => previous ? { ...previous, currentItem: task.itemName, tasks: taskList } : previous);
        const engine = new SimulationEngine();
        engineRef.current = engine;
        await engine.run({
          failure: index === 0 ? failureTarget : 'NONE',
          onStep: (step) => {
            setStatus((previous) => ({ ...previous, currentState: step.state, armStatus: step.source === 'ARM' ? 'BUSY' : previous.armStatus }));
            setArm((previous) => ({ ...previous, state: step.state, currentTask: task.itemName }));
            setCurrentJob((previous) => previous ? { ...previous, currentState: step.state } : previous);
            addEvent(step.level, step.source, `${task.itemName}: ${step.message}`, created.id);
          },
          onRetry: (failedState, retry, message) => {
            retries += 1;
            setCurrentJob((previous) => previous ? { ...previous, currentState: failedState, retryCount: retries } : previous);
            addEvent('ERROR', failedState === 'PICK' ? 'ARM' : 'SYSTEM', `${task.itemName}: ${message} (재시도 ${retry}/2)`, created.id);
          },
        });
        taskList = taskList.map((entry, taskIndex) => taskIndex === index ? { ...entry, status: 'SUCCESS' } : entry);
        setCurrentJob((previous) => previous ? { ...previous, completedItems: index + 1, tasks: taskList, retryCount: retries } : previous);
      }
      const completedAt = new Date().toISOString();
      const durationSeconds = created.startedAt ? Math.max(1, Math.round((Date.now() - new Date(created.startedAt).getTime()) / 1000)) : undefined;
      const completed: Job = { ...created, status: 'SUCCESS', currentState: 'COMPLETE', completedItems: taskList.length, currentItem: undefined, retryCount: retries, completedAt, durationSeconds, tasks: taskList };
      setCurrentJob(completed); setJobs((previous) => [completed, ...previous]);
      setStatus((previous) => ({ ...previous, currentState: 'COMPLETE', armStatus: 'ONLINE' }));
      setArm((previous) => ({ ...previous, state: 'COMPLETE', currentTask: '-', lastResult: 'SUCCESS' }));
      addEvent('SUCCESS', 'SYSTEM', `${created.id} 작업의 모든 물품을 검증하고 완료했습니다.`, created.id);
    } catch {
      const cancelled: Job = { ...created, status: 'CANCELLED', currentState: 'ERROR', completedAt: new Date().toISOString(), tasks: taskList, retryCount: retries };
      setCurrentJob(cancelled); setJobs((previous) => [cancelled, ...previous]);
      setStatus((previous) => ({ ...previous, currentState: 'ERROR', armStatus: 'ONLINE' }));
      addEvent('ERROR', 'SYSTEM', `${created.id} 작업이 안전 정지되었습니다.`, created.id);
    } finally { engineRef.current = null; }
  }, [addEvent, currentJob?.status, failureTarget, items, status.emergencyStop]);

  const stopJob = useCallback(() => { engineRef.current?.cancel(); }, []);
  const emergencyStop = useCallback(() => {
    engineRef.current?.cancel();
    setStatus((previous) => ({ ...previous, emergencyStop: true, currentState: 'ERROR' }));
    setArm((previous) => ({ ...previous, state: 'ERROR', lastCommand: 'STOP', lastResult: 'SUCCESS' }));
    addEvent('ERROR', 'SYSTEM', '비상 정지가 활성화되어 모든 시뮬레이션 동작을 정지했습니다.');
  }, [addEvent]);
  const resetEmergency = useCallback(() => {
    setStatus((previous) => ({ ...previous, emergencyStop: false, currentState: 'IDLE' }));
    setArm((previous) => ({ ...previous, state: 'IDLE', currentTask: '-' }));
    setCurrentJob((previous) => previous?.status === 'RUNNING' ? { ...previous, status: 'CANCELLED', currentState: 'ERROR' } : previous);
    addEvent('WARNING', 'SYSTEM', '비상 정지가 수동으로 해제되었습니다.');
  }, [addEvent]);

  const sendArmCommand = useCallback(async (command: ArmCommand) => {
    if (status.emergencyStop && command !== 'STOP') return;
    setArm((previous) => ({ ...previous, state: command === 'STOP' ? 'IDLE' : 'MOVE', currentTask: '수동 제어', lastCommand: command }));
    addEvent('INFO', 'ARM', `수동 명령 ${command}을(를) 실행합니다.`);
    const result = await armService.sendCommand(command);
    setArm((previous) => ({ ...previous, state: 'IDLE', currentTask: '-', lastCommand: result.command, lastResult: result.result }));
    addEvent('SUCCESS', 'ARM', `${command} 명령이 시뮬레이션에서 완료되었습니다.`);
  }, [addEvent, status.emergencyStop]);

  const simulateDetection = useCallback(async () => {
    const detection = await visionService.simulateDetection(items);
    setDetections((previous) => [detection, ...previous].slice(0, 12));
    addEvent('SUCCESS', 'VISION', `${detection.tagId} ${detection.itemName}을(를) ${detection.gridPosition}에서 탐지했습니다.`);
  }, [addEvent, items]);

  const saveItem = useCallback(async (input: Omit<Item, 'id'> & { id?: number }) => {
    if (input.id) {
      const updated = await itemService.updateItem(input as Item);
      setItems((previous) => previous.map((item) => item.id === updated.id ? updated : item));
      addEvent('INFO', 'SYSTEM', `${updated.name} 물품 정보를 수정했습니다.`);
    } else {
      const created = await itemService.createItem(input, items);
      setItems((previous) => [...previous, created]);
      addEvent('SUCCESS', 'SYSTEM', `${created.name}을(를) 물품 마스터에 추가했습니다.`);
    }
  }, [addEvent, items]);
  const deleteItem = useCallback(async (id: number) => {
    await itemService.deleteItem(id);
    setItems((previous) => previous.filter((item) => item.id !== id));
    addEvent('WARNING', 'SYSTEM', `물품 ID ${id}번을 삭제했습니다.`);
  }, [addEvent]);
  const toggleItem = useCallback(async (id: number) => {
    const target = items.find((item) => item.id === id); if (!target) return;
    const updated = await itemService.updateItem({ ...target, enabled: !target.enabled });
    setItems((previous) => previous.map((item) => item.id === id ? updated : item));
  }, [items]);

  const value = useMemo<SystemContextValue>(() => ({ page, setPage, status, arm, currentJob, jobs, events, items, detections, failureTarget, setFailureTarget, startJob, stopJob, emergencyStop, resetEmergency, sendArmCommand, simulateDetection, saveItem, deleteItem, toggleItem }), [page, status, arm, currentJob, jobs, events, items, detections, failureTarget, startJob, stopJob, emergencyStop, resetEmergency, sendArmCommand, simulateDetection, saveItem, deleteItem, toggleItem]);
  return <SystemContext.Provider value={value}>{children}</SystemContext.Provider>;
}

export function useSystem() {
  const context = useContext(SystemContext);
  if (!context) throw new Error('useSystem must be used inside SystemProvider');
  return context;
}
