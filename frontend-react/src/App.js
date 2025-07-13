import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import ChatPage from './pages/ChatPage';

function AppContent() {
    const { user, loading, setToken } = useAuth();

    React.useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const oauthToken = params.get('token');

        if (oauthToken) {
            localStorage.setItem('authToken', oauthToken);
            setToken(oauthToken);
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }, [setToken]);

    if (loading) {
        return <progress></progress>;
    }

    if (user) {
        return <ChatPage />;
    }

    return <LoginPage />;
}

function App() {
    return (
        <AuthProvider>
            <AppContent />
        </AuthProvider>
    );
}

export default App;