type TokenUsageBarProps = {
    tokenUsed: number
}

const MAX_TOTAL_TOKENS = 120000;

export default function TokenUsageBar({ tokenUsed }: TokenUsageBarProps) {
    const tokensUsedInPercentage = (tokenUsed / MAX_TOTAL_TOKENS) * 100;
    let bg_class = "bg-green-600";
    if (tokensUsedInPercentage > 25) {
        bg_class = "bg-blue-600"
    }
    if (tokensUsedInPercentage > 70) {
        bg_class = "bg-red-600"
    }
    return (

        <div className={`w-[40%] flex gap-2 justify-center items-center`} title={`${tokenUsed}/${MAX_TOTAL_TOKENS}`}>
            <h3 className='text-[10px] font-bold uppercase tracking-[0.3em] text-red-500/80'>Token Usage:</h3>
            <div className='w-[50%] bg-amber-100 rounded-full h-3 overflow-hidden'>
                <div className={`h-full ${bg_class} transition-all duration-300`} style={{ width: `${tokensUsedInPercentage}%` }}>

                </div>
            </div>
        </div>
    )
}