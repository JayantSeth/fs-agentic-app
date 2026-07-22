import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import Chat from "./Chat"
import { Toaster } from "react-hot-toast";
import Navbar from "./Navbar";
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

const queryClient = new QueryClient();

function App() {

  return (
    <QueryClientProvider client={queryClient}>
      <Toaster
        position="top-right"
        toastOptions={{
          className: 'dark:!bg-[#1E2640] dark:!text-[#F1F5F9] !bg-white !text-[#1E293B] !border !border-[#E2E8F0] dark:!border-[#1E293B] !rounded-xl !shadow-md !font-medium !text-sm',
          duration: 6000,
          success: {
            iconTheme: {
              primary: '#10B981',
              secondary: '#FFFFFF',
            },
          },
          error: {
            iconTheme: {
              primary: '#EF4444',
              secondary: '#FFFFFF'
            },
          },
        }}
      />
      <Router>
        {/* Dynamic Global background frame */}
        <div className="min-h-screen bg-page dark:bg-page text-main dark:text-[#E2E8F0] font-sans flex flex-col transition-colors duration-300">

          {/* Global Top Navigation */}
          <Navbar />

          {/* Main Content Area : Body Wrapper */}
          <main className="flex-1 w-full max-w-6xl mx-auto px-4 md:px-6 py-8">
            <Routes>

              <Route path="/chat" element={<Chat />} />       
            </Routes>
          </main>

        </div>
      </Router>
    </QueryClientProvider>
  )
}

export default App
