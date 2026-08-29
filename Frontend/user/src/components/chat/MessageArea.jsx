import { useEffect, useRef, useState } from 'react'
import MessageBubble from './MessageBubble'

const ATTACHMENT_MARKER = '[[orbit-attachment]]'
const EMOJIS = ['😀', '😂', '😍', '👍', '👏', '🎉', '✅', '🔥', '💡', '🙏', '😊', '🤝', '🚀', '❤️', '😅', '🎯']
const MAX_FILES = 5
const MAX_FILE_BYTES = 3 * 1024 * 1024
const MAX_MESSAGE_BYTES = 4_500_000

export default function MessageArea({ conversation, messages, currentUserId, onSend, loading, firstUnreadMessageId, unreadCount }) {
  const [draft, setDraft] = useState('')
  const [attachments, setAttachments] = useState([])
  const [emojiOpen, setEmojiOpen] = useState(false)
  const [attachmentError, setAttachmentError] = useState('')
  const fileInputRef = useRef(null)
  const composerRef = useRef(null)
  const scrollRef = useRef(null)
  const [unreadDismissed, setUnreadDismissed] = useState(false)

  useEffect(() => { scrollRef.current?.scrollIntoView({ block: 'end' }) }, [messages])
  useEffect(() => { setUnreadDismissed(false) }, [firstUnreadMessageId])

  const resizeComposer = field => {
    field.style.height = 'auto'
    field.style.height = `${Math.min(field.scrollHeight, 120)}px`
  }

  const submit = event => {
    event.preventDefault()
    if (!draft.trim() && !attachments.length) return
    const attachmentText = attachments.map(file => `${ATTACHMENT_MARKER}${JSON.stringify(file)}`).join('\n')
    onSend([draft.trim(), attachmentText].filter(Boolean).join('\n'))
    setDraft('')
    setAttachments([])
    setEmojiOpen(false)
    setAttachmentError('')
    if (composerRef.current) composerRef.current.style.height = 'auto'
  }

  const onFiles = async event => {
    const selected = Array.from(event.target.files || [])
    event.target.value = ''
    setAttachmentError('')
    if (!selected.length) return
    if (selected.some(file => file.size > MAX_FILE_BYTES)) {
      setAttachmentError('Mỗi tệp phải nhỏ hơn 3 MB.')
      return
    }
    const prepared = await Promise.all(selected.map(file => new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve({ name: file.name, type: file.type, size: file.size, dataUrl: reader.result })
      reader.onerror = () => reject(new Error(`Không đọc được ${file.name}`))
      reader.readAsDataURL(file)
    })))
    setAttachments(current => {
      const next = [...current, ...prepared].slice(0, MAX_FILES)
      const encodedBytes = new Blob(next.map(file => `${ATTACHMENT_MARKER}${JSON.stringify(file)}\n`)).size
      if (encodedBytes > MAX_MESSAGE_BYTES) {
        setAttachmentError('Tổng dung lượng tệp quá lớn. Hãy gửi ít tệp hơn.')
        return current
      }
      if (current.length + prepared.length > MAX_FILES) setAttachmentError(`Chỉ gửi tối đa ${MAX_FILES} tệp mỗi tin nhắn.`)
      return next
    })
  }

  const unreadTargetLoaded = firstUnreadMessageId && messages.some(message => message.id === firstUnreadMessageId)
  const jumpToUnread = () => {
    document.getElementById(`msg-${firstUnreadMessageId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    setUnreadDismissed(true)
  }

  return (
    <div className="message-area">
      {unreadTargetLoaded && !unreadDismissed && (
        <button type="button" className="jump-to-unread-btn" onClick={jumpToUnread}>
          <i className="bi bi-arrow-up" /> {unreadCount} tin nhắn mới
        </button>
      )}
      <div className="messages-scroll">
        <div className="date-divider"><span>Today</span></div>
        {loading && <p className="text-muted small text-center mt-3">Đang tải tin nhắn...</p>}
        {!loading && messages.map(message => (
          <div key={message.id} id={`msg-${message.id}`}>
            {message.id === firstUnreadMessageId && <div className="unread-divider"><span>{unreadCount} tin nhắn mới</span></div>}
            <MessageBubble message={message} own={message.sender_id === currentUserId} />
          </div>
        ))}
        <div ref={scrollRef} />
      </div>
      <form className="composer" onSubmit={submit}>
        <div className="composer-main">
          <input ref={fileInputRef} type="file" hidden multiple onChange={onFiles} />
          <button type="button" className="icon-btn" aria-label="Đính kèm tệp" title="Đính kèm tệp" onClick={() => fileInputRef.current?.click()}><i className="bi bi-paperclip" /></button>
          <textarea
            ref={composerRef}
            rows="1"
            value={draft}
            onChange={event => setDraft(event.target.value)}
            onInput={event => resizeComposer(event.currentTarget)}
            onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) submit(event) }}
            placeholder={`Message ${conversation.name}...`}
          />
          <button type="button" className="icon-btn" aria-label="Chọn emoji" title="Chọn emoji" onClick={() => setEmojiOpen(open => !open)}><i className="bi bi-emoji-smile" /></button>
          <button className="send-btn" aria-label="Send"><i className="bi bi-send-fill" /></button>
        </div>
        {attachments.length > 0 && <div className="composer-attachments">{attachments.map((file, index) => <span key={`${file.name}-${index}`} className="composer-attachment">{file.type?.startsWith('image/') && <img src={file.dataUrl} alt={file.name} />}<i className="bi bi-paperclip" />{file.name}<button type="button" aria-label={`Bỏ ${file.name}`} onClick={() => setAttachments(files => files.filter((_, itemIndex) => itemIndex !== index))}>×</button></span>)}</div>}
        {attachmentError && <div className="composer-error" role="alert">{attachmentError}</div>}
        {emojiOpen && <div className="emoji-picker" role="listbox" aria-label="Emoji picker">{EMOJIS.map(emoji => <button type="button" key={emoji} onClick={() => { setDraft(value => value + emoji); setEmojiOpen(false); composerRef.current?.focus() }}>{emoji}</button>)}</div>}
        <div className="composer-help"><span><i className="bi bi-stars" /> Type <strong>@orbit</strong> to ask AI</span><span>Enter to send · Shift+Enter xuống dòng</span></div>
      </form>
    </div>
  )
}
