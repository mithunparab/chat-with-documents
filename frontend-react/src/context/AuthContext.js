import React, { createContext, useState, useContext, useEffect } from 'react';
import apiClient from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(() => localStorage.getItem('authToken'));
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (token) {
            localStorage.setItem('authToken', token);
            apiClient.get('/auth/users/me')
                .then(response => setUser(response.data))
                .catch(() => {
                    logout();
                });
        } else {
            localStorage.removeItem('authToken');
        }
    }, [token]);

    const login = async (username, password) => {
        const response = await apiClient.post('/auth/token', new URLSearchParams({ username, password }));
        setToken(response.data.access_token);
    };

    const logout = () => {
        setToken(null);
        setUser(null);
    };

    const value = { user, token, loading, login, logout, setToken };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);