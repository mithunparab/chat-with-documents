import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import apiClient from '../api/client';

const styles = {
    container: { display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' },
    formContainer: { padding: '2rem', border: '1px solid #ccc', borderRadius: '8px', marginRight: '2rem' },
    input: { display: 'block', marginBottom: '1rem', padding: '0.5rem', width: '200px' },
    button: { padding: '0.5rem 1rem', width: '100%' },
    linkButton: { background: 'none', border: '1px solid #4285F4', color: '#4285F4', width: '100%', padding: '0.5rem 1rem', marginTop: '1rem', cursor: 'pointer' }
};

const LoginPage = () => {
    const { login } = useAuth();
    const [loginUsername, setLoginUsername] = useState('');
    const [loginPassword, setLoginPassword] = useState('');
    const [signupUsername, setSignupUsername] = useState('');
    const [signupEmail, setSignupEmail] = useState('');
    const [signupPassword, setSignupPassword] = useState('');
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');
        try {
            await login(loginUsername, loginPassword);
        } catch (err) {
            setError('Login failed. Please check your credentials.');
        }
    };

    const handleSignup = async (e) => {
        e.preventDefault();
        setError('');
        setMessage('');
        try {
            await apiClient.post('/auth/signup', {
                username: signupUsername,
                email: signupEmail,
                password: signupPassword,
            });
            setMessage('Signup successful! Please log in.');
        } catch (err) {
            setError(err.response?.data?.detail || 'Signup failed.');
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.formContainer}>
                <h2>Login</h2>
                <form onSubmit={handleLogin}>
                    <input type="text" placeholder="Username" value={loginUsername} onChange={(e) => setLoginUsername(e.target.value)} style={styles.input} />
                    <input type="password" placeholder="Password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} style={styles.input} />
                    <button type="submit" style={styles.button}>Login</button>
                </form>
                <hr style={{ margin: '2rem 0' }} />
                <a href="/api/v1/auth/login/google" style={{ textDecoration: 'none' }}>
                    <button style={styles.linkButton}>Sign in with Google</button>
                </a>
            </div>

            <div style={styles.formContainer}>
                <h2>Sign Up</h2>
                <form onSubmit={handleSignup}>
                    <input type="text" placeholder="Username" value={signupUsername} onChange={(e) => setSignupUsername(e.target.value)} style={styles.input} />
                    <input type="email" placeholder="Email" value={signupEmail} onChange={(e) => setSignupEmail(e.target.value)} style={styles.input} />
                    <input type="password" placeholder="Password" value={signupPassword} onChange={(e) => setSignupPassword(e.target.value)} style={styles.input} />
                    <button type="submit" style={styles.button}>Sign Up</button>
                </form>
            </div>
            {error && <p style={{ color: 'red' }}>{error}</p>}
            {message && <p style={{ color: 'green' }}>{message}</p>}
        </div>
    );
};

export default LoginPage;