import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCheck,
  Clock,
  Image as ImageIcon,
  Loader2,
  Mic,
  MoreVertical,
  RefreshCw,
  Send,
  ShieldAlert,
  Square,
} from 'lucide-react'
import { getMessages, sendMessage } from '../api/chat.js'
import { getTask } from '../api/tasks.js'
import { useAuthStore } from '../store/authStore.js'
import { API_BASE_URL } from '../api/axios.js'
import EmptyState from '../components/EmptyState.jsx'
import ReportUserModal from '../components/ReportUserModal.jsx'

function formatTime(value) {
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatDate(value) {
  return new Date(value).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })
}

function getQuickReplies(status) {
  if (status === 'IN_PROGRESS') {
    return ['How is it going?', 'Need any info from me?', 'Estimated completion time?']
  }
  if (status === 'COMPLETED') {
    return ['Thanks for the help', 'Please confirm delivery', 'I have left a review']
  }
  return ['What is your availability?', 'I will confirm shortly', 'Can you share an update when done?']
}

function MessageStatus({ message, mine }) {
  if (!mine) return null
  const isLocal = String(message.id).startsWith('local-')
  if (message.is_read) {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-100">
        <CheckCheck size={13} />
        Opened
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 text-[11px] text-emerald-100">
      {isLocal ? <Clock size={13} /> : <Check size={13} />}
      {isLocal ? 'Sending' : 'Sent'}
    </span>
  )
}

