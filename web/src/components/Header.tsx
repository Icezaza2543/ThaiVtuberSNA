import React from 'react'

interface HeaderProps {
  currentRoute: string
  onNavigate: (route: string) => void
}

export const Header: React.FC<HeaderProps> = ({ currentRoute, onNavigate }) => {
  return (
    <header className="site-header">
      <div className="container header-inner">
        <a
          href="#/"
          onClick={(e) => {
            e.preventDefault()
            onNavigate('/')
          }}
          className="brand-block"
        >
          <div className="brand-mark" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <rect width="24" height="24" rx="5" fill="#1A221F" />
              <circle cx="12" cy="12" r="9" stroke="#A28143" strokeWidth="1.5" strokeDasharray="2 2" />
              <path d="M8 17L12 7L16 17L14 17L12 11L10 17Z" fill="#E9DEC7" />
            </svg>
          </div>
          <div>
            <span className="brand-text-th">สารบบครีเอเตอร์เสมือนไทย</span>
            <span className="brand-text-en">Thai Virtual Creator Registry</span>
          </div>
        </a>

        <nav className="nav-links" aria-label="Main Navigation">
          <a
            href="#/"
            onClick={(e) => {
              e.preventDefault()
              onNavigate('/')
            }}
            className={`nav-item ${currentRoute === '/' || currentRoute.startsWith('/creator') ? 'active' : ''}`}
          >
            <span className="nav-label-full">ทำเนียบครีเอเตอร์</span>
            <span className="nav-label-mobile">ทำเนียบ</span>
          </a>
          <a
            href="#/presence"
            onClick={(e) => {
              e.preventDefault()
              onNavigate('/presence')
            }}
            className={`nav-item ${currentRoute === '/presence' ? 'active' : ''}`}
          >
            <span className="nav-label-full">ภาพรวมแพลตฟอร์ม</span>
            <span className="nav-label-mobile">แพลตฟอร์ม</span>
          </a>
          <a
            href="#/methodology"
            onClick={(e) => {
              e.preventDefault()
              onNavigate('/methodology')
            }}
            className={`nav-item ${currentRoute === '/methodology' ? 'active' : ''}`}
          >
            <span className="nav-label-full">ระเบียบวิธีและข้อจำกัด</span>
            <span className="nav-label-mobile">ระเบียบวิธี</span>
          </a>
          <a
            href="./index.html"
            className="nav-item"
            style={{ opacity: 0.9 }}
          >
            <span className="nav-label-full">เครือข่าย SNA</span>
            <span className="nav-label-mobile">SNA</span>
          </a>
          <a
            href="https://github.com/Icezaza2543/ThaiVtuberSNA"
            target="_blank"
            rel="noopener noreferrer"
            className="nav-item"
            style={{ opacity: 0.9 }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
            </svg>
            <span>GitHub</span>
          </a>
        </nav>
      </div>
    </header>
  )
}
