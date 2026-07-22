export type Message = {
    role: string
    content: string
    tool_calls: {}[] | null
}