export default function ChatPage() {
  const { taskId } = useParams()
  const numericTaskId = Number(taskId)
  const user = useAuthStore((state) => state.user)
  const accessToken = useAuthStore((state) => state.accessToken)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [isFallbackPolling, setIsFallbackPolling] = useState(false)
  const [typingName, setTypingName] = useState('')
  const [reconnectKey, setReconnectKey] = useState(0)
  const [showQuickReplies, setShowQuickReplies] = useState(false)
  const [isUploadingAttachment, setIsUploadingAttachment] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isReportOpen, setIsReportOpen] = useState(false)
  const socketRef = useRef(null)
  const bottomRef = useRef(null)
  const typingTimeoutRef = useRef(null)
  const imageInputRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

  const taskQuery = useQuery({
    queryKey: ['task', numericTaskId],
    queryFn: () => getTask(numericTaskId),
  })

  const messagesQuery = useQuery({
    queryKey: ['chat-messages', numericTaskId],
    queryFn: () => getMessages(numericTaskId),
    refetchInterval: isFallbackPolling ? 5000 : 15000,
  })

  useEffect(() => {
    if (messagesQuery.data) {
      setMessages(messagesQuery.data)
    }
  }, [messagesQuery.data])

  useEffect(() => {
    if (!accessToken || !numericTaskId) return undefined

    const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL
      || API_BASE_URL.replace(/^https/, 'wss').replace(/^http/, 'ws').replace(/\/api\/v1\/?$/, '')
    const socket = new WebSocket(`${wsBaseUrl}/ws/chat/${numericTaskId}/?token=${accessToken}`)
    socketRef.current = socket

    socket.onopen = () => setIsFallbackPolling(false)
    socket.onerror = () => setIsFallbackPolling(true)
    socket.onclose = () => setIsFallbackPolling(true)
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data)
      if (payload.type === 'typing') {
        setTypingName(payload.is_typing ? payload.sender_name : '')
        window.clearTimeout(typingTimeoutRef.current)
        typingTimeoutRef.current = window.setTimeout(() => setTypingName(''), 2500)
        return
      }

      setMessages((current) => {
        if (payload.client_message_id) {
          return current.map((message) =>
            message.client_message_id === payload.client_message_id
              ? { ...payload, sender: payload.sender_id }
              : message,
          )
        }
        if (current.some((message) => message.id === payload.id)) return current
        return [...current, { ...payload, sender: payload.sender_id }]
      })
    }

    return () => {
      socket.close()
      window.clearTimeout(typingTimeoutRef.current)
    }
  }, [accessToken, numericTaskId, reconnectKey])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, typingName])

  const task = taskQuery.data
  const quickReplies = getQuickReplies(task?.status)
  const otherParty = useMemo(() => {
    if (!task || !user) return { id: null, name: 'Task chat', photo: '' }
    if (task.client_id === user.id) {
      return { id: task.assigned_tasker_id, name: task.assigned_tasker || 'Assigned tasker', photo: '' }
    }
    return { id: task.client_id, name: task.client || 'Task client', photo: '' }
  }, [task, user])

  const handleTyping = (value) => {
    setDraft(value)
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'typing', is_typing: Boolean(value.trim()) }))
    }
  }

  const useQuickReply = (reply) => {
    setDraft(reply)
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'typing', is_typing: true }))
    }
  }

  const handleSend = async (event) => {
    event.preventDefault()
    const content = draft.trim()
    if (!content) return

    const clientMessageId = `local-${Date.now()}`
    const optimisticMessage = {
      id: clientMessageId,
      client_message_id: clientMessageId,
      sender: user.id,
      sender_id: user.id,
      sender_name: user.full_name,
      content,
      timestamp: new Date().toISOString(),
      is_read: false,
    }
    setMessages((current) => [...current, optimisticMessage])
    setDraft('')
    window.navigator?.vibrate?.(35)

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'message', content, client_message_id: clientMessageId }))
      socketRef.current.send(JSON.stringify({ type: 'typing', is_typing: false }))
      return
    }

    const savedMessage = await sendMessage(numericTaskId, { content })
    setMessages((current) => current.map((message) => (message.id === clientMessageId ? savedMessage : message)))
  }

  const sendAttachment = async ({ file, type }) => {
    if (!file) return
    setIsUploadingAttachment(true)
    try {
      const payload = new FormData()
      payload.append('content', type === 'image' ? 'Photo attachment' : 'Voice note')
      payload.append(type === 'image' ? 'image' : 'voice_note', file)
      const savedMessage = await sendMessage(numericTaskId, payload)
      setMessages((current) => [...current, savedMessage])
      messagesQuery.refetch()
      window.navigator?.vibrate?.(35)
    } finally {
      setIsUploadingAttachment(false)
    }
  }

  const handleImageSelected = (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    sendAttachment({ file, type: 'image' })
  }

  const startRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      window.alert('Voice notes are not supported in this browser.')
      return
    }

    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      window.alert('Microphone permission is needed to record a voice note.')
      return
    }
    audioChunksRef.current = []
    const recorder = new MediaRecorder(stream)
    mediaRecorderRef.current = recorder

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) audioChunksRef.current.push(event.data)
    }
    recorder.onstop = () => {
      stream.getTracks().forEach((track) => track.stop())
      const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' })
      const file = new File([blob], `voice-note-${Date.now()}.webm`, { type: blob.type })
      setIsRecording(false)
      sendAttachment({ file, type: 'voice_note' })
    }

    recorder.start()
    setIsRecording(true)
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }

  if (taskQuery.isLoading || messagesQuery.isLoading) {
    return <div className="flex justify-center py-12 text-primary"><Loader2 className="animate-spin" size={32} /></div>
  }

  return (
    <section className="relative mx-auto flex h-[calc(100vh-140px)] max-w-5xl flex-col overflow-hidden rounded-lg border border-slate-200 bg-[#071c15] shadow-sm">
      <img
        src="https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=1800&q=85"
        alt=""
        className="absolute inset-0 h-full w-full object-cover opacity-75"
      />
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(2,10,7,0.78),rgba(2,10,7,0.58)_34%,rgba(248,250,252,0.82)_70%,rgba(248,250,252,0.92))]" />

      <header className="relative flex items-center gap-4 border-b border-white/15 bg-white/90 px-4 py-3 backdrop-blur">
        <Link to={`/tasks/${numericTaskId}`} className="rounded-md p-2 hover:bg-slate-100" aria-label="Back to task">
          <ArrowLeft size={20} />
        </Link>
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-emerald-100 text-primary">
          {otherParty.photo ? <img src={otherParty.photo} alt="" className="h-full w-full rounded-full object-cover" /> : <ImageIcon size={20} />}
        </div>
        <div className="min-w-0">
          <h1 className="truncate font-semibold text-text-dark">{otherParty.name}</h1>
          <Link to={`/tasks/${numericTaskId}`} className="truncate text-sm text-primary">
            {task?.title ?? 'Task details'}
          </Link>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {isFallbackPolling ? (
            <button
              type="button"
              onClick={() => {
                setReconnectKey((key) => key + 1)
                messagesQuery.refetch()
              }}
              className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700"
            >
              <RefreshCw size={13} />
              Reconnect
            </button>
          ) : (
            <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">Live</span>
          )}
          <button
            type="button"
            onClick={() => setIsReportOpen(true)}
            className="rounded-md p-2 text-text-muted hover:bg-slate-100"
            aria-label="Report user"
            title="Report user"
          >
            <MoreVertical size={18} />
          </button>
        </div>
      </header>

      <div className="relative border-b border-white/15 bg-white/85 px-4 py-3 backdrop-blur">
        <div className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-center">
          <div className="rounded-lg border border-emerald-100 bg-emerald-50/90 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-primary">{task?.status ?? 'Task'}</span>
              <span className="text-sm font-semibold text-text-dark">{task?.title}</span>
              <span className="text-sm text-text-muted">KES {task?.budget_min} - {task?.budget_max}</span>
            </div>
            <p className="mt-1 text-xs text-emerald-800">
              Keep exact room details, payment, and task changes inside TaskiT so there is a clear record if support is needed.
            </p>
          </div>
          <Link to={`/tasks/${numericTaskId}`} className="inline-flex justify-center rounded-md border border-primary px-3 py-2 text-sm font-semibold text-primary">
            View Task Details
          </Link>
        </div>
      </div>

      <div className="relative flex-1 overflow-y-auto px-4 py-5">
        <div className="mx-auto grid max-w-3xl gap-3">
          <div className="rounded-lg border border-amber-200 bg-amber-50/95 p-3 text-sm text-amber-900">
            <div className="flex gap-2">
              <ShieldAlert size={18} className="mt-0.5 shrink-0" />
              <p>
                Be respectful, do not harass, threaten, share unsafe content, or move payment outside TaskiT.
                Report safety concerns from the task page.
              </p>
            </div>
          </div>
          {messages.length === 0 && (
            <EmptyState title="No messages yet. Send the first one." />
          )}
          {messages.map((message, index) => {
            const mine = (message.sender_id ?? message.sender) === user?.id
            const previous = messages[index - 1]
            const showDate = !previous || formatDate(previous.timestamp) !== formatDate(message.timestamp)
            return (
              <div key={message.id} className="grid gap-2">
                {showDate && (
                  <div className="flex items-center gap-3 py-2 text-xs font-semibold text-text-muted">
                    <div className="h-px flex-1 bg-slate-200" />
                    {formatDate(message.timestamp)}
                    <div className="h-px flex-1 bg-slate-200" />
                  </div>
                )}
                <article
                  role="article"
                  aria-label={`Message from ${message.sender_name ?? (mine ? 'you' : otherParty.name)} at ${formatTime(message.timestamp)}`}
                  className={`flex ${mine ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[82%] rounded-2xl px-4 py-2 shadow-sm sm:max-w-[70%] ${mine ? 'rounded-br-sm bg-primary text-white' : 'rounded-bl-sm bg-white text-text-dark'}`}>
                    {!mine && <p className="mb-1 text-xs font-semibold text-primary">{message.sender_name ?? otherParty.name}</p>}
                    {message.image_url && (
                      <a href={message.image_url} target="_blank" rel="noreferrer" className="mb-2 block overflow-hidden rounded-lg">
                        <img src={message.image_url} alt="Chat attachment" className="max-h-72 w-full object-cover" />
                      </a>
                    )}
                    {message.voice_note_url && (
                      <audio controls src={message.voice_note_url} className="mb-2 w-full max-w-xs" />
                    )}
                    {message.content && <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>}
                    <div className={`mt-1 flex items-center justify-end gap-2 ${mine ? 'text-emerald-100' : 'text-text-muted'}`}>
                      <span className="text-[11px]">{formatTime(message.timestamp)}</span>
                      <MessageStatus message={message} mine={mine} />
                    </div>
                  </div>
                </article>
              </div>
            )
          })}
          {typingName && (
            <div className="flex items-center gap-2 text-sm text-text-muted">
              <span>{typingName} is typing</span>
              <span className="typing-dots" aria-hidden="true"><i /><i /><i /></span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="relative border-t border-slate-200 bg-white/95 px-3 py-2 backdrop-blur">
        <div className="mx-auto max-w-3xl">
          <div className="mb-1.5">
            <button
              type="button"
              onClick={() => setShowQuickReplies((value) => !value)}
              className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-text-muted hover:border-primary hover:text-primary"
            >
              {showQuickReplies ? 'Hide quick replies' : 'Quick replies'}
            </button>
            {showQuickReplies && (
              <div className="mt-1.5 flex gap-1.5 overflow-x-auto pb-1">
                {quickReplies.map((reply) => (
                  <button
                    key={reply}
                    type="button"
                    onClick={() => {
                      useQuickReply(reply)
                      setShowQuickReplies(false)
                    }}
                    className="shrink-0 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-text-dark hover:border-primary hover:text-primary"
                  >
                    {reply}
                  </button>
                ))}
              </div>
            )}
          </div>
          {isFallbackPolling && (
            <div className="mb-1.5 inline-flex items-center gap-1.5 rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800">
              <AlertTriangle size={13} />
              Syncing every few seconds.
            </div>
          )}
          <form onSubmit={handleSend} className="flex gap-2">
            <input ref={imageInputRef} type="file" accept="image/*" className="hidden" onChange={handleImageSelected} />
            <button
              type="button"
              onClick={() => imageInputRef.current?.click()}
              disabled={isUploadingAttachment}
              title="Send image"
              className="inline-flex rounded-md border border-slate-200 px-2.5 py-1.5 text-text-muted hover:border-primary hover:text-primary disabled:opacity-60"
            >
              {isUploadingAttachment ? <Loader2 size={16} className="animate-spin" /> : <ImageIcon size={16} />}
            </button>
            <button
              type="button"
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isUploadingAttachment}
              title={isRecording ? 'Stop voice note' : 'Record voice note'}
              className={`inline-flex rounded-md border px-2.5 py-1.5 ${isRecording ? 'border-red-200 bg-red-50 text-red-700' : 'border-slate-200 text-text-muted hover:border-primary hover:text-primary'}`}
            >
              {isRecording ? <Square size={16} /> : <Mic size={16} />}
            </button>
            <input
              value={draft}
              onChange={(event) => handleTyping(event.target.value)}
              placeholder="Type a message..."
              className="min-w-0 flex-1 rounded-full border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-primary"
            />
            <button type="submit" className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-sm font-semibold text-white">
              <Send size={16} />
              Send
            </button>
          </form>
        </div>
      </div>
      <div aria-live="polite" className="sr-only">
        {messages.at(-1)?.sender_name ? `New message from ${messages.at(-1).sender_name}` : ''}
      </div>
      {isReportOpen && otherParty.id && (
        <ReportUserModal
          userId={otherParty.id}
          taskId={numericTaskId}
          userName={otherParty.name}
          onClose={() => setIsReportOpen(false)}
        />
      )}
    </section>
  )
}
