

"use client"
import Link from 'next/link'

export default function Home() {
  return (
    <div className="relative flex size-full min-h-screen flex-col bg-[#111b22] dark group/design-root overflow-x-hidden" style={{fontFamily: 'Inter, "Noto Sans", sans-serif'}}>
      <div className="layout-container flex h-full grow flex-col">
        <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-b-[#243847] px-10 py-3">
          <div className="flex items-center gap-4 text-white">
            <div className="size-4">
              <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 6H42L36 24L42 42H6L12 24L6 6Z" fill="currentColor"></path>
              </svg>
            </div>
            <h2 className="text-white text-lg font-bold leading-tight tracking-[-0.015em]">VoiceExam AI</h2>
          </div>
          <div className="flex flex-1 justify-end gap-8">
            <div className="flex items-center gap-9">
              <a className="text-white text-sm font-medium leading-normal cursor-pointer hover:text-[#47a7eb] transition-colors" onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}>Features</a>
              <a className="text-white text-sm font-medium leading-normal cursor-pointer hover:text-[#47a7eb] transition-colors" onClick={() => document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' })}>Pricing</a>
              <a className="text-white text-sm font-medium leading-normal cursor-pointer hover:text-[#47a7eb] transition-colors" onClick={() => document.getElementById('contact')?.scrollIntoView({ behavior: 'smooth' })}>Contact</a>
            </div>
            <div className="flex gap-2">
              <button className="flex min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-xl h-10 px-4 bg-[#47a7eb] text-[#111b22] text-sm font-bold leading-normal tracking-[0.015em]">
                <span className="truncate">Sign Up</span>
              </button>
              <button className="flex min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-xl h-10 px-4 bg-[#243847] text-white text-sm font-bold leading-normal tracking-[0.015em]">
                <span className="truncate">Login</span>
              </button>
            </div>
          </div>
        </header>
        
        <div className="px-40 flex flex-1 justify-center py-5">
          <div className="layout-content-container flex flex-col max-w-[960px] flex-1">
            <div className="@container">
              <div className="@[480px]:p-4">
                <div
                  className="flex min-h-[480px] flex-col gap-6 bg-cover bg-center bg-no-repeat @[480px]:gap-8 @[480px]:rounded-xl items-center justify-center p-4"
                  style={{
                    backgroundImage: 'linear-gradient(rgba(0, 0, 0, 0.1) 0%, rgba(0, 0, 0, 0.4) 100%), url("https://lh3.googleusercontent.com/aida-public/AB6AXuAvZhxfenRzqtUoVXX3mXM6h5kGSPKvbAcI4GZ5lDeIs4po8A-jxMx5gAqvs_WW8uTfO69K3EYSwCKD67gePLudBgeK35BhhYsS1tEZ9saf17ghhPUNuC5tp1imGB0Hw3Gnou-zy-Zror5ZEx_IEYFMAZPX9dzvKKO3xoW8c6iI0rFmjAOUw9e_53duDgo80Sp111nkA-viRBHZnJtkT0sK5VoNA4Mri_0qWQXA6nX1BXqyrODCYRZGbAc7AirJQZ07Rtt9Fta3lhg")'
                  }}
                >
                  <div className="flex flex-col gap-2 text-center">
                    <h1 className="text-white text-4xl font-black leading-tight tracking-[-0.033em] @[480px]:text-5xl @[480px]:font-black @[480px]:leading-tight @[480px]:tracking-[-0.033em]">
                      Revolutionize Your Voice Assessments with AI
                    </h1>
                    <h2 className="text-white text-sm font-normal leading-normal @[480px]:text-base @[480px]:font-normal @[480px]:leading-normal">
                      Experience the future of voice exams with our AI-powered platform. Get instant feedback, personalized insights, and accurate evaluations.
                    </h2>
                  </div>
                  <Link href="/exam">
                    <button className="flex min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-xl h-10 px-4 @[480px]:h-12 @[480px]:px-5 bg-[#47a7eb] text-[#111b22] text-sm font-bold leading-normal tracking-[0.015em] @[480px]:text-base @[480px]:font-bold @[480px]:leading-normal @[480px]:tracking-[0.015em]">
                      <span className="truncate">Try Now</span>
                    </button>
                  </Link>
                </div>
              </div>
            </div>
            
            {/* Bloom's Taxonomy & Pedagogy Section */}
            <div className="flex flex-col gap-10 px-4 py-10 @container">
              <div className="flex flex-col gap-4">
                <h1 className="text-white tracking-light text-[32px] font-bold leading-tight @[480px]:text-4xl @[480px]:font-black @[480px]:leading-tight @[480px]:tracking-[-0.033em] max-w-[720px]">
                  Built on Educational Science
                </h1>
                <p className="text-white text-base font-normal leading-normal max-w-[720px]">
                  Our platform is grounded in proven pedagogical frameworks, leveraging Bloom&apos;s Taxonomy to create assessments that truly measure understanding across all cognitive levels.
                </p>
              </div>
              
              <div className="grid grid-cols-1 @[768px]:grid-cols-2 gap-6">
                <div className="flex flex-col gap-4 p-6 bg-[#1a2832] rounded-xl border border-[#345165]">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-[#47a7eb] rounded-xl flex items-center justify-center">
                      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="white" viewBox="0 0 256 256">
                        <path d="M208,32H48A16,16,0,0,0,32,48V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V48A16,16,0,0,0,208,32ZM176,152H80a8,8,0,0,1,0-16h96a8,8,0,0,1,0,16Zm0-32H80a8,8,0,0,1,0-16h96a8,8,0,0,1,0,16Zm0-32H80a8,8,0,0,1,0-16h96a8,8,0,0,1,0,16Z"/>
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-white text-xl font-bold">Bloom&apos;s Taxonomy Integration</h3>
                      <p className="text-[#93b2c8] text-sm">Evidence-based assessment design</p>
                    </div>
                  </div>
                  <p className="text-[#93b2c8] text-sm leading-relaxed">
                    Our AI automatically generates questions across all six cognitive levels: Remember, Understand, Apply, Analyze, Evaluate, and Create. This ensures comprehensive assessment of student knowledge and critical thinking skills.
                  </p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    <span className="px-2 py-1 bg-[#243847] text-[#47a7eb] text-xs rounded-full">Remember</span>
                    <span className="px-2 py-1 bg-[#243847] text-[#47a7eb] text-xs rounded-full">Understand</span>
                    <span className="px-2 py-1 bg-[#243847] text-[#47a7eb] text-xs rounded-full">Apply</span>
                    <span className="px-2 py-1 bg-[#243847] text-[#47a7eb] text-xs rounded-full">Analyze</span>
                    <span className="px-2 py-1 bg-[#243847] text-[#47a7eb] text-xs rounded-full">Evaluate</span>
                    <span className="px-2 py-1 bg-[#243847] text-[#47a7eb] text-xs rounded-full">Create</span>
                  </div>
                </div>
                
                <div className="flex flex-col gap-4 p-6 bg-[#1a2832] rounded-xl border border-[#345165]">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-[#47a7eb] rounded-xl flex items-center justify-center">
                      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="white" viewBox="0 0 256 256">
                        <path d="M225.86,102.82c-3.77-3.94-7.67-8-9.14-11.57-1.36-3.27-1.44-8.69-1.52-13.94-.15-9.76-.31-20.82-8-28.51s-18.75-7.85-28.51-8c-5.25-.08-10.67-.16-13.94-1.52-3.56-1.47-7.63-5.37-11.57-9.14C146.28,23.51,138.44,16,128,16s-18.27,7.51-25.18,14.14c-3.94,3.77-8,7.67-11.57,9.14C88,40.64,82.56,40.72,77.31,40.8c-9.76.15-20.82.31-28.51,8S41,67.55,40.8,77.31c-.08,5.25-.16,10.67-1.52,13.94-1.47,3.56-5.37,7.63-9.14,11.57C23.51,109.72,16,117.56,16,128s7.51,18.27,14.14,25.18c3.77,3.94,7.67,8,9.14,11.57,1.36,3.27,1.44,8.69,1.52,13.94.15,9.76.31,20.82,8,28.51s18.75,7.85,28.51,8c5.25.08,10.67.16,13.94,1.52,3.56,1.47,7.63,5.37,11.57,9.14C109.72,232.49,117.56,240,128,240s18.27-7.51,25.18-14.14c3.94-3.77,8-7.67,11.57-9.14,3.27-1.36,8.69-1.44,13.94-1.52,9.76-.15,20.82-.31,28.51-8s7.85-18.75,8-28.51c.08-5.25.16-10.67,1.52-13.94,1.47-3.56,5.37-7.63,9.14-11.57C232.49,146.28,240,138.44,240,128S232.49,109.73,225.86,102.82Zm-52.2,6.84-56,56a8,8,0,0,1-11.32,0l-24-24a8,8,0,0,1,11.32-11.32L112,148.69l50.34-50.35a8,8,0,0,1,11.32,11.32Z"/>
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-white text-xl font-bold">Pedagogical Excellence</h3>
                      <p className="text-[#93b2c8] text-sm">Research-backed learning principles</p>
                    </div>
                  </div>
                  <p className="text-[#93b2c8] text-sm leading-relaxed">
                    Built on constructivist learning theory, our platform promotes active learning through conversational assessment. Students engage in meaningful dialogue, demonstrating understanding through explanation and application rather than rote memorization.
                  </p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    <span className="px-2 py-1 bg-[#243847] text-[#47a7eb] text-xs rounded-full">Active Learning</span>
                    <span className="px-2 py-1 bg-[#243847] text-[#47a7eb] text-xs rounded-full">Formative Assessment</span>
                    <span className="px-2 py-1 bg-[#243847] text-[#47a7eb] text-xs rounded-full">Metacognition</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-10 px-4 py-10 @container" id="features">
              <div className="flex flex-col gap-4">
                <h1 className="text-white tracking-light text-[32px] font-bold leading-tight @[480px]:text-4xl @[480px]:font-black @[480px]:leading-tight @[480px]:tracking-[-0.033em] max-w-[720px]">
                  Advanced AI Features
                </h1>
                <p className="text-white text-base font-normal leading-normal max-w-[720px]">
                  Our AI-powered platform revolutionizes educational assessments with real-time voice interaction, intelligent document processing, and personalized learning experiences based on educational best practices.
                </p>
              </div>
              
              <div className="grid grid-cols-[repeat(auto-fit,minmax(158px,1fr))] gap-3">
                <div className="flex flex-col gap-3 pb-3">
                  <div
                    className="w-full bg-center bg-no-repeat aspect-video bg-cover rounded-xl"
                    style={{backgroundImage: 'url("https://images.unsplash.com/photo-1589254065878-42c9da997008?w=400&h=300&fit=crop")'}}
                  ></div>
                  <div>
                    <p className="text-white text-base font-medium leading-normal">Real-time Voice Interaction</p>
                    <p className="text-[#93b2c8] text-sm font-normal leading-normal">
                      Engage in natural conversations with AI agents through WebRTC technology. Experience seamless voice-based exams with instant feedback and analysis.
                    </p>
                  </div>
                </div>
                
                <div className="flex flex-col gap-3 pb-3">
                  <div
                    className="w-full bg-center bg-no-repeat aspect-video bg-cover rounded-xl"
                    style={{backgroundImage: 'url("https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=400&h=300&fit=crop")'}}
                  ></div>
                  <div>
                    <p className="text-white text-base font-medium leading-normal">Intelligent Document Processing</p>
                    <p className="text-[#93b2c8] text-sm font-normal leading-normal">
                      Upload PDFs and documents to automatically generate exam questions aligned with Bloom&apos;s taxonomy levels. Our AI analyzes content and creates questions targeting specific cognitive skills from basic recall to complex synthesis.
                    </p>
                  </div>
                </div>
                
                <div className="flex flex-col gap-3 pb-3">
                  <div
                    className="w-full bg-center bg-no-repeat aspect-video bg-cover rounded-xl"
                    style={{backgroundImage: 'url("https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=400&h=300&fit=crop")'}}
                  ></div>
                  <div>
                    <p className="text-white text-base font-medium leading-normal">Advanced AI Assessment</p>
                    <p className="text-[#93b2c8] text-sm font-normal leading-normal">
                      Powered by LangGraph workflows and OpenAI, our system provides comprehensive evaluation of student responses with detailed insights across multiple learning dimensions.
                    </p>
                  </div>
                </div>
                
                <div className="flex flex-col gap-3 pb-3">
                  <div
                    className="w-full bg-center bg-no-repeat aspect-video bg-cover rounded-xl"
                    style={{backgroundImage: 'url("https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=300&fit=crop")'}}
                  ></div>
                  <div>
                    <p className="text-white text-base font-medium leading-normal">Socratic Questioning</p>
                    <p className="text-[#93b2c8] text-sm font-normal leading-normal">
                      Engage students through guided inquiry using Socratic questioning techniques. Our AI prompts deeper thinking, challenges assumptions, and builds critical reasoning skills through conversational assessment.
                    </p>
                  </div>
                </div>
                
                <div className="flex flex-col gap-3 pb-3">
                  <div
                    className="w-full bg-center bg-no-repeat aspect-video bg-cover rounded-xl"
                    style={{backgroundImage: 'url("https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=400&h=300&fit=crop")'}}
                  ></div>
                  <div>
                    <p className="text-white text-base font-medium leading-normal">Adaptive Learning Pathways</p>
                    <p className="text-[#93b2c8] text-sm font-normal leading-normal">
                      Personalized assessment experiences that adapt to student responses in real-time. Questions dynamically adjust difficulty and focus areas based on demonstrated understanding and learning gaps.
                    </p>
                  </div>
                </div>
              </div>
            </div>
            
            <h2 className="text-white text-[22px] font-bold leading-tight tracking-[-0.015em] px-4 pb-3 pt-5" id="pricing">Pricing Plans</h2>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(228px,1fr))] gap-2.5 px-4 py-3 @3xl:grid-cols-4">
              <div className="flex flex-1 flex-col gap-4 rounded-xl border border-solid border-[#345165] bg-[#1a2832] p-6">
                <div className="flex flex-col gap-1">
                  <h1 className="text-white text-base font-bold leading-tight">Trial</h1>
                  <p className="flex items-baseline gap-1 text-white">
                    <span className="text-white text-4xl font-black leading-tight tracking-[-0.033em]">Free</span>
                  </p>
                  <p className="text-[#93b2c8] text-xs">15 minutes included</p>
                </div>
                <button className="flex min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-xl h-10 px-4 bg-[#243847] text-white text-sm font-bold leading-normal tracking-[0.015em]">
                  <span className="truncate">Start Trial</span>
                </button>
                <div className="flex flex-col gap-2">
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    15 minutes of voice exams
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    1 document upload
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Share exams with anyone
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Basic AI-generated questions (3 cognitive levels)
                  </div>
                </div>
              </div>
              
              <div className="flex flex-1 flex-col gap-4 rounded-xl border border-solid border-[#345165] bg-[#1a2832] p-6">
                <div className="flex flex-col gap-1">
                  <h1 className="text-white text-base font-bold leading-tight">Starter</h1>
                  <p className="flex items-baseline gap-1 text-white">
                    <span className="text-white text-4xl font-black leading-tight tracking-[-0.033em]">$9</span>
                    <span className="text-white text-base font-bold leading-tight">/month</span>
                  </p>
                  <p className="text-[#93b2c8] text-xs">100 minutes included</p>
                </div>
                <button className="flex min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-xl h-10 px-4 bg-[#243847] text-white text-sm font-bold leading-normal tracking-[0.015em]">
                  <span className="truncate">Get Started</span>
                </button>
                <div className="flex flex-col gap-2">
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    100 minutes of voice exams
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Unlimited document uploads
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Share with unlimited users
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Full Bloom&apos;s taxonomy question generation
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Socratic questioning & guided inquiry
                  </div>
                </div>
              </div>
              
              <div className="flex flex-1 flex-col gap-4 rounded-xl border border-solid border-[#345165] bg-[#1a2832] p-6">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <h1 className="text-white text-base font-bold leading-tight">Pro</h1>
                    <p className="text-[#111b22] text-xs font-medium leading-normal tracking-[0.015em] rounded-xl bg-[#47a7eb] px-3 py-[3px] text-center">Popular</p>
                  </div>
                  <p className="flex items-baseline gap-1 text-white">
                    <span className="text-white text-4xl font-black leading-tight tracking-[-0.033em]">$19</span>
                    <span className="text-white text-base font-bold leading-tight">/month</span>
                  </p>
                  <p className="text-[#93b2c8] text-xs">300 minutes included</p>
                </div>
                <button className="flex min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-xl h-10 px-4 bg-[#47a7eb] text-[#111b22] text-sm font-bold leading-normal tracking-[0.015em]">
                  <span className="truncate">Choose Plan</span>
                </button>
                <div className="flex flex-col gap-2">
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    300 minutes of voice exams
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Unlimited document uploads
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Share with unlimited users
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Advanced learning analytics & insights
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Priority support
                  </div>
                </div>
              </div>
              
              <div className="flex flex-1 flex-col gap-4 rounded-xl border border-solid border-[#345165] bg-[#1a2832] p-6">
                <div className="flex flex-col gap-1">
                  <h1 className="text-white text-base font-bold leading-tight">Scale</h1>
                  <p className="flex items-baseline gap-1 text-white">
                    <span className="text-white text-4xl font-black leading-tight tracking-[-0.033em]">$39</span>
                    <span className="text-white text-base font-bold leading-tight">/month</span>
                  </p>
                  <p className="text-[#93b2c8] text-xs">600 minutes included</p>
                </div>
                <button className="flex min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-xl h-10 px-4 bg-[#243847] text-white text-sm font-bold leading-normal tracking-[0.015em]">
                  <span className="truncate">Get Scale</span>
                </button>
                <div className="flex flex-col gap-2">
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    600 minutes of voice exams
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Unlimited document uploads
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Share with unlimited users
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Advanced analytics & insights
                  </div>
                  <div className="text-[13px] font-normal leading-normal flex gap-3 text-white">
                    <div className="text-white">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
                        <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
                      </svg>
                    </div>
                    Dedicated support
                  </div>
                </div>
              </div>
            </div>
            
            <div className="@container">
              <div className="flex flex-col justify-end gap-6 px-4 py-10 @[480px]:gap-8 @[480px]:px-10 @[480px]:py-20">
                <div className="flex flex-col gap-2 text-center mx-auto">
                  <h1 className="text-white tracking-light text-[32px] font-bold leading-tight @[480px]:text-4xl @[480px]:font-black @[480px]:leading-tight @[480px]:tracking-[-0.033em] max-w-[720px] mx-auto">
                    Ready to Transform Educational Assessment?
                  </h1>
                  <p className="text-white text-base font-normal leading-normal max-w-[720px] mx-auto">
                    Join educators worldwide who are revolutionizing learning through evidence-based, AI-powered voice assessments grounded in pedagogical excellence and Bloom&apos;s taxonomy.
                  </p>
                </div>
                <div className="flex flex-1 justify-center">
                  <div className="flex justify-center">
                    <Link href="/exam">
                      <button className="flex min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-xl h-10 px-4 @[480px]:h-12 @[480px]:px-5 bg-[#47a7eb] text-[#111b22] text-sm font-bold leading-normal tracking-[0.015em] @[480px]:text-base @[480px]:font-bold @[480px]:leading-normal @[480px]:tracking-[0.015em] grow">
                        <span className="truncate">Get Started</span>
                      </button>
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <footer className="flex justify-center" id="contact">
          <div className="flex max-w-[960px] flex-1 flex-col">
            <footer className="flex flex-col gap-6 px-5 py-10 text-center @container">
              <div className="flex flex-wrap items-center justify-center gap-6 @[480px]:flex-row @[480px]:justify-around">
                <a className="text-[#93b2c8] text-base font-normal leading-normal min-w-40" href="#">Terms of Service</a>
                <a className="text-[#93b2c8] text-base font-normal leading-normal min-w-40" href="#">Privacy Policy</a>
                <a className="text-[#93b2c8] text-base font-normal leading-normal min-w-40" href="#">Contact Us</a>
              </div>
              <div className="flex flex-wrap justify-center gap-4">
                <a href="#">
                  <div className="text-[#93b2c8]">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24px" height="24px" fill="currentColor" viewBox="0 0 256 256">
                      <path d="M247.39,68.94A8,8,0,0,0,240,64H209.57A48.66,48.66,0,0,0,168.1,40a46.91,46.91,0,0,0-33.75,13.7A47.9,47.9,0,0,0,120,88v6.09C79.74,83.47,46.81,50.72,46.46,50.37a8,8,0,0,0-13.65,4.92c-4.31,47.79,9.57,79.77,22,98.18a110.93,110.93,0,0,0,21.88,24.2c-15.23,17.53-39.21,26.74-39.47,26.84a8,8,0,0,0-3.85,11.93c.75,1.12,3.75,5.05,11.08,8.72C53.51,229.7,65.48,232,80,232c70.67,0,129.72-54.42,135.75-124.44l29.91-29.9A8,8,0,0,0,247.39,68.94Zm-45,29.41a8,8,0,0,0-2.32,5.14C196,166.58,143.28,216,80,216c-10.56,0-18-1.4-23.22-3.08,11.51-6.25,27.56-17,37.88-32.48A8,8,0,0,0,92,169.08c-.47-.27-43.91-26.34-44-96,16,13,45.25,33.17,78.67,38.79A8,8,0,0,0,136,104V88a32,32,0,0,1,9.6-22.92A30.94,30.94,0,0,1,167.9,56c12.66.16,24.49,7.88,29.44,19.21A8,8,0,0,0,204.67,80h16Z"></path>
                    </svg>
                  </div>
                </a>
                <a href="#">
                  <div className="text-[#93b2c8]">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24px" height="24px" fill="currentColor" viewBox="0 0 256 256">
                      <path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm8,191.63V152h24a8,8,0,0,0,0-16H136V112a16,16,0,0,1,16-16h16a8,8,0,0,0,0-16H152a32,32,0,0,0-32,32v24H96a8,8,0,0,0,0,16h24v63.63a88,88,0,1,1,16,0Z"></path>
                    </svg>
                  </div>
                </a>
                <a href="#">
                  <div className="text-[#93b2c8]">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24px" height="24px" fill="currentColor" viewBox="0 0 256 256">
                      <path d="M216,24H40A16,16,0,0,0,24,40V216a16,16,0,0,0,16,16H216a16,16,0,0,0,16-16V40A16,16,0,0,0,216,24Zm0,192H40V40H216V216ZM96,112v64a8,8,0,0,1-16,0V112a8,8,0,0,1,16,0Zm88,28v36a8,8,0,0,1-16,0V140a20,20,0,0,0-40,0v36a8,8,0,0,1-16,0V112a8,8,0,0,1,15.79-1.78A36,36,0,0,1,184,140ZM100,84A12,12,0,1,1,88,72,12,12,0,0,1,100,84Z"></path>
                    </svg>
                  </div>
                </a>
              </div>
              <p className="text-[#93b2c8] text-base font-normal leading-normal">© 2023 VoiceExam AI. All rights reserved.</p>
            </footer>
          </div>
        </footer>
      </div>
    </div>
  );
}
