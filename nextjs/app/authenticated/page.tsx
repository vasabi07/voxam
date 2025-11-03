"use client"

export default function DashboardPage() {
  return (
    <div className="p-4">
      <div className="flex flex-wrap justify-between gap-3 mb-6">
        <div className="flex min-w-72 flex-col gap-3">
          <p className="text-white tracking-light text-[32px] font-bold leading-tight">Dashboard</p>
          <p className="text-[#93b2c8] text-sm font-normal leading-normal">Overview of your VoiceExam activity</p>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-[#1a2832] rounded-xl p-6 border border-[#345165]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[#93b2c8] text-sm font-normal leading-normal">Total Documents</p>
              <p className="text-white text-2xl font-bold leading-tight">0</p>
            </div>
            <div className="text-[#47a7eb] text-2xl">📄</div>
          </div>
        </div>
        
        <div className="bg-[#1a2832] rounded-xl p-6 border border-[#345165]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[#93b2c8] text-sm font-normal leading-normal">Exams Created</p>
              <p className="text-white text-2xl font-bold leading-tight">0</p>
            </div>
            <div className="text-[#47a7eb] text-2xl">🎯</div>
          </div>
        </div>
        
        <div className="bg-[#1a2832] rounded-xl p-6 border border-[#345165]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[#93b2c8] text-sm font-normal leading-normal">Minutes Used</p>
              <p className="text-white text-2xl font-bold leading-tight">0/15</p>
            </div>
            <div className="text-[#47a7eb] text-2xl">⏱️</div>
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#1a2832] rounded-xl p-6 border border-[#345165]">
          <h3 className="text-white text-lg font-bold leading-tight mb-4">Recent Activity</h3>
          <div className="flex flex-col items-center justify-center py-12">
            <div className="text-[#93b2c8] text-4xl mb-4">📊</div>
            <p className="text-[#93b2c8] text-sm font-normal leading-normal text-center">
              No recent activity yet
            </p>
            <p className="text-[#93b2c8] text-xs font-normal leading-normal text-center mt-2">
              Upload documents and create exams to see your activity here
            </p>
          </div>
        </div>
        
        <div className="bg-[#1a2832] rounded-xl p-6 border border-[#345165]">
          <h3 className="text-white text-lg font-bold leading-tight mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <button className="w-full flex items-center gap-3 p-3 bg-[#243847] hover:bg-[#2a4454] rounded-lg transition-colors text-left">
              <div className="text-[#47a7eb]">📄</div>
              <div>
                <p className="text-white text-sm font-medium">Upload Document</p>
                <p className="text-[#93b2c8] text-xs">Add a new document for exam creation</p>
              </div>
            </button>
            
            <button className="w-full flex items-center gap-3 p-3 bg-[#243847] hover:bg-[#2a4454] rounded-lg transition-colors text-left">
              <div className="text-[#47a7eb]">🎯</div>
              <div>
                <p className="text-white text-sm font-medium">Start Voice Exam</p>
                <p className="text-[#93b2c8] text-xs">Begin a new voice examination session</p>
              </div>
            </button>
            
            <button className="w-full flex items-center gap-3 p-3 bg-[#243847] hover:bg-[#2a4454] rounded-lg transition-colors text-left">
              <div className="text-[#47a7eb]">⚙️</div>
              <div>
                <p className="text-white text-sm font-medium">View Settings</p>
                <p className="text-[#93b2c8] text-xs">Configure your account preferences</p>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}