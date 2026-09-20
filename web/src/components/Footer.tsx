import React from 'react'
import type { RegistryData } from '../types'
import { formatDate } from '../utils/formatters'

interface FooterProps {
  data: RegistryData | null
  onNavigate: (route: string) => void
}

export const Footer: React.FC<FooterProps> = ({ data, onNavigate }) => {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-top-grid">
          <div>
            <div className="footer-brand">สารบบครีเอเตอร์เสมือนไทย (Thai Virtual Creator Registry)</div>
            <p className="footer-desc">
              โครงการจัดทำฐานข้อมูลและทำเนียบบุคคลสาธารณะเสมือนจริงของไทย
              มุ่งเน้นความโปร่งใสและตรวจสอบได้ อ้างอิงจากหลักฐานปฐมภูมิที่เปิดเผยต่อสาธารณะ
              ไม่ใช่การจัดอันดับความนิยม และไม่ครอบคลุมข้อมูลส่วนบุคคลที่ไม่เปิดเผย
            </p>
          </div>

          <div>
            <div className="footer-col-title">การนำทาง</div>
            <ul className="footer-links-list">
              <li>
                <a
                  href="#/"
                  onClick={(e) => {
                    e.preventDefault()
                    onNavigate('/')
                  }}
                  className="footer-link"
                >
                  ทำเนียบครีเอเตอร์
                </a>
              </li>
              <li>
                <a
                  href="#/presence"
                  onClick={(e) => {
                    e.preventDefault()
                    onNavigate('/presence')
                  }}
                  className="footer-link"
                >
                  ภาพรวมแพลตฟอร์ม
                </a>
              </li>
              <li>
                <a
                  href="#/methodology"
                  onClick={(e) => {
                    e.preventDefault()
                    onNavigate('/methodology')
                  }}
                  className="footer-link"
                >
                  ระเบียบวิธีและข้อจำกัด
                </a>
              </li>
            </ul>
          </div>

          <div>
            <div className="footer-col-title">ข้อมูลและหลักฐาน</div>
            <ul className="footer-links-list">
              <li>
                <a
                  href="https://github.com/Icezaza2543/ThaiVirtualCreatorRegistry"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-link"
                >
                  GitHub Repository
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/Icezaza2543/ThaiVirtualCreatorRegistry/issues"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-link"
                >
                  เสนอแก้ไข / เพิ่มข้อมูล
                </a>
              </li>
              <li>
                <span style={{ fontSize: '0.82rem', color: 'rgba(251,250,247,0.5)' }}>
                  {data?.generated_at ? `ข้อมูลรอบการส่งออก: ${formatDate(data.generated_at)}` : ''}
                </span>
              </li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <div>
            © 2026 Thai Virtual Creator Registry · Internal Research / All Rights Reserved
          </div>
          <div>
            {data?.source_registry_sha256 && (
              <span style={{ fontFamily: 'var(--font-sans)', fontSize: '0.76rem' }}>
                SHA256: {data.source_registry_sha256.slice(0, 12)}...
              </span>
            )}
          </div>
        </div>
      </div>
    </footer>
  )
}
