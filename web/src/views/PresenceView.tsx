import React from 'react'
import type { RegistryData } from '../types'
import { PlatformIcon } from '../components/Icons'
import { PLATFORM_CONFIG } from '../utils/formatters'

interface PresenceViewProps {
  data: RegistryData
}

export const PresenceView: React.FC<PresenceViewProps> = ({ data }) => {
  const publishedPlatforms = data.published.accounts_by_platform
  const inventoryPlatforms = data.inventory.accounts_by_platform

  const allPlatformKeys = Array.from(
    new Set([...Object.keys(publishedPlatforms), ...Object.keys(inventoryPlatforms)])
  ).sort((a, b) => (publishedPlatforms[b] || 0) - (publishedPlatforms[a] || 0))

  return (
    <div className="container" style={{ padding: '2.5rem 1.5rem 4rem' }}>
      <div style={{ maxWidth: '840px', marginBottom: '2.5rem' }}>
        <div className="hero-subtitle">Platform Presence Architecture</div>
        <h1 className="hero-title">ภาพรวมการปรากฏตัวบนแพลตฟอร์ม</h1>
        <p className="hero-desc">
          การวิเคราะห์การกระจายตัวของบัญชีครีเอเตอร์เสมือนไทยข้ามแพลตฟอร์ม
          แยกความแตกต่างอย่างชัดเจนระหว่าง <strong>คลังข้อมูลทั้งหมด (Inventory)</strong>{' '}
          และ <strong>ข้อมูลที่ผ่านการตรวจสอบยืนยันสิทธิแล้ว (Published)</strong>
        </p>
      </div>

      {/* Distinction Banner */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1.25rem',
          marginBottom: '2.5rem',
        }}
      >
        <div
          style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            padding: '1.5rem',
            borderTop: '4px solid var(--forest)',
          }}
        >
          <div style={{ fontSize: '0.86rem', color: 'var(--muted-ink)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            คลังข้อมูลทั้งหมด (Catalog Inventory)
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--forest)', margin: '0.4rem 0' }}>
            {data.inventory.accounts.toLocaleString()}{' '}
            <span style={{ fontSize: '1rem', fontWeight: 400 }}>บัญชี</span>
          </div>
          <p style={{ fontSize: '0.88rem', color: 'var(--muted-ink)', lineHeight: '1.5' }}>
            ประกอบด้วย {data.inventory.personas.toLocaleString()} ตัวตนในระบบ ทั้งที่ผ่านการตรวจสอบแล้วและรายการที่ยังอยู่ในกระบวนการรอหลักฐาน (needs evidence)
          </p>
        </div>

        <div
          style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            padding: '1.5rem',
            borderTop: '4px solid var(--gold)',
          }}
        >
          <div style={{ fontSize: '0.86rem', color: 'var(--gold)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            เผยแพร่สู่สาธารณะ (Published & Verified)
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--forest)', margin: '0.4rem 0' }}>
            {data.published.accounts.toLocaleString()}{' '}
            <span style={{ fontSize: '1rem', fontWeight: 400 }}>บัญชี</span>
          </div>
          <p style={{ fontSize: '0.88rem', color: 'var(--muted-ink)', lineHeight: '1.5' }}>
            เชื่อมโยงกับ {data.published.personas.toLocaleString()} ครีเอเตอร์เสมือนไทยที่ผ่านการตรวจสอบหลักฐานปฐมภูมิครบถ้วน รวม {data.published.persona_account_pairs.toLocaleString()} คู่ความสัมพันธ์
          </p>
        </div>
      </div>

      {/* Presence Table */}
      <section className="editorial-prose-card">
        <h2>สถิติบัญชีรายแพลตฟอร์ม</h2>
        <p>
          ตารางแสดงจำนวนบัญชีที่บันทึกไว้ในแต่ละแพลตฟอร์ม เปรียบเทียบระหว่างบัญชีที่ยืนยันสิทธิเผยแพร่แล้วกับคลังข้อมูลทั้งหมด
          ตัวเลขเหล่านี้แสดงถึงการกระจายตัวของช่องทางสื่อสาร ไม่ใช่สัดส่วนผู้ติดตามหรือความนิยม
        </p>

        <div style={{ overflowX: 'auto' }}>
          <table className="stats-table">
            <thead>
              <tr>
                <th>แพลตฟอร์ม</th>
                <th className="num">ยืนยันและเผยแพร่ (Published)</th>
                <th className="num">คลังข้อมูลรวม (Inventory)</th>
                <th className="num">สัดส่วนที่ยืนยันแล้ว</th>
              </tr>
            </thead>
            <tbody>
              {allPlatformKeys.map((plt) => {
                const pub = publishedPlatforms[plt] || 0
                const inv = inventoryPlatforms[plt] || 0
                const pct = inv > 0 ? ((pub / inv) * 100).toFixed(1) : '0.0'
                const cfg = PLATFORM_CONFIG[plt] || { name: plt }

                return (
                  <tr key={plt}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                        <span className="platform-pill" style={{ width: 24, height: 24 }}>
                          <PlatformIcon platform={plt} size={14} />
                        </span>
                        <strong style={{ color: 'var(--forest)' }}>{cfg.name}</strong>
                      </div>
                    </td>
                    <td className="num" style={{ fontWeight: 600, color: 'var(--forest)' }}>
                      {pub.toLocaleString()}
                    </td>
                    <td className="num" style={{ color: 'var(--muted-ink)' }}>
                      {inv.toLocaleString()}
                    </td>
                    <td className="num">
                      <span
                        style={{
                          display: 'inline-block',
                          padding: '0.15rem 0.45rem',
                          borderRadius: '4px',
                          backgroundColor: Number(pct) >= 70 ? 'var(--success-bg)' : 'var(--surface-muted)',
                          color: Number(pct) >= 70 ? 'var(--success)' : 'var(--forest)',
                          fontSize: '0.82rem',
                          fontWeight: 600,
                        }}
                      >
                        {pct}%
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Methodological Caveats on Presence */}
      <section className="editorial-prose-card">
        <h2>หลักการตีความข้อมูลการปรากฏตัว (Presence Principles)</h2>
        <ul>
          <li>
            <strong>การปรากฏตัวหมายถึงการมีช่องทาง ไม่ใช่กลุ่มผู้ชมร่วม:</strong> การที่ครีเอเตอร์มีทั้งช่อง YouTube และ TikTok หมายความว่าครีเอเตอร์ใช้สองแพลตฟอร์มนี้ในการเผยแพร่เนื้อหา ไม่ได้หมายความว่าผู้ชมของสองแพลตฟอร์มเป็นกลุ่มเดียวกัน (No audience overlap inference)
          </li>
          <li>
            <strong>ไม่บังคับจำนวนแพลตฟอร์ม — บัญชีช่องทางเดียวผ่านได้:</strong>{' '}
            การมีเพียง Twitch / TikTok / X / YouTube ช่องเดียวไม่ลดระดับความน่าเชื่อถือของครีเอเตอร์
            หากหลักฐาน persona และ ownership ผ่านการ review ครีเอเตอร์นั้นก็ถือเป็นส่วนหนึ่งของสารบบ
            YouTube ไม่ใช่ข้อบังคับ การมีหลายแพลตฟอร์มไม่ใช่เกณฑ์ตัดสิน
          </li>
          <li>
            <strong>การไม่พบข้อมูลไม่ได้แปลว่าไม่มีอยู่จริง (Missing is not absence):</strong> หากครีเอเตอร์ไม่มีบัญชีบนแพลตฟอร์มใดในสารบบ หมายถึง "ยังไม่พบหลักฐานเชื่อมโยงขั้นปฐมภูมิที่ยืนยันได้" ไม่ได้เป็นข้อพิสูจน์ว่าบุคคลนั้นไม่ได้ใช้งานแพลตฟอร์มดังกล่าว
          </li>
          <li>
            <strong>ความคงที่ของรหัส (Stable Identifiers):</strong> บัญชีทั้งหมดถูกจัดเก็บด้วยรหัสประจำตัวทางเทคนิคที่ถาวร (เช่น YouTube Channel ID ที่ขึ้นต้นด้วย UC, TikTok Web User ID, Twitch Numeric ID) เพื่อป้องกันความคลาดเคลื่อนจากการเปลี่ยนชื่อหรือ handle ในอนาคต
          </li>
        </ul>
      </section>
    </div>
  )
}
