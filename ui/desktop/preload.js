const { contextBridge } = require('electron');

// Expose a minimal API; network calls go directly via fetch
contextBridge.exposeInMainWorld('nova', {
  sendPrompt: async (text) => {
    const res = await fetch('http://127.0.0.1:8000/api/prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: text })
    });
    return res.json();
  },
  confirmActions: async (actions) => {
    const res = await fetch('http://127.0.0.1:8000/api/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actions })
    });
    return res.json();
  },
  speak: (text) => {
    const utter = new SpeechSynthesisUtterance(text);
    speechSynthesis.speak(utter);
  }
});
