'use client';

import { useState } from 'react';
import { Modal, PageHeader } from '@/components/ui';
import { useSystem } from '@/store/SystemProvider';
import type { Item } from '@/types';

const destinations = ['외출 가방', '현관', '침실', '주방', '보호자 확인'];
const categories = ['의료용품', '일상용품', '개인용품', '위생용품', '기타'];

export function ItemsPage() {
  const { items, saveItem, deleteItem, toggleItem } = useSystem();
  const [editing, setEditing] = useState<Item | 'new' | null>(null);
  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    await saveItem({ id: editing === 'new' ? undefined : editing?.id, tagId: String(data.get('tagId')), name: String(data.get('name')), category: String(data.get('category')), destination: String(data.get('destination')), enabled: data.get('enabled') === 'on' });
    setEditing(null);
  };
  return <>
    <PageHeader eyebrow="물품 마스터" title="물품 및 목적지" description="AprilTag와 물품 정보를 연결하고 기본 배치 목적지를 관리합니다." action={<button className="primary" onClick={() => setEditing('new')}>+ 물품 추가</button>} />
    <section className="mapping-rule"><i>→</i><div><b>목적지 판단은 비전이 아닌 물품 마스터가 담당합니다.</b><p>카메라 태그 탐지 → 물품 마스터 조회 → 목적지 확인 → 실행 엔진 작업 생성</p></div></section>
    <section className="panel items-panel"><div className="panel-head"><div><p>등록 물품</p><span>사용 중인 물품 {items.filter((item) => item.enabled).length}개 · 전체 {items.length}개</span></div><label className="table-search"><span>⌕</span><input placeholder="물품명 또는 태그 검색" /></label></div><table><thead><tr><th>태그 ID</th><th>물품명</th><th>분류</th><th>기본 목적지</th><th>사용</th><th>관리</th></tr></thead><tbody>{items.map((item) => <tr key={item.id} className={item.enabled ? '' : 'disabled-row'}><td><code>{item.tagId}</code></td><td><b>{item.name}</b></td><td>{item.category}</td><td><span className="destination-badge">{item.destination}</span></td><td><button aria-label={`${item.name} ${item.enabled ? '사용 중지' : '사용'}`} className={`toggle ${item.enabled ? 'on' : ''}`} onClick={() => toggleItem(item.id)}><i /></button><small className="toggle-label">{item.enabled ? '사용' : '미사용'}</small></td><td><div className="row-actions"><button onClick={() => setEditing(item)}>수정</button><button className="delete" onClick={() => deleteItem(item.id)}>삭제</button></div></td></tr>)}</tbody></table></section>
    {editing && <Modal title={editing === 'new' ? '새 물품 추가' : '물품 정보 수정'} onClose={() => setEditing(null)}><form className="item-form" onSubmit={handleSubmit}><label><span>태그 ID</span><input name="tagId" required defaultValue={editing === 'new' ? `TAG-${String(items.length + 1).padStart(3, '0')}` : editing.tagId} /></label><label><span>물품명</span><input name="name" required defaultValue={editing === 'new' ? '' : editing.name} placeholder="예: 안경" /></label><div className="form-row"><label><span>분류</span><select name="category" defaultValue={editing === 'new' ? categories[0] : editing.category}>{categories.map((value) => <option key={value}>{value}</option>)}</select></label><label><span>기본 목적지</span><select name="destination" defaultValue={editing === 'new' ? destinations[0] : editing.destination}>{destinations.map((value) => <option key={value}>{value}</option>)}</select></label></div><label className="check-row"><input type="checkbox" name="enabled" defaultChecked={editing === 'new' || editing.enabled} /> 작업 계획에서 이 물품 사용</label><footer><button type="button" className="secondary outline" onClick={() => setEditing(null)}>취소</button><button className="primary" type="submit">저장</button></footer></form></Modal>}
  </>;
}
