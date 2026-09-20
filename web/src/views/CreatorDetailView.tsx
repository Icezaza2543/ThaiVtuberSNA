import React, { useEffect } from 'react'
import type { Creator } from '../types'
import { CreatorMonogram } from '../components/CreatorMonogram'
import {
  PlatformIcon,
  ArrowLeftIcon,
  ExternalLinkIcon,
  VerifiedBadgeIcon,
  InfoIcon,
} from '../components/Icons'
import {
  FORMAT_LABELS,
  ROLE_LABELS,
  THAI_RELATION_LABELS,
  PLATFORM_CONFIG,
  formatDate,
} from '../utils/formatters'

interface CreatorDetailViewProps {
  creator: Creator
  onBack: () => void
}

export const CreatorDetailView: React.FC<CreatorDetailViewProps> = ({
  creator,
  onBack,
}) => {
  // Scroll to top on mount
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [creator.id])

  const formatInfo = FORMAT_LABELS[creator.format] || { th: creator.format, en: creator.format }
  const relationInfo = THAI_RELATION_LABELS[creator.thai_relation] || {
    th: creator.thai_relation,
    desc: 'ข้อมูลความสัมพันธ์กับคอมมูนิตี้ไทย',
  }

  return (
    <div className="container detail-container">
      {/* Breadcrumb / Back button */}
      <button
        type="button"
        className="back-link"
        onClick={onBack}
        aria-label="กลับสู่ทำเนียบครีเอเตอร์"
      >
        <ArrowLeftIcon size={16} />
        <span>กลับสู่ทำเนียบครีเอเตอร์</span>
      </button>

      {/* Hero Panel */}
      <section className="creator-hero-panel" aria-label="ข้อมูลครีเอเตอร์">
        <CreatorMonogram name={creator.name} size="xl" />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <h1 className="detail-headline">{creator.name}</h1>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                backgroundColor: 'var(--forest)',
                color: 'var(--gold-soft)',
                padding: '0.2rem 0.55rem',
                borderRadius: '4px',
                fontSize: '0.82rem',
                fontWeight: 600,
              }}
            >
              <VerifiedBadgeIcon size={14} />
              <span>ยืนยันหลักฐานแล้ว</span>
            </div>
          </div>

          <div className="detail-badges-row" style={{ marginTop: '0.6rem' }}>
            <span className="badge-tag badge-format" style={{ fontSize: '0.85rem' }}>
              รูปแบบโมเดล: {formatInfo.th}
            </span>
            {creator.roles.map((r) => (
              <span key={r} className="badge-tag" style={{ fontSize: '0.85rem' }}>
                {ROLE_LABELS[r]?.th || r}
              </span>
            ))}
          </div>

          <div className="detail-desc-box">
            <strong>ความสัมพันธ์กับไทย:</strong> {relationInfo.th} — {relationInfo.desc}
          </div>

          {/* Evidence proofs for the persona itself */}
          {creator.sources.length > 0 && (
            <div style={{ marginTop: '0.9rem', fontSize: '0.82rem', color: 'var(--muted-ink)' }}>
              <span>หลักฐานยืนยันตัวตนสาธารณะ: </span>
              {creator.sources.map((s, idx) => (
                <span key={idx}>
                  {s.url ? (
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="evidence-source-link"
                    >
                      หลักฐานลำดับที่ {idx + 1}
                    </a>
                  ) : (
                    <span>บันทึกหลักฐาน</span>
                  )}
                  {s.observed_at && (
                    <span> (บันทึกเมื่อ {formatDate(s.observed_at)})</span>
                  )}
                  {idx < creator.sources.length - 1 && ', '}
                </span>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Notice Banner */}
      <div
        style={{
          display: 'flex',
          gap: '0.75rem',
          alignItems: 'flex-start',
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)',
          padding: '1rem 1.25rem',
          marginBottom: '2rem',
          fontSize: '0.88rem',
          color: 'var(--muted-ink)',
          lineHeight: '1.6',
        }}
      >
        <span style={{ color: 'var(--gold)', marginTop: '2px' }} aria-hidden="true">
          <InfoIcon size={18} />
        </span>
        <div>
          <strong>หลักความน่าเชื่อถือของสารบบ:</strong> การยืนยันตัวตนเสมือน (Verified Persona) ไม่ได้หมายความว่าทุกบัญชีที่ค้นพบในอินเทอร์เน็ตได้รับการยืนยันแล้ว
          และแพลตฟอร์มที่ไม่มีในหน้านี้ไม่ได้แปลว่าครีเอเตอร์ไม่ได้ใช้งาน (Missing platform is unknown, not absent)
          ระบบแสดงเฉพาะบัญชีที่มีหลักฐานยืนยันสิทธิการเป็นเจ้าของ (ownership) ขั้นปฐมภูมิ และเก็บเฉพาะรหัสคงที่ (Stable IDs) เพื่อความโปร่งใส
        </div>
      </div>

      {/* Accounts & Channels Section */}
      <section aria-labelledby="accounts-section-heading">
        <h2
          id="accounts-section-heading"
          style={{
            fontSize: '1.4rem',
            fontWeight: 700,
            color: 'var(--forest)',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <span>บัญชีและช่องทางทางการที่ผ่านการตรวจสอบ</span>
          <span
            style={{
              fontFamily: 'var(--font-sans)',
              fontSize: '0.88rem',
              color: 'var(--muted-ink)',
              fontWeight: 400,
            }}
          >
            ({creator.accounts.length} บัญชี)
          </span>
        </h2>

        {creator.accounts.length === 0 ? (
          <div
            style={{
              backgroundColor: 'var(--surface)',
              border: '1px dashed var(--border)',
              borderRadius: 'var(--radius-md)',
              padding: '2rem 1.5rem',
              textAlign: 'center',
              color: 'var(--muted-ink)',
              fontSize: '0.95rem',
              lineHeight: '1.6',
            }}
          >
            <div style={{ color: 'var(--forest)', fontWeight: 600, marginBottom: '0.5rem', fontSize: '1.05rem' }}>
              บัญชีสาธารณะที่เชื่อมโยงกับตัวตนนี้ยังไม่มีรายการที่ผ่านการตรวจสอบ ownership
            </div>
            <p style={{ margin: 0, fontSize: '0.88rem', maxWidth: '640px', marginLeft: 'auto', marginRight: 'auto' }}>
              ตัวตนนี้ได้รับการยืนยันว่าเป็นครีเอเตอร์เสมือนที่มีความสัมพันธ์กับไทย (Verified Persona)
              แต่ลิงก์บัญชีแพลตฟอร์มยังอยู่ในระหว่างการตรวจสอบหลักฐานปฐมภูมิ
              สารบบจะไม่แสดงบัญชีที่ยังไม่มีหลักฐานยืนยันสิทธิการเป็นเจ้าของที่ชัดเจน
            </p>
          </div>
        ) : (
          <div className="accounts-grid">
          {creator.accounts.map((account) => {
            const platformCfg = PLATFORM_CONFIG[account.platform] || {
              name: account.platform,
              brandColor: '#1A221F',
            }

            return (
              <div key={account.id} className="account-card">
                <div>
                  <div className="account-header">
                    <div className="account-platform-label">
                      <PlatformIcon platform={account.platform} size={18} />
                      <span>{platformCfg.name}</span>
                    </div>

                    <a
                      href={account.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="account-link-btn"
                    >
                      <span>เปิดโปรไฟล์</span>
                      <ExternalLinkIcon size={12} />
                    </a>
                  </div>

                  <div className="account-body">
                    <div className="account-display-name">
                      {account.name || creator.name}
                    </div>
                    {account.handle && (
                      <div className="account-handle">
                        {account.handle.startsWith('@') ? account.handle : `@${account.handle}`}
                      </div>
                    )}
                    <div className="account-stable-id" title={`Namespace: ${account.id_namespace}`}>
                      ID: {account.platform_id} ({account.id_namespace})
                    </div>
                  </div>
                </div>

                {/* Evidence timeline */}
                {account.ownership_evidence.length > 0 && (
                  <div className="account-evidence-block">
                    <div style={{ fontWeight: 600, color: 'var(--forest)', marginBottom: '0.25rem' }}>
                      ประวัติการตรวจยืนยันสิทธิ:
                    </div>
                    {account.ownership_evidence.map((ev, evIdx) => (
                      <div key={evIdx} style={{ fontSize: '0.78rem', lineHeight: '1.5' }}>
                        <span>
                          {ev.valid_from ? `ช่วงเวลา: ${ev.valid_from}` : 'บันทึกยืนยัน'}
                          {ev.valid_to ? ` ถึง ${ev.valid_to}` : ' เป็นต้นมา'}
                        </span>
                        {ev.source?.url && (
                          <div>
                            <a
                              href={ev.source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="evidence-source-link"
                            >
                              ตรวจหลักฐานอ้างอิง
                            </a>
                            {ev.source.observed_at && (
                              <span> ({formatDate(ev.source.observed_at)})</span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
        )}
      </section>

      {/* Affiliations & Organizations Section */}
      {creator.affiliations.length > 0 && (
        <section className="timeline-card" style={{ marginTop: '2rem' }}>
          <h2
            style={{
              fontSize: '1.25rem',
              fontWeight: 700,
              color: 'var(--forest)',
              marginBottom: '1rem',
            }}
          >
            สังกัดและองค์กรที่ผ่านการตรวจสอบ
          </h2>
          <div className="timeline-list">
            {creator.affiliations.map((aff, idx) => (
              <div key={idx} className="timeline-item">
                <div className="timeline-dot" />
                <div className="timeline-title">{aff.organization}</div>
                <div className="timeline-date">
                  {aff.valid_from ? `ตั้งแต่ ${aff.valid_from}` : 'มีผล'}
                  {aff.valid_to ? ` ถึง ${aff.valid_to}` : ' เป็นต้นมา'}
                </div>
                {aff.source?.url && (
                  <div style={{ fontSize: '0.8rem', marginTop: '0.2rem' }}>
                    <a
                      href={aff.source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="evidence-source-link"
                    >
                      หลักฐานการสังกัด
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Lifecycle Events Section */}
      {creator.events.length > 0 && (
        <section className="timeline-card" style={{ marginTop: '2rem' }}>
          <h2
            style={{
              fontSize: '1.25rem',
              fontWeight: 700,
              color: 'var(--forest)',
              marginBottom: '1rem',
            }}
          >
            ประวัติและหมุดหมายสำคัญ (Lifecycle Events)
          </h2>
          <div className="timeline-list">
            {creator.events.map((ev, idx) => (
              <div key={idx} className="timeline-item">
                <div className="timeline-dot" />
                <div className="timeline-title">
                  {ev.event_type === 'graduation'
                    ? 'ยุติกิจกรรม / จบการศึกษา (Graduation)'
                    : ev.event_type === 'debut'
                    ? 'เปิดตัวอย่างเป็นทางการ (Debut)'
                    : ev.event_type === 'hiatus'
                    ? 'พักกิจกรรมชั่วคราว (Hiatus)'
                    : ev.event_type}
                </div>
                <div className="timeline-date">
                  วันที่: {ev.event_date || 'ไม่ระบุวันที่แน่ชัด'}
                  {ev.date_precision && ` (ความละเอียดระดับ ${ev.date_precision})`}
                </div>
                {ev.source?.url && (
                  <div style={{ fontSize: '0.8rem', marginTop: '0.2rem' }}>
                    <a
                      href={ev.source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="evidence-source-link"
                    >
                      หลักฐานประกาศทางการ
                    </a>
                    {ev.source.observed_at && (
                      <span> (บันทึกเมื่อ {formatDate(ev.source.observed_at)})</span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
