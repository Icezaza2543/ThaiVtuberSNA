export const FORMAT_LABELS: Record<string, { th: string; en: string }> = {
  '2d': { th: 'Live2D / 2D', en: '2D Model' },
  '3d': { th: '3D Model', en: '3D Model' },
  'png': { th: 'PNGTuber', en: 'PNGTuber' },
  'unknown': { th: 'ไม่ระบุประเภทโมเดล', en: 'Unknown Model' },
}

export const ROLE_LABELS: Record<string, { th: string; en: string }> = {
  vtuber: { th: 'VTuber', en: 'VTuber' },
  vsinger: { th: 'VSinger', en: 'VSinger' },
  streamer: { th: 'สตรีมเมอร์', en: 'Streamer' },
  entertainer: { th: 'เอนเตอร์เทนเนอร์', en: 'Entertainer' },
  artist: { th: 'ศิลปิน / นักวาด', en: 'Artist' },
  educator: { th: 'ครู / ผู้ให้ความรู้', en: 'Educator' },
}

export const THAI_RELATION_LABELS: Record<string, { th: string; desc: string }> = {
  thai_language: {
    th: 'สื่อสารภาษาไทย',
    desc: 'ใช้ภาษาไทยเป็นภาษาหลักในการเผยแพร่ผลงานหรือสตรีม',
  },
  thai_community: {
    th: 'คอมมูนิตี้ไทย',
    desc: 'มีส่วนร่วมและเป็นที่ยอมรับในเครือข่ายครีเอเตอร์เสมือนไทย',
  },
  multiple: {
    th: 'หลากหลายเกณฑ์',
    desc: 'มีความสัมพันธ์กับไทยผ่านหลายองค์ประกอบทั้งภาษาและเครือข่าย',
  },
  self_declared_thai: {
    th: 'ระบุตัวตนไทย',
    desc: 'ระบุสัญชาติหรือความเป็นไทยไว้ในชีวประวัติทางการอย่างชัดแจ้ง',
  },
  thai_agency: {
    th: 'สังกัดในไทย',
    desc: 'สังกัดหรือดำเนินงานภายใต้บริษัท/กลุ่มสังกัดในประเทศไทย',
  },
  unknown: {
    th: 'รอการตรวจสอบเพิ่มเติม',
    desc: 'ยังไม่มีข้อมูลระบุยืนยันความสัมพันธ์กับไทยที่ชัดเจน',
  },
}

export const PLATFORM_CONFIG: Record<
  string,
  { name: string; brandColor: string; bgTone: string }
> = {
  youtube: { name: 'YouTube', brandColor: '#C4302B', bgTone: '#FAF0F0' },
  twitch: { name: 'Twitch', brandColor: '#9146FF', bgTone: '#F5F0FC' },
  tiktok: { name: 'TikTok', brandColor: '#111111', bgTone: '#F3F4F6' },
  x: { name: 'X', brandColor: '#1A1A1A', bgTone: '#F4F4F4' },
  facebook: { name: 'Facebook', brandColor: '#1877F2', bgTone: '#EEF4FD' },
  instagram: { name: 'Instagram', brandColor: '#E1306C', bgTone: '#FDF0F4' },
  ganknow: { name: 'GankNow', brandColor: '#FF5722', bgTone: '#FFF3E0' },
  kick: { name: 'Kick', brandColor: '#53FC18', bgTone: '#EBFCE6' },
  linktree: { name: 'Linktree', brandColor: '#43E660', bgTone: '#EBFCEF' },
  litlink: { name: 'lit.link', brandColor: '#00B0FF', bgTone: '#E6F6FD' },
}

export function getCreatorMonogram(name: string): { initials: string; hue: number } {
  // Strip quotes and leading symbols
  const cleaned = name.replace(/^["'“”‘«\s]+/, '').trim()
  if (!cleaned) return { initials: 'VC', hue: 42 }

  // Extract first 1 or 2 meaningful letters / syllables
  const words = cleaned.split(/[\s/._-]+/).filter(Boolean)
  let initials = ''

  if (words.length >= 2) {
    initials = words[0].slice(0, 1) + words[1].slice(0, 1)
  } else {
    // Check if Thai or Latin
    const firstChar = cleaned.charAt(0)
    if (/[\u0E00-\u0E7F]/.test(firstChar)) {
      // Thai: take up to 2 graphemes
      initials = cleaned.slice(0, 2)
    } else {
      initials = cleaned.slice(0, 2).toUpperCase()
    }
  }

  // Generate deterministic hue between 30 and 220 (forest, gold, earth tones)
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = (hash << 5) - hash + name.charCodeAt(i)
    hash |= 0
  }
  const hue = Math.abs(hash) % 360

  return { initials: initials.trim(), hue }
}

export function formatDate(isoStr: string | null | undefined): string {
  if (!isoStr) return 'ไม่ระบุ'
  try {
    const d = new Date(isoStr)
    if (isNaN(d.getTime())) return isoStr
    return d.toLocaleDateString('th-TH', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return isoStr
  }
}
