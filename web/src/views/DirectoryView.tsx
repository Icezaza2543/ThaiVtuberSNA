import React, { useState, useMemo } from 'react'
import type { RegistryData } from '../types'
import { CreatorMonogram } from '../components/CreatorMonogram'
import {
  PlatformIcon,
  SearchIcon,
  CloseIcon,
  VerifiedBadgeIcon,
} from '../components/Icons'
import {
  FORMAT_LABELS,
  ROLE_LABELS,
  THAI_RELATION_LABELS,
  PLATFORM_CONFIG,
} from '../utils/formatters'

interface DirectoryViewProps {
  data: RegistryData
  onSelectCreator: (creatorId: string) => void
}

export const DirectoryView: React.FC<DirectoryViewProps> = ({
  data,
  onSelectCreator,
}) => {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null)
  const [selectedRole, setSelectedRole] = useState<string | null>(null)
  const [selectedFormat, setSelectedFormat] = useState<string | null>(null)
  const [selectedRelation, setSelectedRelation] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<'name' | 'platforms' | 'accounts'>('name')

  // Available platforms in published dataset
  const availablePlatforms = useMemo(() => {
    return Object.keys(data.published.accounts_by_platform).sort((a, b) => {
      return (data.published.accounts_by_platform[b] || 0) - (data.published.accounts_by_platform[a] || 0)
    })
  }, [data])

  // Count active filters
  const hasActiveFilters = Boolean(
    searchQuery.trim() || selectedPlatform || selectedRole || selectedFormat || selectedRelation
  )

  const clearAllFilters = () => {
    setSearchQuery('')
    setSelectedPlatform(null)
    setSelectedRole(null)
    setSelectedFormat(null)
    setSelectedRelation(null)
  }

  // Filter and sort creators
  const filteredCreators = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()

    return data.creators
      .filter((creator) => {
        // Search filter
        if (query) {
          const cleanQuery = query.startsWith('@') ? query.slice(1) : query
          const matchName = creator.name.toLowerCase().includes(query) || (cleanQuery && creator.name.toLowerCase().includes(cleanQuery))
          const matchHandle = creator.accounts.some((a) => {
            const h = (a.handle || '').toLowerCase()
            const an = (a.name || '').toLowerCase()
            const pid = (a.platform_id || '').toLowerCase()
            return (
              (h && (h.includes(query) || (cleanQuery && h.includes(cleanQuery)))) ||
              (an && (an.includes(query) || (cleanQuery && an.includes(cleanQuery)))) ||
              (pid && (pid.includes(query) || (cleanQuery && pid.includes(cleanQuery))))
            )
          })
          if (!matchName && !matchHandle) return false
        }

        // Platform filter
        if (selectedPlatform) {
          if (!creator.platforms.includes(selectedPlatform)) return false
        }

        // Role filter
        if (selectedRole) {
          if (!creator.roles.includes(selectedRole)) return false
        }

        // Format filter
        if (selectedFormat) {
          if (creator.format !== selectedFormat) return false
        }

        // Thai relation filter
        if (selectedRelation) {
          if (creator.thai_relation !== selectedRelation) return false
        }

        return true
      })
      .sort((a, b) => {
        if (sortBy === 'platforms') {
          return b.platforms.length - a.platforms.length || a.name.localeCompare(b.name, 'th')
        }
        if (sortBy === 'accounts') {
          return b.accounts.length - a.accounts.length || a.name.localeCompare(b.name, 'th')
        }
        return a.name.localeCompare(b.name, 'th')
      })
  }, [
    data.creators,
    searchQuery,
    selectedPlatform,
    selectedRole,
    selectedFormat,
    selectedRelation,
    sortBy,
  ])

  return (
    <div>
      {/* Editorial Hero Banner */}
      <section className="hero-editorial">
        <div className="container">
          <div className="hero-subtitle">Directory of Thai Virtual Personas</div>
          <h1 className="hero-title">ทำเนียบบุคคลสาธารณะเสมือนจริงของไทย</h1>
          <p className="hero-desc">
            รวบรวมและตรวจสอบข้อมูลครีเอเตอร์เสมือนไทย (VTubers / VSingers / Virtual Creators)
            ผ่านหลักฐานปฐมภูมิที่เปิดเผยต่อสาธารณะ เพื่อสร้างสารบบที่ถูกต้อง โปร่งใส และค้นหาได้จริง
          </p>

          <div className="hero-meta-strip">
            <div className="meta-pill">
              <span>ครีเอเตอร์ที่ยืนยันแล้ว:</span>
              <strong>{data.published.personas.toLocaleString()}</strong>
            </div>
            <div className="meta-pill">
              <span>บัญชีแพลตฟอร์มที่เชื่อมโยง:</span>
              <strong>{data.published.accounts.toLocaleString()}</strong>
            </div>
            <div className="meta-pill">
              <span>คู่ความสัมพันธ์ที่มีหลักฐาน:</span>
              <strong>{data.published.persona_account_pairs.toLocaleString()}</strong>
            </div>
            <div className="meta-pill">
              <span>สถานะการตรวจสอบ:</span>
              <strong style={{ color: 'var(--success)' }}>ผ่านการตรวจสอบ 100%</strong>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content Area */}
      <div className="container" style={{ paddingTop: '2rem' }}>
        {/* Filter Bar */}
        <div className="filter-bar" role="search" aria-label="ค้นหาและกรองครีเอเตอร์">
          <div className="search-input-wrapper">
            <span className="search-icon-left" aria-hidden="true">
              <SearchIcon size={20} />
            </span>
            <input
              type="text"
              className="search-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="ค้นหาด้วยชื่อครีเอเตอร์, ช่อง, หรือ @handle..."
              aria-label="ค้นหาด้วยชื่อหรือ handle"
            />
            {searchQuery && (
              <button
                type="button"
                className="clear-search-btn"
                onClick={() => setSearchQuery('')}
                aria-label="ล้างคำค้นหา"
              >
                <CloseIcon size={18} />
              </button>
            )}
          </div>

          <div className="filter-groups-wrap">
            {/* Platform filter */}
            <div className="filter-row">
              <span className="filter-row-label">แพลตฟอร์ม:</span>
              <div className="filter-chips">
                <button
                  type="button"
                  className={`chip-btn ${selectedPlatform === null ? 'active' : ''}`}
                  onClick={() => setSelectedPlatform(null)}
                >
                  ทั้งหมด
                </button>
                {availablePlatforms.map((plt) => {
                  const count = data.published.accounts_by_platform[plt] || 0
                  const cfg = PLATFORM_CONFIG[plt] || { name: plt }
                  return (
                    <button
                      key={plt}
                      type="button"
                      className={`chip-btn ${selectedPlatform === plt ? 'active' : ''}`}
                      onClick={() => setSelectedPlatform(selectedPlatform === plt ? null : plt)}
                    >
                      <PlatformIcon platform={plt} size={14} />
                      <span>{cfg.name}</span>
                      <span className="chip-count">({count})</span>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Role filter */}
            <div className="filter-row">
              <span className="filter-row-label">บทบาท:</span>
              <div className="filter-chips">
                <button
                  type="button"
                  className={`chip-btn ${selectedRole === null ? 'active' : ''}`}
                  onClick={() => setSelectedRole(null)}
                >
                  ทุกบทบาท
                </button>
                {Object.entries(ROLE_LABELS).map(([roleKey, label]) => (
                  <button
                    key={roleKey}
                    type="button"
                    className={`chip-btn ${selectedRole === roleKey ? 'active' : ''}`}
                    onClick={() => setSelectedRole(selectedRole === roleKey ? null : roleKey)}
                  >
                    <span>{label.th}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Model format filter */}
            <div className="filter-row">
              <span className="filter-row-label">รูปแบบโมเดล:</span>
              <div className="filter-chips">
                <button
                  type="button"
                  className={`chip-btn ${selectedFormat === null ? 'active' : ''}`}
                  onClick={() => setSelectedFormat(null)}
                >
                  ทุกรูปแบบ
                </button>
                {Object.entries(FORMAT_LABELS).map(([fmtKey, label]) => (
                  <button
                    key={fmtKey}
                    type="button"
                    className={`chip-btn ${selectedFormat === fmtKey ? 'active' : ''}`}
                    onClick={() => setSelectedFormat(selectedFormat === fmtKey ? null : fmtKey)}
                  >
                    <span>{label.th}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Thai relation filter */}
            <div className="filter-row">
              <span className="filter-row-label">เกณฑ์ระบุไทย:</span>
              <div className="filter-chips">
                <button
                  type="button"
                  className={`chip-btn ${selectedRelation === null ? 'active' : ''}`}
                  onClick={() => setSelectedRelation(null)}
                >
                  ทุกเกณฑ์
                </button>
                {Object.entries(THAI_RELATION_LABELS).map(([relKey, label]) => (
                  <button
                    key={relKey}
                    type="button"
                    className={`chip-btn ${selectedRelation === relKey ? 'active' : ''}`}
                    onClick={() => setSelectedRelation(selectedRelation === relKey ? null : relKey)}
                  >
                    <span>{label.th}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Results Header Bar */}
        <div className="results-header-bar">
          <div className="results-count-text">
            แสดง <strong>{filteredCreators.length.toLocaleString()}</strong> จากทั้งหมด{' '}
            <strong>{data.published.personas.toLocaleString()}</strong> ครีเอเตอร์ที่ผ่านการตรวจสอบ
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            {hasActiveFilters && (
              <button
                type="button"
                className="reset-filters-btn"
                onClick={clearAllFilters}
              >
                ล้างตัวกรองทั้งหมด
              </button>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.86rem' }}>
              <span style={{ color: 'var(--muted-ink)' }}>เรียงตาม:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                style={{
                  padding: '0.35rem 0.6rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--surface)',
                  fontFamily: 'var(--font-thai)',
                  fontSize: '0.86rem',
                  color: 'var(--forest)',
                  cursor: 'pointer',
                }}
              >
                <option value="name">ชื่อ (ก-ฮ / A-Z)</option>
                <option value="platforms">จำนวนแพลตฟอร์มมากสุด</option>
                <option value="accounts">จำนวนบัญชีเชื่อมโยงมากสุด</option>
              </select>
            </div>
          </div>
        </div>

        {/* Results Grid or Empty State */}
        {filteredCreators.length === 0 ? (
          <div className="state-box">
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '0.5rem' }}>
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="var(--muted-ink)" strokeWidth="1.5">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
                <line x1="8" y1="11" x2="14" y2="11" />
              </svg>
            </div>
            <h2 className="state-title">ไม่พบครีเอเตอร์ที่ตรงกับเงื่อนไข</h2>
            <p className="state-desc">
              ลองเปลี่ยนคำค้นหา หรือปรับตัวกรองแพลตฟอร์ม บทบาท และรูปแบบโมเดลใหม่
            </p>
            <button
              type="button"
              className="chip-btn active"
              onClick={clearAllFilters}
              style={{ margin: '0 auto' }}
            >
              ล้างตัวกรองทั้งหมด
            </button>
          </div>
        ) : (
          <div className="creators-grid">
            {filteredCreators.map((creator) => {
              const formatInfo = FORMAT_LABELS[creator.format] || { th: creator.format }
              const relationInfo = THAI_RELATION_LABELS[creator.thai_relation]

              return (
                <div
                  key={creator.id}
                  className="creator-card"
                  onClick={() => onSelectCreator(creator.id)}
                  style={{ cursor: 'pointer' }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      onSelectCreator(creator.id)
                    }
                  }}
                  aria-label={`ดูข้อมูลของ ${creator.name}`}
                >
                  <div>
                    <div className="creator-card-top">
                      <CreatorMonogram name={creator.name} size="md" />
                      <div className="creator-meta-block">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <h2 className="creator-name">{creator.name}</h2>
                          <span title="ผ่านการตรวจสอบหลักฐานยืนยันตัวตนแล้ว">
                            <VerifiedBadgeIcon size={16} />
                          </span>
                        </div>

                        <div className="creator-roles-row">
                          {creator.roles.map((r) => (
                            <span key={r} className="badge-tag">
                              {ROLE_LABELS[r]?.th || r}
                            </span>
                          ))}
                          <span className="badge-tag badge-format">
                            {formatInfo.th}
                          </span>
                        </div>
                      </div>
                    </div>

                    {relationInfo && (
                      <div style={{ fontSize: '0.8rem', color: 'var(--muted-ink)', marginTop: '0.35rem' }}>
                        {relationInfo.th}
                      </div>
                    )}
                  </div>

                  {/* Platforms Row */}
                  <div className="creator-platforms-row">
                    <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', flex: 1 }}>
                      {creator.platforms.length > 0 ? (
                        creator.platforms.map((plt) => (
                          <span
                            key={plt}
                            className="platform-pill"
                            title={PLATFORM_CONFIG[plt]?.name || plt}
                          >
                            <PlatformIcon platform={plt} size={15} />
                          </span>
                        ))
                      ) : (
                        <span style={{ fontSize: '0.78rem', color: 'var(--muted-ink)', fontStyle: 'italic' }}>
                          รอตรวจสอบ ownership บัญชี
                        </span>
                      )}
                    </div>
                    <span style={{ fontSize: '0.8rem', color: 'var(--muted-ink)', fontFamily: 'var(--font-sans)' }}>
                      {creator.accounts.length > 0 ? `${creator.accounts.length} บัญชี` : 'ยังไม่มีบัญชีที่ยืนยัน'}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
