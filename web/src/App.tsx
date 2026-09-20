import { useState, useEffect, useCallback } from 'react'
import type { RegistryData } from './types'
import { Header } from './components/Header'
import { Footer } from './components/Footer'
import { DirectoryView } from './views/DirectoryView'
import { CreatorDetailView } from './views/CreatorDetailView'
import { PresenceView } from './views/PresenceView'
import { MethodologyView } from './views/MethodologyView'

export function App() {
  const [data, setData] = useState<RegistryData | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [currentHash, setCurrentHash] = useState<string>(
    window.location.hash || '#/'
  )

  const [refreshTrigger, setRefreshTrigger] = useState(0)

  // Fetch exported frontend projection data
  useEffect(() => {
    let ignore = false
    async function fetchData() {
      try {
        setLoading(true)
        setError(null)
        const dataUrl = `${import.meta.env.BASE_URL}data/registry.json`
        const response = await fetch(dataUrl)
        if (!response.ok) {
          throw new Error(
            `ไม่สามารถโหลดข้อมูลสารบบได้ (HTTP ${response.status}: ${response.statusText})`
          )
        }
        const json: RegistryData = await response.json()
        if (!ignore) {
          setData(json)
        }
      } catch (err: any) {
        if (!ignore) {
          console.error('Failed to load registry data:', err)
          setError(
            err?.message ||
              'เกิดข้อผิดพลาดในการโหลดข้อมูล กรุณาตรวจสอบการเชื่อมต่ออินเทอร์เน็ต'
          )
        }
      } finally {
        if (!ignore) {
          setLoading(false)
        }
      }
    }

    fetchData()
    return () => {
      ignore = true
    }
  }, [refreshTrigger])

  const retryLoading = useCallback(() => {
    setRefreshTrigger((prev) => prev + 1)
  }, [])

  // Listen to hash changes for deep linking and back/forward navigation
  useEffect(() => {
    const handleHashChange = () => {
      setCurrentHash(window.location.hash || '#/')
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  const navigateTo = (path: string) => {
    const newHash = path.startsWith('#') ? path : `#${path}`
    window.location.hash = newHash
    setCurrentHash(newHash)
  }

  // Parse current route
  const cleanRoute = currentHash.replace(/^#/, '') || '/'
  const isCreatorDetail = cleanRoute.startsWith('/creator/')
  const selectedCreatorId = isCreatorDetail
    ? cleanRoute.replace('/creator/', '')
    : null

  // Find creator for detail view
  const selectedCreator = data && selectedCreatorId
    ? data.creators.find((c) => c.id === selectedCreatorId)
    : null

  // Update document title based on active route
  useEffect(() => {
    if (selectedCreator) {
      document.title = `${selectedCreator.name} — สารบบครีเอเตอร์เสมือนไทย`
    } else if (cleanRoute === '/presence') {
      document.title = 'ภาพรวมแพลตฟอร์ม — สารบบครีเอเตอร์เสมือนไทย'
    } else if (cleanRoute === '/methodology') {
      document.title = 'ระเบียบวิธีและข้อจำกัด — สารบบครีเอเตอร์เสมือนไทย'
    } else {
      document.title = 'ทำเนียบบุคคลสาธารณะเสมือนจริงของไทย — Thai Virtual Creator Registry'
    }
  }, [cleanRoute, selectedCreator])

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header currentRoute={cleanRoute} onNavigate={navigateTo} />

      <main style={{ flex: 1 }}>
        {/* Loading State */}
        {loading && (
          <div className="container" style={{ padding: '6rem 1.5rem', textAlign: 'center' }}>
            <div className="state-box">
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  margin: '0 auto 1.25rem',
                  border: '3px solid var(--border)',
                  borderTopColor: 'var(--gold)',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                }}
              />
              <style>{`
                @keyframes spin {
                  to { transform: rotate(360deg); }
                }
              `}</style>
              <h2 className="state-title">กำลังเปิดหน้าสารบบ...</h2>
              <p className="state-desc">
                กำลังอ่านข้อมูลที่ผ่านการตรวจสอบหลักฐานปฐมภูมิ
              </p>
            </div>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="container" style={{ padding: '6rem 1.5rem' }}>
            <div
              className="state-box"
              style={{
                borderColor: 'var(--danger)',
                backgroundColor: 'var(--danger-bg)',
              }}
            >
              <h2 className="state-title" style={{ color: 'var(--danger)' }}>
                ไม่สามารถโหลดข้อมูลสารบบได้
              </h2>
              <p className="state-desc">{error}</p>
              <button
                type="button"
                className="chip-btn active"
                onClick={retryLoading}
                style={{ margin: '0 auto' }}
              >
                ลองใหม่อีกครั้ง
              </button>
            </div>
          </div>
        )}

        {/* Loaded Content */}
        {!loading && data && (
          <>
            {cleanRoute === '/' && (
              <DirectoryView
                data={data}
                onSelectCreator={(id) => navigateTo(`/creator/${id}`)}
              />
            )}

            {isCreatorDetail && (
              selectedCreator ? (
                <CreatorDetailView
                  creator={selectedCreator}
                  onBack={() => navigateTo('/')}
                />
              ) : (
                <div className="container" style={{ padding: '4rem 1.5rem' }}>
                  <div className="state-box">
                    <h2 className="state-title">ไม่พบข้อมูลครีเอเตอร์รหัสนี้</h2>
                    <p className="state-desc">
                      รหัสตัวตน <code>{selectedCreatorId}</code> อาจยังไม่ผ่านการตรวจสอบ หรือไม่มีอยู่ในฐานข้อมูลสารบบ
                    </p>
                    <button
                      type="button"
                      className="chip-btn active"
                      onClick={() => navigateTo('/')}
                      style={{ margin: '0 auto' }}
                    >
                      กลับสู่ทำเนียบครีเอเตอร์
                    </button>
                  </div>
                </div>
              )
            )}

            {cleanRoute === '/presence' && <PresenceView data={data} />}

            {cleanRoute === '/methodology' && <MethodologyView data={data} />}
          </>
        )}
      </main>

      <Footer data={data} onNavigate={navigateTo} />
    </div>
  )
}
export default App
