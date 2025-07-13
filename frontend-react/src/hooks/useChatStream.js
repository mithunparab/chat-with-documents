import { useState, useEffect, useRef } from 'react';

export const useChatStream = (projectId) => {
    const [messages, setMessages] = useState([]);
    const [sources, setSources] = useState([]);
    const [error, setError] = useState(null);

    const eventSourceRef = useRef(null);

    const sendMessage = (query, chatId) => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }

        setMessages(prev => [...prev, { role: 'user', content: query }]);
        setSources([]);

        const token = localStorage.getItem('authToken');

        const streamResponse = async () => {
            const response = await fetch(`/api/v1/chat/stream/${projectId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ query, chat_id: chatId }),
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let currentAssistantMessage = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n\n');

                for (const line of lines) {
                    if (line.includes('event: start')) {
                    } else if (line.includes('event: sources')) {
                        const data = JSON.parse(line.split('data: ')[1]);
                        setSources(data);
                    } else if (line.includes('event: token')) {
                        const tokenData = JSON.parse(line.split('data: ')[1]);
                        currentAssistantMessage += tokenData;
                    }
                }
            }
            setMessages(prev => [...prev, { role: 'assistant', content: currentAssistantMessage }]);
        };

        streamResponse().catch(setError);
    };

    return { messages, sources, error, sendMessage };
};