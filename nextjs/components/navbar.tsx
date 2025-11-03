"use client"
import Link from 'next/link'

export default function Navbar() {
  return (
    <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-b-[#243847] px-10 py-3">
      <div className="flex items-center gap-4 text-white">
        <div className="size-4">
          <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M24 18.4228L42 11.475V34.3663C42 34.7796 41.7457 35.1504 41.3601 35.2992L24 42V18.4228Z"
              fill="currentColor"
            />
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M24 8.18819L33.4123 11.574L24 15.2071L14.5877 11.574L24 8.18819ZM9 15.8487L21 20.4805V37.6263L9 32.9945V15.8487ZM27 37.6263V20.4805L39 15.8487V32.9945L27 37.6263ZM25.354 2.29885C24.4788 1.98402 23.5212 1.98402 22.646 2.29885L4.98454 8.65208C3.7939 9.08038 3 10.2097 3 11.475V34.3663C3 36.0196 4.01719 37.5026 5.55962 38.098L22.9197 44.7987C23.6149 45.0671 24.3851 45.0671 25.0803 44.7987L42.4404 38.098C43.9828 37.5026 45 36.0196 45 34.3663V11.475C45 10.2097 44.2061 9.08038 43.0155 8.65208L25.354 2.29885Z"
              fill="currentColor"
            />
          </svg>
        </div>
        <Link href="/authenticated">
          <h2 className="text-white text-lg font-bold leading-tight tracking-[-0.015em] hover:text-[#47a7eb] transition-colors cursor-pointer">
            VoiceExam
          </h2>
        </Link>
      </div>
      <div className="flex flex-1 justify-end gap-8">
        <div className="flex items-center gap-9">
          <Link href="/authenticated" className="text-white text-sm font-medium leading-normal hover:text-[#47a7eb] transition-colors">
            Dashboard
          </Link>
          <Link href="/authenticated/examlist" className="text-white text-sm font-medium leading-normal hover:text-[#47a7eb] transition-colors">
            Exams
          </Link>
          <Link href="/authenticated/documents" className="text-white text-sm font-medium leading-normal hover:text-[#47a7eb] transition-colors">
            Documents
          </Link>
          <Link href="/authenticated/settings" className="text-white text-sm font-medium leading-normal hover:text-[#47a7eb] transition-colors">
            Settings
          </Link>
        </div>
        <div
          className="bg-center bg-no-repeat aspect-square bg-cover rounded-full size-10 cursor-pointer hover:ring-2 hover:ring-[#47a7eb] transition-all"
          style={{backgroundImage: 'url("https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=40&h=40&fit=crop&crop=face")'}}
        />
      </div>
    </header>
  )
}
