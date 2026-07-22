import { Cog, Moon, Sun, MessagesSquare } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useDarkMode } from "./hooks/useDarkMode";

export default function Navbar() {
    const { theme, toggleTheme } = useDarkMode();

    return <nav className="sticky top-0 z-50 backdrop-blur-md bg-page/80 dark:bg-page/80 border-b border-[#E2E8F0] dark:border-[#1E293B] px-6 py-4 transition-colors duration-300">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
            {/* Logo Section */}
            <div className="flex items-center gap-3 group">
                <div className="p-2 rounded-xl bg-indigo-50 dark:bg-sky-950/40 text-[#6366F1] dark:text-[#38BDF8] transition-colors duration-300">
                    <Cog className="animate-[spin_8s_linear_infinite]" size={22} />
                </div>
                <span className="font-semibold tracking-tight text-main dark:text-[#F1F5F9] text-lg">File System Agent</span>
            </div>
            <div className="flex gap-2 items-center">

                {/* Navigation Links */}
                <div className="flex gap-2">
                    <NavLink
                        to="/chat"
                        className={({ isActive }) =>
                            `flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium uppercase tracking-wide transition-all duration-200 ${isActive ? 'bg-white dark:bg-surface text-[#6366F1] dark:text-[#38BDF8] shadow-sm ring-1 ring-black/5 dark:ring-white/5'
                                : 'text-[#64748B] dark:text-[#94A3B8] hover:text-main dark:hover:text-[#F1F5F9] hover:bg-[#E2E8F0]/50 dark:hover:bg-surface/50'}`
                        }
                    >
                        <MessagesSquare size={16} />
                        <span>
                            Chat
                        </span>
                    </NavLink>
                </div>
                {/* Calming Divider */}
                <div className="h-6 w-px bg-[#E2E8F0] dark:bg-[#1E293B]" />
                {/* Theme toggle button */}
                <button
                    onClick={toggleTheme}
                    aria-label="Toggle theme"
                    className="relative w-10 h-10 p-2.5 rounded-xl bg-white dark:bg-surface border border-[#E2E8F0] dark:border-[#1E293B] text-[#64748B] dark:text-[#94A3B8] hover:text-main dark:hover:text-[#F1F5F9] shadow-xs hover:shadow-sm hover:cursor-pointer active:scale-95 transition-all duration-200"
                    title="Theme"
                >
                    {/* Sun Icon Container */}
                    <div className={`absolute inset-0 flex items-center justify-center transition-all duration-2000 ease-[cubic-bezier(0.34,1.56,0.64,1)] ${theme === "light"
                        ? "translate-y-0 opacity-100 scale-100" // Active
                        : "-translate-y-8 opacity-0 scale-75" // Exiting: flies up and out when switching to dark
                        }`}
                    >
                        {/* If it's dark mode, we prepare the sun at the bottom so it can rise up next time */}
                        <Sun size={18} className={`text-amber-400 transition-transform duration-2000 ${theme === "dark" ? "translate-y-8" : "translate-y-0"}`} />
                    </div>
                    {/* Moon Icon container */}
                    <div
                        className={`absolute inset-0 flex items-center justify-center transition-all duration-2000 ease-[cubic-bezier(0.34,1.56,0.64,1)] ${theme === "dark"
                            ? "translate-y-0 opacity-100 scale-100"       // Active: centered in Dark Mode
                            : "-translate-y-8 opacity-0 scale-75"       // Exiting: flies UP and out when switching to Light
                            }`}
                    >
                        {/* If it's light mode, we prepare the moon at the BOTTOM so it can rise up next time */}
                        <Moon size={18} className={`text-indigo-500 transition-transform duration-2000  ${theme === "light" ? "translate-y-8" : "translate-y-0"}`} />
                    </div>
                </button>
            </div>
        </div>
    </nav>

}