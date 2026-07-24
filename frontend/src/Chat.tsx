import { useMutation } from "@tanstack/react-query";
import axios, { AxiosError } from "axios";
import { Download, Loader, Loader2, MessageSquare, Trash2, TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { type Message } from "./types";
import TokenUsageBar from "./components/TokenUsageBar";

export default function Chat() {
    // --- UI States ---
    const [chatInput, setChatInput] = useState("");
    const [chatMessages, setChatMessages] = useState<{ role: string, text: string }[]>([]);
    const [sessionId, setSessionId] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState<boolean>(false)
    const [error, setError] = useState<string | null>(null)
    const [tokensUsed, setTokensUsed] = useState<number>(0)


    // --- Refs ---
    const chatEndRef = useRef<HTMLDivElement>(null);


    useEffect(() => {
        (async () => {
            try {
                setIsLoading(true)
                let session_id = localStorage.getItem("session_id")
                if (!session_id || session_id.length === 0) {
                    session_id = crypto.randomUUID()
                    localStorage.setItem("session_id", session_id)
                }
                setSessionId(session_id)
                let chatData: Message[] = []
                const chatResp = await axios.get(`/api/chat/history/${session_id}`)
                if (chatResp.data.messages) {
                    chatData = chatResp.data.messages
                }
                const relevantMessages: { role: string, text: string }[] = []
                for (const msg of chatData) {
                    if (msg.type === "human") {
                        const role = "human"
                        relevantMessages.push({ role: role, text: msg.content })
                    } else if (msg.type === "ai" && msg.tool_calls?.length === 0) {
                        const role = "ai"
                        const token_usage = msg.response_metadata?.token_usage
                        if (token_usage) {
                            setTokensUsed(token_usage.total_tokens)
                        }
                        const resp = JSON.parse(msg.content) as { message: string, tools_used: string[] }
                        relevantMessages.push({ role, text: resp.message })
                    }
                }
                if (relevantMessages.length === 0) {
                    relevantMessages.push({
                        role: "ai", text: `
Hi,

How can I help you today ?`})
                }
                setChatMessages(relevantMessages)
                setIsLoading(false)
            } catch (err) {
                if (err instanceof AxiosError) {
                    const respData = err.response?.data as { detail: string, status_code: number }
                    if (respData.status_code !== 404) {
                        const errMsg = respData.detail || `${err}`
                        console.log(`chat History error: ${errMsg}`)
                        setError(errMsg)
                    }
                } else {
                    setError(`${err}`)
                    console.error(`${err}`)
                }
                setIsLoading(false)

            }
        })()

    }, [])

    function downloadChat() {
        let content = ""
        for (const msg of chatMessages) {
            content = `${content}\n===========================================\n${msg.role.toUpperCase()}: ${msg.text}`
        }
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `chat_123.txt`
        document.body.appendChild(link)
        link.click()

        document.body.removeChild(link)
        URL.revokeObjectURL(url) // free up memory allocation
    }

    // --- Auto Scroll ---
    useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatMessages]);

    const chatMutation = useMutation({
        mutationFn: async (msg: string) => {
            return (await axios.post(`/api/chat`, {
                message: msg,
                session_id: sessionId,
            })).data;
        },
        onSuccess: (data) => {
            setChatMessages(prev => [...prev, { role: 'bot', text: data.response }]);
            setTokensUsed(+data.total_tokens)
        },
        onError: (err: AxiosError) => {
            const respData = err.response?.data as { detail: string }
            const errMsg = respData.detail || `${err}`
            toast.error(`${errMsg}`)
            setChatMessages(prev => [...prev, { role: 'bot', text: `${errMsg}` }])
        }
    });

    const deleteChatMutation = useMutation({
        mutationFn: async () => {
            return (await axios.delete(`/api/chat/history/${sessionId}`))
        },
        onSuccess: () => {
            toast.success("Successfully cleared all chat history!!")
            localStorage.removeItem("session_id")
            setTokensUsed(0)
            setChatMessages([{
                role: "bot", text: `
Hi,

How can I help you today ?` }])
        },
        onError: (err) => {
            toast.error(`Failed to clear chat history: ${err}`)
        }
    })

    const handleSendMessage = (e: React.FormEvent) => {
        e.preventDefault();
        if (!chatInput.trim()) return;
        setChatMessages(prev => [...prev, { role: 'human', text: chatInput }]);
        chatMutation.mutate(chatInput);
        setChatInput("");
    };

    /* Error Screen */
    if (error) {
        console.log(`${error}`)
        return (
            <div
                className="h-[60vh] flex flex-col items-center justify-center gap-3"
            >
                <div className='p-4 rounded-2xl bg-white dark:bg-surface shadow-xs'>
                    <TriangleAlert
                        className='text-[#a52e69] dark:text-[#aa3c70]' size={32}
                    />
                </div>
                <h3
                    className='text-sm font-medium text-status-danger-text'
                >
                    Agent is not healthy
                </h3>
            </div>
        );
    }


    return (
        <section className="bg-surface border border-stroke rounded-2xl overflow-hidden shadow-xs flex flex-col h-[75vh] transition-colors duration-300">
            <header className="px-5 py-4 bg-surface-alt border-b border-stroke flex justify-between items-center">
                <div className='flex items-center gap-2.5'>
                    <MessageSquare size={16} className="text-brand" />
                    <h3 className="text-xs font-semibold tracking-wider text-text-main uppercase">Helpdesk</h3>
                </div>
                <TokenUsageBar tokenUsed={tokensUsed} />
                <div className='flex items-center gap-4'>
                    <div className='flex gap-1 items-center border-l border-stroke pl-4'>
                        <button
                            className='p-1.5 rounded-lg text-text-muted hover:text-text-main hover:bg-page transition-all disabled:opacity-20 cursor-pointer'
                            disabled={chatMessages.length < 2}
                            onClick={downloadChat}
                        >
                            <Download size={15} />
                        </button>
                        <button
                            disabled={deleteChatMutation.isPending || chatMessages.length < 2}
                            onClick={() => deleteChatMutation.mutate()}
                            className='p-1.5 rounded-lg text-text-muted disabled:opacity-20 hover:text-danger-text hover:bg-danger-bg transition-all cursor-pointer'
                        >
                            {
                                deleteChatMutation.isPending
                                && <Loader2 className='animate-spin' size={15} />
                                || <Trash2 size={15} />
                            }
                        </button>
                    </div>
                </div>
            </header>
            {/* Chat Display box */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-page/30">
                {(isLoading || deleteChatMutation.isPending)
                    && (<div className='h-full w-full flex flex-col items-center justify-center gap-2'>
                        <Loader className='animate-spin [animation-duration:2s] text-brand' size={24} />
                        <span className='text-xs font-medium text-text-muted animate-pulse'>{isLoading && "Loading..." || "Deleting..."}</span>
                    </div>)}
                {!isLoading && chatMessages.map((m, i) => (
                    <div key={i} className={`flex ${m.role === 'human' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] p-3.5 rounded-2xl text-sm border shadow-xs transition-colors ${m.role === 'human'
                            ? 'bg-brand text-white dark:text-page border-transparent rounded-br-xs'
                            : 'bg-surface text-text-main border-stroke rounded-bl-xs'}`}>
                            <div
                                className={`prose max-w-none wrap-break-word text-sm ${m.role === 'human' ? 'prose-invert' : 'dark:prose-invert'}`}
                            >
                                <Markdown remarkPlugins={[remarkGfm]}>
                                    {m.text}
                                </Markdown>
                            </div>
                            <div
                                className={`text-[9px] mt-1.5 uppercase tracking-wider opacity-60 font-bold ${m.role === 'human'
                                    ? 'text-right text-white/80' : 'text-left text-text-ghost'}`}
                            >
                                {m.role === 'human' ? 'Commander' : 'System_AI'}
                            </div>
                        </div>
                    </div>
                ))}

                {chatMutation.isPending
                    && (
                        <div className="flex items-center gap-2 bg-surface px-4 py-3 rounded-xl border border-stroke w-max shadow-xs">
                            <Loader2 className="animate-spin text-brand" size={14} />
                            <span className="text-xs font-medium text-text-muted">Working...</span>
                        </div>
                    )}
                <div ref={chatEndRef} />
            </div>

            {/* Send Message footer */}
            <footer className="p-4 bg-surface-alt border-t border-stroke">
                <form onSubmit={handleSendMessage} className="flex gap-2">
                    <input
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        placeholder="Query protocol..."
                        className="flex-1 bg-surface border border-stroke rounded-xl px-4 py-2.5 text-sm text-text-main placeholder-text-ghost focus:border-brand focus:ring-1 focus:ring-brand outline-none transitiona-all"
                    />
                    <button
                        type="submit"
                        className="bg-brand hover:bg-brand-hover text-white dark:text-page px-5 rounded-xl transition-all font-semibold text-sm shadow-xs cursor-pointer active:scale-95"
                    >
                        Send
                    </button>
                </form>
            </footer>

        </section>
    )
}