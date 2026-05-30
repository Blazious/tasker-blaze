import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bot, Loader2, Mail, MessageCircle, Send, X } from 'lucide-react'
import toast from 'react-hot-toast'
import { getSupportConversation, sendSupportMessage } from '../api/support.js'
import { SUPPORT_EMAIL, SUPPORT_MAILTO } from '../constants/support.js'
import { useAuthStore } from '../store/authStore.js'
import { getApiErrorMessage } from '../utils/apiError.js'

const starterPrompts = [
  'How do payments and escrow work?',
  'Ninawezaje ku-report mtu?',
  'How do I schedule a task?',
  'Why can’t I bid on a task?',
]

export default function TaskitAssistant() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const [isOpen, setIsOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [localMessages, setLocalMessages] = useState([])
  const queryClient = useQueryClient()

  const conversationQuery = useQuery({
    queryKey: ['support-conversation'],
    queryFn: getSupportConversation,
    enabled: isAuthenticated && isOpen,
  })

  const messages = useMemo(() => {
    const saved = conversationQuery.data?.messages ?? []
    return [...saved, ...localMessages]
  }, [conversationQuery.data?.messages, localMessages])

  const sendMutation = useMutation({
    mutationFn: sendSupportMessage,
    onSuccess: (data) => {
      setLocalMessages([])
      setDraft('')
      queryClient.invalidateQueries({ queryKey: ['support-conversation'] })
      if (data.ticket) {
        toast.success('TaskiT admin ticket created')
      }
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Assistant could not reply.'))
      setLocalMessages((current) => current.filter((message) => message.id !== 'pending'))
    },
  })

  if (!isAuthenticated) return null

  const submitMessage = (messageText = draft) => {
    const message = messageText.trim()
    if (!message) return
    setLocalMessages([{ id: 'pending', sender: 'USER', content: message, created_at: new Date().toISOString() }])
    sendMutation.mutate({
      message,
      conversation_id: conversationQuery.data?.id,
    })
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="fixed bottom-5 right-5 z-40 inline-flex items-center gap-2 rounded-full bg-primary px-4 py-3 font-semibold text-white shadow-lg"
      >
        <Bot size={20} />
        Help
      </button>

      {isOpen && (
        <div className="fixed bottom-5 right-5 z-50 flex h-[min(680px,calc(100vh-40px))] w-[min(420px,calc(100vw-24px))] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl">
          <header className="flex items-center gap-3 bg-primary px-4 py-3 text-white">
            <div className="rounded-full bg-white/15 p-2">
              <Bot size={20} />
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="font-semibold">TaskiT Assistant</h2>
              <p className="text-xs text-emerald-100">English, Swahili, and campus support</p>
            </div>
            <button type="button" onClick={() => setIsOpen(false)} className="rounded-md p-1 hover:bg-white/10">
              <X size={20} />
            </button>
          </header>

          <div className="border-b border-slate-100 bg-emerald-50 px-4 py-3 text-xs leading-5 text-primary">
            <p>Ask about tasks, bids, KYC, chat, payments, reviews, safety, or reports. If I cannot solve it, I will raise an admin ticket.</p>
            <a href={SUPPORT_MAILTO} className="mt-2 inline-flex items-center gap-1.5 font-semibold underline-offset-2 hover:underline">
              <Mail size={14} />
              Email admin support: {SUPPORT_EMAIL}
            </a>
          </div>

          <div className="flex-1 overflow-y-auto bg-surface px-4 py-4">
            {conversationQuery.isLoading ? (
              <div className="flex justify-center py-8 text-primary"><Loader2 className="animate-spin" /></div>
            ) : (
              <div className="grid gap-3">
                {messages.length === 0 && (
                  <div className="rounded-lg bg-white p-4 text-sm text-text-muted">
                    Hi. I’m your TaskiT support assistant. Unaweza kuniuliza kwa Kiswahili pia.
                  </div>
                )}
                {messages.map((message) => {
                  const mine = message.sender === 'USER'
                  return (
                    <div key={message.id} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[82%] rounded-2xl px-3 py-2 text-sm shadow-sm ${mine ? 'rounded-br-sm bg-primary text-white' : 'rounded-bl-sm bg-white text-text-dark'}`}>
                        <p className="whitespace-pre-wrap leading-6">{message.content}</p>
                      </div>
                    </div>
                  )
                })}
                {sendMutation.isPending && (
                  <div className="flex items-center gap-2 text-sm text-text-muted">
                    <MessageCircle size={16} />
                    Assistant is thinking...
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="border-t border-slate-200 bg-white p-3">
            <div className="mb-2 flex gap-1.5 overflow-x-auto pb-1">
              {starterPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => submitMessage(prompt)}
                  className="shrink-0 rounded-full border border-slate-200 px-2.5 py-1 text-xs font-medium text-text-muted hover:border-primary hover:text-primary"
                >
                  {prompt}
                </button>
              ))}
            </div>
            <form
              onSubmit={(event) => {
                event.preventDefault()
                submitMessage()
              }}
              className="flex gap-2"
            >
              <input
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Ask TaskiT..."
                className="min-w-0 flex-1 rounded-full border border-slate-300 px-3 py-2 text-sm outline-none focus:border-primary"
              />
              <button type="submit" disabled={sendMutation.isPending} className="rounded-full bg-primary px-3 py-2 text-white disabled:opacity-60">
                {sendMutation.isPending ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
