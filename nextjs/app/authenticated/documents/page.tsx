"use client"

export default function DocumentsPage() {
  return (
    <>
      <div className="flex flex-wrap justify-between gap-3 p-4">
        <div className="flex min-w-72 flex-col gap-3">
          <p className="text-white tracking-light text-[32px] font-bold leading-tight">Documents</p>
          <p className="text-[#93b2c8] text-sm font-normal leading-normal">Manage your documents for exams</p>
        </div>
      </div>
      
      <div className="flex flex-col p-4">
        <div className="flex flex-col items-center gap-6 rounded-xl border-2 border-dashed border-[#345165] px-6 py-14">
          <div className="flex max-w-[480px] flex-col items-center gap-2">
            <p className="text-white text-lg font-bold leading-tight tracking-[-0.015em] max-w-[480px] text-center">
              Drag and drop or browse to upload
            </p>
            <p className="text-white text-sm font-normal leading-normal max-w-[480px] text-center">
              Supported formats: PDF, DOCX, TXT
            </p>
          </div>
          <button className="flex min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-xl h-10 px-4 bg-[#243847] text-white text-sm font-bold leading-normal tracking-[0.015em] hover:bg-[#2a4454] transition-colors">
            <span className="truncate">Upload Document</span>
          </button>
        </div>
      </div>
      
      <h2 className="text-white text-[22px] font-bold leading-tight tracking-[-0.015em] px-4 pb-3 pt-5">
        Existing Documents
      </h2>
      
      <div className="px-4 py-3">
        <div className="flex overflow-hidden rounded-xl border border-[#345165] bg-[#111b22]">
          <table className="flex-1">
            <thead>
              <tr className="bg-[#1a2832]">
                <th className="px-4 py-3 text-left text-white w-[400px] text-sm font-medium leading-normal">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-white w-14 text-sm font-medium leading-normal">
                  Preview
                </th>
                <th className="px-4 py-3 text-left w-60 text-[#93b2c8] text-sm font-medium leading-normal">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-t-[#345165]">
                <td colSpan={3} className="h-[120px] px-4 py-8 text-center">
                  <div className="flex flex-col items-center gap-3">
                    <div className="text-[#93b2c8] text-lg">📄</div>
                    <p className="text-[#93b2c8] text-sm font-normal leading-normal">
                      No documents uploaded yet
                    </p>
                    <p className="text-[#93b2c8] text-xs font-normal leading-normal">
                      Upload your first document to get started with creating exams
                    </p>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
