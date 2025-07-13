import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import apiClient from '../api/client';

const ProjectList = ({ projects, onSelectProject, selectedProjectId }) => (
    <aside>
        <h3>Projects</h3>
        <nav>
            <ul>
                {projects.map(p => (
                    <li key={p.id}>
                        <a
                            href="#"
                            onClick={(e) => { e.preventDefault(); onSelectProject(p); }}
                            aria-current={selectedProjectId === p.id ? 'page' : undefined}
                        >
                            {p.name}
                        </a>
                    </li>
                ))}
            </ul>
        </nav>
        <hr />
        {/* We'll add the "Create Project" form here later */}
    </aside>
);

const ChatPage = () => {
    const { user, logout } = useAuth();
    const [projects, setProjects] = useState([]);
    const [selectedProject, setSelectedProject] = useState(null);
    const [error, setError] = useState('');

    useEffect(() => {
        const fetchProjects = async () => {
            try {
                const response = await apiClient.get('/projects/');
                setProjects(response.data);
                // Automatically select the first project if one isn't already selected
                if (response.data.length > 0 && !selectedProject) {
                    setSelectedProject(response.data[0]);
                }
            } catch (err) {
                setError('Failed to fetch projects.');
                console.error(err);
            }
        };
        fetchProjects();
    }, [selectedProject]);

    return (
        <main className="container-fluid">
            <nav>
                <ul>
                    <li><strong>Chat with Your Docs</strong></li>
                </ul>
                <ul>
                    <li>Welcome, {user?.full_name || user?.username}!</li>
                    <li><a href="#" role="button" onClick={logout}>Logout</a></li>
                </ul>
            </nav>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 3fr', gap: '2rem' }}>
                <ProjectList
                    projects={projects}
                    onSelectProject={setSelectedProject}
                    selectedProjectId={selectedProject?.id}
                />

                <article>
                    {selectedProject ? (
                        <div>
                            <h2>Project: {selectedProject.name}</h2>
                            <p>LLM: {selectedProject.llm_provider} ({selectedProject.llm_model_name})</p>
                            <hr />
                            <p>The chat interface and document manager for this project will go here.</p>
                        </div>
                    ) : (
                        <p>Please select a project from the sidebar, or create a new one.</p>
                    )}
                    {error && <p style={{ color: 'red' }}>{error}</p>}
                </article>
            </div>
        </main>
    );
};

export default ChatPage;