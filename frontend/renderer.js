const API_BASE = 'http://localhost:8000/api';

// State
let currentProjectId = null;

// DOM Elements
const projectSelector = document.getElementById('project-selector');
const newProjectBtn = document.getElementById('new-project-btn');
const newProjectModal = document.getElementById('new-project-modal');
const newProjectForm = document.getElementById('new-project-form');
const cancelProjectBtn = document.getElementById('cancel-project-btn');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const navItems = document.querySelectorAll('.nav-item');
const tabContents = document.querySelectorAll('.tab-content');
const statusText = document.getElementById('status-text');

// API Functions
async function api(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'APIエラー');
        }
        return response.json();
    } catch (error) {
        console.error('API Error:', error);
        setStatus(`エラー: ${error.message}`);
        throw error;
    }
}

// Project Functions
async function loadProjects() {
    try {
        const projects = await api('/projects');
        projectSelector.innerHTML = '<option value="">プロジェクトを選択...</option>';
        projects.forEach(p => {
            const option = document.createElement('option');
            option.value = p.project_id;
            option.textContent = p.project_name;
            projectSelector.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load projects:', error);
    }
}

async function createProject(name, citationStyle) {
    try {
        const project = await api('/projects', {
            method: 'POST',
            body: JSON.stringify({
                project_name: name,
                citation_style: citationStyle
            })
        });
        await loadProjects();
        projectSelector.value = project.project_id;
        currentProjectId = project.project_id;
        setStatus(`プロジェクト "${name}" を作成しました`);
        return project;
    } catch (error) {
        alert(error.message);
    }
}

// Chat Functions
async function sendMessage(content) {
    if (!currentProjectId) {
        alert('プロジェクトを選択してください');
        return;
    }

    // Add user message to UI
    addMessage('user', content);
    chatInput.value = '';
    setStatus('処理中...');

    try {
        const response = await api('/chat', {
            method: 'POST',
            body: JSON.stringify({
                project_id: currentProjectId,
                content: content
            })
        });

        // Add assistant message
        addMessage('assistant', response.content);

        // Show intent and plan if available
        if (response.intent) {
            console.log('Intent:', response.intent);
        }
        if (response.plan) {
            console.log('Plan:', response.plan);
        }

        setStatus('準備完了');
    } catch (error) {
        addMessage('assistant', `エラーが発生しました: ${error.message}`);
        setStatus('エラー');
    }
}

function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `<p>${content}</p>`;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function loadChatHistory() {
    if (!currentProjectId) return;

    try {
        const history = await api(`/chat/${currentProjectId}/history`);
        chatMessages.innerHTML = '';
        history.forEach(msg => {
            addMessage(msg.role, msg.content);
        });
        if (history.length === 0) {
            addMessage('assistant', 'こんにちは！論文検索をお手伝いします。検索したいテーマを入力してください。');
        }
    } catch (error) {
        console.error('Failed to load chat history:', error);
    }
}

// UI Functions
function setStatus(text) {
    statusText.textContent = text;
}

function switchTab(tabId) {
    navItems.forEach(item => {
        item.classList.toggle('active', item.dataset.tab === tabId);
    });
    tabContents.forEach(content => {
        content.classList.toggle('active', content.id === tabId);
    });
}

// Event Listeners
projectSelector.addEventListener('change', (e) => {
    currentProjectId = e.target.value || null;
    if (currentProjectId) {
        loadChatHistory();
        setStatus('プロジェクトを選択しました');
    }
});

newProjectBtn.addEventListener('click', () => {
    newProjectModal.classList.remove('hidden');
});

cancelProjectBtn.addEventListener('click', () => {
    newProjectModal.classList.add('hidden');
});

newProjectForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('project-name').value;
    const style = document.getElementById('citation-style').value;
    await createProject(name, style);
    newProjectModal.classList.add('hidden');
    newProjectForm.reset();
});

sendBtn.addEventListener('click', () => {
    const content = chatInput.value.trim();
    if (content) {
        sendMessage(content);
    }
});

chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        const content = chatInput.value.trim();
        if (content) {
            sendMessage(content);
        }
    }
});

navItems.forEach(item => {
    item.addEventListener('click', () => {
        switchTab(item.dataset.tab);
    });
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();
    setStatus('準備完了');
});
