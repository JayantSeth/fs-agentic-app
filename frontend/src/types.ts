export type ResponseMetadata = {
        token_usage: {
            completion_tokens: number,
            prompt_tokens: number,
            total_tokens: number
        }
    }

export type Message = {
    type: string
    content: string
    tool_calls: {}[] | null
    response_metadata: ResponseMetadata | null
}