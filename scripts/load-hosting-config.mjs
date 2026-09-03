import { readFileSync } from 'node:fs';

/**
 * 개인 Sites 연결 파일이 없는 clone은 일반 로컬 개발 설정으로 실행한다.
 * 잘못된 JSON이나 읽기 오류는 숨기지 않는다.
 * @param {string | URL} file
 * @returns {{ d1: string | null, r2: string | null } | null}
 */
export function loadHostingConfig(file) {
  let source;
  try {
    source = readFileSync(file, 'utf8');
  } catch (error) {
    if (error && typeof error === 'object' && 'code' in error && error.code === 'ENOENT') return null;
    throw new Error('Sites 설정 파일을 읽을 수 없습니다. 경로와 권한을 확인하세요.', { cause: error });
  }

  let config;
  try {
    config = JSON.parse(source);
  } catch {
    throw new Error('Sites 설정 파일 .openai/hosting.json의 JSON 형식이 올바르지 않습니다.');
  }
  if (!config || typeof config !== 'object' || Array.isArray(config)) {
    throw new Error('Sites 설정 파일은 JSON 객체여야 합니다.');
  }
  for (const key of ['d1', 'r2']) {
    const value = config[key];
    if (value != null && (typeof value !== 'string' || !value.trim())) {
      throw new Error(`Sites 설정의 ${key}는 비어 있지 않은 문자열 또는 null이어야 합니다.`);
    }
  }
  return { d1: config.d1 ?? null, r2: config.r2 ?? null };
}
