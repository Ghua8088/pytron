import { useState, useEffect, useRef } from 'react'
import pytron from 'pytron-client'
import './App.css'

const presets = [
  {
    label: 'Explain Pytron',
    prompt: 'What are the key components of Pytron and how do they work together?'
  },
  {
    label: 'Generate creative idea',
    prompt: 'Help me brainstorm a creative code-focused challenge for a weekend project.'
  },
  {
    label: 'Debugging tips',
    prompt: 'What are your tips for debugging native + web hybrid apps?'
  }
]

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [connected, setConnected] = useState(false)
  const [sending, setSending] = useState(false)
  const sendingRef = useRef(false)
  const messagesRef = useRef(null)

  useEffect(() => {
    if (pytron) setConnected(true)
  }, [])

  useEffect(() => {
    const node = messagesRef.current
    if (node) node.scrollTop = node.scrollHeight
  }, [messages, sending])

  async function send() {
    if (!input.trim() || sendingRef.current) return
    const text = input.trim()
    setInput('')
    const time = new Date().toISOString()
    setMessages((m) => [...m, { sender: 'you', text, time }])
    sendingRef.current = true
    setSending(true)

    try {
      const reply = await pytron.send_message(text)
      setMessages((m) => [...m, { sender: 'bot', text: String(reply), time: new Date().toISOString() }])
    } catch (err) {
      setMessages((m) => [...m, { sender: 'bot', text: `Echo (no backend): ${text}`, time: new Date().toISOString() }])
    } finally {
      sendingRef.current = false
      setSending(false)
    }
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const lastMessage = messages[messages.length - 1]
  const history = [...messages].reverse().slice(0, 5)
  const lastSeen = lastMessage ? new Date(lastMessage.time).toLocaleTimeString() : '—'

  function applyPreset(preset) {
    setInput(preset.prompt)
  }

  function clearHistory() {
    setMessages([])
  }

  return (
    <div className="chat-shell">
      <aside className="sidebar">
        <div className="sidebar-top">
          <p className="sidebar-title">History &amp; Quick Actions</p>
          <button className="ghost" onClick={clearHistory}>
            Clear history
          </button>
          <button onClick={pytron.minimize()}>minimize</button>
        </div>
        <div className="history-list">
          {history.length === 0 && <p className="empty">No activity yet — send the first message.</p>}
          {history.map((item, index) => (
            <button
              key={`${item.time}-${index}`}
              className="history-row"
              onClick={() => setInput(item.text)}
            >
              <span className="history-avatar">{item.sender === 'you' ? 'You' : 'Bot'}</span>
              <div>
                <p className="history-text">{item.text}</p>
                <small>{new Date(item.time).toLocaleTimeString()}</small>
              </div>
            </button>
          ))}
        </div>
        <div className="sidebar-bottom">
          <div>
            <p className="sidebar-label">Last seen</p>
            <strong>{lastSeen}</strong>
          </div>
          <div>
            <p className="sidebar-label">Messages</p>
            <strong>{messages.length}</strong>
          </div>
        </div>
        <div className="presets">
          <p className="sidebar-label">Jump start</p>
          <div className="preset-grid">
            {presets.map((preset) => (
              <button key={preset.label} onClick={() => applyPreset(preset)}>
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      </aside>

      <section className="chat-area">
        <header>
          <div>
            <h1>Pytron Assistant</h1>
            <p className="status">Status: {connected ? 'Online' : 'Offline (guest preview)'}</p>
          </div>
          <div className="header-badge">Ollama Model</div>
        </header>

        <main className="messages" ref={messagesRef}>
          {messages.map((m, i) => (
            <div key={i} className={`message ${m.sender}`}>
              <div className="meta">
                <span className="sender">{m.sender === 'you' ? 'You' : 'Bot'}</span>
                <span className="time">{m.time ? new Date(m.time).toLocaleTimeString() : ''}</span>
              </div>
              <div className="text">{m.text}</div>
            </div>
          ))}
          {sending && (
            <div className="message bot typing">
              <div className="meta">
                <span className="sender">Bot</span>
              </div>
              <div className="text">Thinking…</div>
            </div>
          )}
        </main>

        <footer>
          <textarea
            disabled={sending}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            placeholder={sending ? 'Sending…' : 'Ask anything to your Ollama assistant'}
          />
          <button onClick={send} disabled={sending || !input.trim()}>
            {sending ? 'Sending…' : 'Send message'}
          </button>
        </footer>
      </section>
    </div>
  )
}

export default App
