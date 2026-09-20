import React from 'react'
import type { RegistryData } from '../types'
import { formatDate } from '../utils/formatters'

interface MethodologyViewProps {
  data: RegistryData
}

export const MethodologyView: React.FC<MethodologyViewProps> = ({ data }) => {
  return (
    <div className="container" style={{ padding: '2.5rem 1.5rem 4rem' }}>
      <div style={{ maxWidth: '840px', marginBottom: '2.5rem' }}>
        <div className="hero-subtitle">Standards, Provenance & Limitations</div>
        <h1 className="hero-title">ระเบียบวิธีจัดทำข้อมูลและข้อจำกัด</h1>
        <p className="hero-desc">
          หลักเกณฑ์การคัดเลือก กระบวนการตรวจสอบหลักฐานปฐมภูมิ และข้อพึงระวังในการใช้งานสารบบครีเอเตอร์เสมือนไทย
        </p>
      </div>

      <div style={{ maxWidth: '880px' }}>
        {/* Section 1: Nature of the registry */}
        <section className="editorial-prose-card">
          <h2>1. ขอบเขตและลักษณะของสารบบ</h2>
          <p>
            สารบบนี้จัดทำขึ้นในฐานะ <strong>ทำเนียบบุคคลสาธารณะเสมือน (Public-Persona Registry)</strong>{' '}
            ไม่ได้มีเป้าหมายเพื่อการสำรวจสำมะโนประชากรส่วนบุคคล (Census of Private People)
            หรือการสืบหาตัวตนเบื้องหลัง (Doxxing / Real Identity Inference)
          </p>
          <p>
            ข้อมูลที่รวบรวมมุ่งเน้นไปที่บทบาท ผลงาน และช่องทางการสื่อสารที่ตัวตนเสมือนนั้นเผยแพร่สู่สาธารณะด้วยตนเอง
            โดยไม่มีการคาดเดาความสัมพันธ์ส่วนตัว การเชื่อมโยงคนต่างตัวตนที่มีชื่อคล้ายกัน หรือการนำข้อมูลส่วนบุคคลที่ไม่ได้เปิดเผยมาจัดเก็บ
          </p>
        </section>

        {/* Section 2: Platform-Independent Verification */}
        <section className="editorial-prose-card">
          <h2>2. การยืนยันตัวตนไม่ขึ้นกับแพลตฟอร์ม (Platform-Independent Verification)</h2>
          <p>
            <strong>ครีเอเตอร์สามารถผ่านการ Verify ได้แม้มีบัญชีเพียงแพลตฟอร์มเดียว</strong>
          </p>
          <p>
            สารบบนี้ไม่กำหนดว่าครีเอเตอร์ต้องมี YouTube หรือต้องมีหลายแพลตฟอร์ม
            สิ่งที่ตรวจสอบคือ:
          </p>
          <ul>
            <li>
              <strong>Virtual Presentation:</strong>{' '}
              มีการนำเสนอตัวตนด้วยภาพแทนเสมือน (2D / 3D / PNGTuber / avatar) บนช่องทางสาธารณะ
            </li>
            <li>
              <strong>Thai Relation:</strong>{' '}
              มีความสัมพันธ์กับชุมชนไทย เช่น ใช้ภาษาไทย ระบุตนเองเป็นครีเอเตอร์ไทย มีสังกัดไทย หรืออยู่ในชุมชนไทย
            </li>
            <li>
              <strong>Public Account Ownership:</strong>{' '}
              มีหลักฐานปฐมภูมิยืนยันว่าบัญชีสาธารณะที่ระบุเป็นของบุคคลนี้จริง
            </li>
            <li>
              <strong>Human Review:</strong>{' '}
              ผ่านการตรวจสอบโดยบุคคลที่รับผิดชอบโครงการ
            </li>
          </ul>
          <p style={{ marginTop: '1rem', padding: '0.85rem 1rem', background: 'var(--surface-muted)', borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--forest)' }}>
            <strong>ตัวอย่างที่ผ่าน Verify:</strong>{' '}
            ครีเอเตอร์ที่มีเฉพาะ Twitch · ครีเอเตอร์ที่มีเฉพาะ TikTok ·
            ครีเอเตอร์ที่มีเฉพาะ X · ครีเอเตอร์ที่มีเฉพาะ YouTube
            — ทั้งหมดนี้สามารถผ่านเกณฑ์ได้ หากมีหลักฐานครบ 4 ข้อข้างต้น
          </p>
          <div style={{ marginTop: '1rem', padding: '1rem', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)' }}>
            <h3 style={{ fontSize: '1rem', margin: '0 0 0.5rem', color: 'var(--forest)' }}>หลักความโปร่งใสด้านแบบจำลองความน่าเชื่อถือ (Trust Model Transparency)</h3>
            <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.88rem', color: 'var(--muted-ink)', lineHeight: '1.6' }}>
              <li>
                <strong>Verified Persona ≠ All Accounts Verified:</strong> การที่ตัวตนหนึ่งผ่านการตรวจสอบ (Verified Persona) ไม่ได้หมายความว่าทุกบัญชีในอินเทอร์เน็ตที่อ้างอิงชื่อเดียวกันได้รับการยืนยันแล้ว แต่ละบัญชีต้องมีหลักฐานปฐมภูมิรองรับเฉพาะตัว
              </li>
              <li>
                <strong>Missing Platform ≠ Absence:</strong> แพลตฟอร์มที่ไม่ปรากฏในหน้านี้หมายความว่าสารบบยังไม่มีข้อมูลที่ผ่านการตรวจสอบหลักฐานปฐมภูมิ ไม่ใช่ข้อพิสูจน์ว่าครีเอเตอร์ไม่ได้ใช้งานแพลตฟอร์มนั้น
              </li>
              <li>
                <strong>Evidence Freshness ≠ Creator Inactivity:</strong> วันที่สังเกตหลักฐาน (observed_at) ที่ผ่านมานาน หมายความเพียงว่าสารบบยังไม่ได้ตรวจบันทึกหลักฐานซ้ำเมื่อเร็วๆ นี้ ไม่ใช่ข้อพิสูจน์ว่าครีเอเตอร์ยุติกิจกรรมหรือเปลี่ยนสถานะ
              </li>
            </ul>
          </div>
          <p style={{ fontSize: '0.9rem', color: 'var(--muted-ink)', marginTop: '0.75rem' }}>
            <em>จำนวนแพลตฟอร์มไม่ใช่เกณฑ์ตัดสิน การมี YouTube หรือหลายแพลตฟอร์มไม่ใช่ข้อกำหนด และไม่ใช่ข้อพิสูจน์เพียงพอในตัวเอง</em>
          </p>
        </section>

        {/* Section 3: Verification Criteria Detail */}
        <section className="editorial-prose-card">
          <h2>3. เกณฑ์การตรวจสอบและยืนยันข้อมูล (Verification Protocol)</h2>
          <p>
            ครีเอเตอร์และบัญชีที่จะได้รับการเผยแพร่ในหน้าทำเนียบสาธารณะ ต้องผ่านการตรวจสอบหลักฐานตามเกณฑ์ดังต่อไปนี้:
          </p>
          <ul>
            <li>
              <strong>การยืนยันความเป็นครีเอเตอร์เสมือนไทย (Thai Virtual Persona):</strong>{' '}
              ต้องมีหลักฐานชัดเจนว่าใช้ภาษาไทยในการสื่อสาร มีส่วนร่วมในเครือข่ายครีเอเตอร์ไทย หรือระบุตนเองเป็นครีเอเตอร์ไทย ควบคู่ไปกับการนำเสนอตัวตนด้วยภาพแทนเสมือน (2D / 3D / PNGTuber)
            </li>
            <li>
              <strong>การเชื่อมโยงบัญชีเพิ่มเติมด้วยหลักฐานปฐมภูมิ (Cross-Platform Linking):</strong>{' '}
              การผูกบัญชีเพิ่มเติมระหว่างแพลตฟอร์ม (เช่น จาก YouTube ไปยัง X หรือ TikTok){' '}
              <strong>เป็นกระบวนการยืนยันบัญชีเพิ่มเติมเท่านั้น ไม่ใช่วิธีตัดสินว่าบุคคลนั้นเป็นครีเอเตอร์เสมือนหรือไม่</strong>{' '}
              หลักฐานที่ใช้ต้องมาจากเจ้าของบัญชีระบุด้วยตนเอง เช่น ลิงก์ใน Bio ทางการ หรือหน้า Hub (Carrd, Linktree, lit.link)
              <br /><em>การมีชื่อหรือ handle คล้ายกันเพียงอย่างเดียวไม่ถือเป็นหลักฐานยืนยันความสัมพันธ์</em>
            </li>
            <li>
              <strong>การใช้รหัสคงที่ประจำแพลตฟอร์ม (Stable Identifiers):</strong>{' '}
              ระบบจัดเก็บและตรวจสอบผ่านรหัสถาวร (เช่น YouTube Channel ID ขึ้นต้นด้วย <code>UC</code>, TikTok <code>web_user_id</code> หรือ Twitch Numeric ID) บัญชีที่ยังทราบเฉพาะ Handle ชั่วคราวจะคงสถานะเป็น "รายการรอหลักฐาน (Candidate)" และจะไม่ถูกนำมาคำนวณเป็นบัญชีที่ยืนยันแล้วจนกว่าจะได้รหัสคงที่
            </li>
          </ul>
        </section>

        {/* Section 4: Data Semantics */}
        <section className="editorial-prose-card">
          <h2>4. ความหมายของตัวเลขสถิติ (Count Semantics)</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            <div style={{ background: 'var(--surface-muted)', padding: '1rem', borderRadius: 'var(--radius-sm)' }}>
              <strong>คลังข้อมูลทั้งหมด (Inventory): {data.inventory.accounts.toLocaleString()} บัญชี / {data.inventory.personas.toLocaleString()} ตัวตน</strong>
              <div style={{ fontSize: '0.9rem', color: 'var(--muted-ink)', marginTop: '0.25rem' }}>
                {data.count_semantics.inventory}
              </div>
            </div>

            <div style={{ background: 'var(--surface-muted)', padding: '1rem', borderRadius: 'var(--radius-sm)' }}>
              <strong>ข้อมูลที่ยืนยันและเผยแพร่ (Published): {data.published.accounts.toLocaleString()} บัญชี / {data.published.personas.toLocaleString()} ตัวตน</strong>
              <div style={{ fontSize: '0.9rem', color: 'var(--muted-ink)', marginTop: '0.25rem' }}>
                {data.count_semantics.published}
              </div>
            </div>

            <div style={{ background: 'var(--surface-muted)', padding: '1rem', borderRadius: 'var(--radius-sm)' }}>
              <strong>การถือครองและสิทธิ (Ownership Evidence):</strong>
              <div style={{ fontSize: '0.9rem', color: 'var(--muted-ink)', marginTop: '0.25rem' }}>
                {data.count_semantics.ownership}
              </div>
            </div>
          </div>
        </section>

        {/* Section 5: Limitations */}
        <section className="editorial-prose-card">
          <h2>5. ข้อจำกัดและสิ่งที่ระบบนี้ไม่ทำ (Explicit Limitations)</h2>
          <ul>
            <li>
              <strong>ไม่มีการจัดอันดับความนิยม:</strong> สารบบนี้ไม่มีการดึงตัวเลขยอดผู้ติดตาม ยอดเข้าชม หรือยอดกดถูกใจ เพื่อป้องกันการนำข้อมูลเชิงสารบบไปใช้แข่งขันเชิงตัวเลข
            </li>
            <li>
              <strong>ไม่มีการวิเคราะห์กลุ่มผู้ชมร่วม (No Audience Overlap):</strong> การมีบัญชีข้ามแพลตฟอร์มไม่ได้หมายความว่าฐานผู้ชมซ้อนทับกัน และไม่ได้ถูกสร้างเป็นกราฟเชื่อมโยงผู้ชม
            </li>
            <li>
              <strong>ไม่มีการติดตามสถานะการสตรีมสด (No Live Status Tracking):</strong> ระบบเก็บประวัติและหลักฐาน ไม่ใช่แดชบอร์ดแสดงว่าใครกำลังถ่ายทอดสด
            </li>
            <li>
              <strong>ไม่มีการสร้างหรือดึงรูปโปรไฟล์โดยไม่ได้รับสิทธิ์:</strong> สารบบใช้ตราสัญลักษณ์อักษรย่อ (Monogram Medallion) ที่ออกแบบเชิงกราฟิกแทนรูปภาพ เพื่อเคารพลิขสิทธิ์และสิทธิในภาพลักษณ์ของครีเอเตอร์
            </li>
          </ul>
        </section>

        {/* Section 6: Provenance & Correction Path */}
        <section className="editorial-prose-card">
          <h2>6. ที่มาของข้อมูลและการแจ้งแก้ไข</h2>
          <table className="stats-table" style={{ marginBottom: '1.5rem' }}>
            <tbody>
              <tr>
                <td style={{ width: '220px', fontWeight: 600 }}>เวอร์ชัน Schema</td>
                <td style={{ fontFamily: 'var(--font-sans)' }}>v{data.schema_version}</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600 }}>บันทึกรอบส่งออก</td>
                <td style={{ fontFamily: 'var(--font-sans)' }}>{formatDate(data.generated_at)} ({data.generated_at})</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600 }}>Source Registry SHA256</td>
                <td style={{ fontFamily: 'var(--font-sans)', wordBreak: 'break-all', fontSize: '0.84rem' }}>
                  {data.source_registry_sha256}
                </td>
              </tr>
            </tbody>
          </table>

          <h3>ช่องทางการแจ้งแก้ไขหรือเสนอชื่อครีเอเตอร์</h3>
          <p>
            หากท่านเป็นเจ้าของช่อง หรือพบข้อมูลที่คลาดเคลื่อน ต้องการอัปเดต หรือเสนอหลักฐานเพิ่มเติม สามารถดำเนินการได้โดย:
          </p>
          <ul>
            <li>
              เปิดประเด็นผ่าน{' '}
              <a
                href="https://github.com/Icezaza2543/ThaiVirtualCreatorRegistry/issues"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'var(--forest)', fontWeight: 600, textDecoration: 'underline' }}
              >
                GitHub Issues ของโครงการ
              </a>{' '}
              พร้อมแนบลิงก์หลักฐานปฐมภูมิที่เปิดเผยต่อสาธารณะ
            </li>
            <li>
              ส่ง Pull Request เสนอไฟล์การเปลี่ยนแปลงในรูปแบบ JSON ภายใต้ไดเรกทอรี <code>reviews/</code> ตามข้อกำหนดในคู่มือการมีส่วนร่วม (CONTRIBUTING.md)
            </li>
          </ul>
        </section>
      </div>
    </div>
  )
}
